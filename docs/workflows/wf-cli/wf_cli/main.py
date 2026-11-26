"""System-level wf command entry point.

``wf`` is the single user-facing command for maintenance and a forwarder for project runtime
commands. It never reads or writes project work products itself: install/upgrade run the release
installer, uninstall/repair run the installed independent entries, and everything else is
delegated to ``.wf/bin/wf.py``.
"""

from __future__ import annotations

import os
import sys

from . import commands, selfupdate
from .selfupdate import SelfUpgradeError
from .project import ProjectError, installed_version, open_project
from .release import ReleaseError, current_source_url, ensure_release, latest_release
from .result import blocked, passed
from .version import (VersionError, cli_version, require_release_version, tag_name)

MAINTENANCE = ("install", "upgrade", "uninstall", "repair")
RETIRED = {
    "--release": "发行身份由系统 wf 命令决定：不再接受本地发行检出根",
    "--release-ref": "发行身份由系统 wf 命令/发行 tag 决定：不再接受发行引用参数",
    "--source": "发行源由登记 forgejo 仓库决定：不再接受本地 --source",
    "--strict-source": "发行源由系统 wf 命令校验：不再接受 --strict-source",
    "--target": "统一用 --project <绝对路径>；--target 属发行安装器内部参数",
    "--upgrade": "升级由 `wf upgrade` 承接；不再对 install 传入 --upgrade",
    "--nonce": "预览指纹只由终端预览生成；不接受注入令牌的测试形态",
}

COMMAND_HELP = {
    "install": "wf install [--project <绝对路径>] [--confirm] [--python <绝对路径>] [--json]",
    "upgrade": "wf upgrade [--project <绝对路径>] [--apply | --export-deviations --out <目录>] "
               "[--keep <项目相对路径> ...] [--restore <项目相对路径> ...] [--json]",
    "uninstall": "wf uninstall [--project <绝对路径>] [--purge] [--apply] [--json]",
    "repair": "wf repair [--project <绝对路径>] [--apply] [--dispose <处置计划>] [--json]",
    "version": "wf version [--project <绝对路径>] [--json]",
    "self-upgrade": "wf self-upgrade [--manager uv|pipx|pip] [--json]",
    "self-uninstall": "wf self-uninstall [--manager uv|pipx|pip] [--apply] [--json]",
    "help": "wf help [<命令>]",
}

# 每个命令的说明只登记一次：总览与 `wf help <命令>` / `<命令> --help` 都从这里取值，
# 否则"用法一处、作用一处"必然漂移（`wf repair` 曾只剩转交说明，看不出它到底修什么）。
COMMAND_DESC = {
    "install": "在尚无 .wf/ 的项目中安装系统 wf 命令自身版本对应的发行；首跑只预览，确认后加 "
               "--confirm。--python 选定运行 wf 的解释器（>=3.11 绝对路径，写入本机用户级配置）。",
    "upgrade": "把项目资产升级到登记发行源默认分支上的最新发行（按 tag 创建时间取最新，"
               "不指定版本、不指定本地发行目录）：首跑只预览，--apply 后在终端输入预览指纹执行；"
               "--export-deviations 是只读回源，导出本地偏离清单与补丁。",
    "uninstall": "转交已安装版本的独立卸载入口 .wf/bin/uninstall.py（缺该单文件时从对应发行重取同一文件）："
                 "预览将删除的资产，默认保留项目数据；--apply 输入预览指纹后执行。",
    "repair": "转交已安装版本的独立修复入口 .wf/bin/repair.py（缺该单文件时从对应发行重取同一文件）："
              "修复被中断或残留的写入记录——把 .wf/writer.json 复位为空闲（代次 +1、保留维护回执），"
              "不动业务记录与 skill 资产；--dispose <处置计划> 只回写指定维护回执的处置字段。"
              "首跑只预览，--apply 输入预览指纹才执行；旧写者进程仍存活时拒绝。",
    "version": "显示系统 wf 版本、登记发行源与当前项目已安装的版本。",
    "self-upgrade": "升级系统 wf 命令本身到登记源最新发行（区别于项目内 wf upgrade）。",
    "self-uninstall": "卸载系统 wf 命令本身；首跑只显示将要执行的管理器命令，加 --apply 执行。",
    "help": "显示总览；wf help <命令> 给出该命令的用法与说明。",
}

# 模板里的占位名不能用连字符，这里按「命令名 → 下划线形式」派生；缺一项即 KeyError（不静默留空）
_HELP_FIELDS = {name.replace("-", "_"): description
                for name, description in COMMAND_DESC.items()}

HELP = """wf — 系统级 wf 命令

用法：
  wf install  [--project <绝对路径>] [--confirm] [--python <绝对路径>] [--json]
      {install}
  wf upgrade  [--project <绝对路径>] [--apply | --export-deviations --out <目录>]
              [--keep <项目相对路径> ...] [--restore <项目相对路径> ...] [--json]
      {upgrade}
  wf uninstall [--project <绝对路径>] [--purge] [--apply] [--json]
      {uninstall}
  wf repair    [--project <绝对路径>] [--apply] [--dispose <处置计划>] [--json]
      {repair}
  wf version   [--project <绝对路径>] [--json]
      {version}
  wf self-upgrade [--manager uv|pipx|pip] [--json]
      {self_upgrade}
  wf self-uninstall [--manager uv|pipx|pip] [--apply] [--json]
      {self_uninstall}
  wf help [<命令>]
      {help}

运行期命令（task-new、task-check、spec、review-* 等）：
  wf [--project <绝对路径>] <命令> [参数]
      在项目内自动定位 .wf/ 并转交 .wf/bin/wf.py；--project 可选，缺省用当前目录（向上找 .wf/）。

发行规则：
  - 系统命令用 `python3 scripts/install-wf.py`（或 release 的 `install.py` 附件）取最新正式
    release 的 wheel 附件安装，不指定版本。
  - 项目 install 使用系统 wf 命令自身版本对应的发行 tag。
  - 项目 upgrade 使用登记源默认分支上的最新发行 tag（按 tag 创建时间取最新，不按版本号猜）。
  - self-upgrade 升级系统命令本身；与项目 upgrade 分离。
  - 不再接受 --release、--release-ref、--source、--target；不使用本机 checkout 充当发行源。
""".format(**_HELP_FIELDS)


def command_text(command):
    """单个命令的帮助正文：用法 + 说明（总览与 help 子命令共用这一份）。"""
    return f"{COMMAND_HELP[command]}\n      {COMMAND_DESC[command]}\n"


class UsageError(Exception):
    def __init__(self, message, facts=None, exit_hint=None):
        super().__init__(message)
        self.code = "WF_USAGE_INVALID"
        self.message = message
        self.facts = facts or {}
        self.exit_hint = exit_hint


def _extract_leading_project(argv):
    project = None
    rest = list(argv)
    while rest:
        token = rest[0]
        if token == "--project":
            if len(rest) < 2 or not rest[1] or rest[1].startswith("--"):
                raise UsageError("--project 缺绝对路径值",
                                 {"missing": "--project"},
                                 "在命令前给出 --project <绝对路径>")
            if project is not None:
                raise UsageError("--project 重复", {"project": project, "again": rest[1]},
                                 "只给一次 --project")
            project = rest[1]
            rest = rest[2:]
            continue
        if token.startswith("--project="):
            value = token.split("=", 1)[1]
            if not value:
                raise UsageError("--project 缺绝对路径值", {"missing": "--project"},
                                 "在命令前给出 --project <绝对路径>")
            if project is not None:
                raise UsageError("--project 重复", {"project": project, "again": value},
                                 "只给一次 --project")
            project = value
            rest = rest[1:]
            continue
        break
    return project, rest


def _parse_flags(command, argv):
    spec = {
        "install": ({"--confirm", "--json"}, {"--project", "--python"}),
        "upgrade": ({"--apply", "--export-deviations", "--json"},
                    {"--project", "--out", "--keep", "--restore"}),
        "uninstall": ({"--purge", "--apply", "--json"}, {"--project"}),
        "repair": ({"--apply", "--json"}, {"--project", "--dispose"}),
        "version": ({"--json"}, {"--project"}),
        "self-upgrade": ({"--json"}, {"--manager"}),
        "self-uninstall": ({"--json", "--apply"}, {"--manager"}),
    }[command]
    booleans, values = spec
    parsed = {"json": False}
    repeated = {"--keep": [], "--restore": []}
    index = 0
    while index < len(argv):
        token = argv[index]
        if token in ("-h", "--help"):
            parsed["help"] = True
            index += 1
            continue
        name, inline = token, None
        if token.startswith("--") and "=" in token:
            name, inline = token.split("=", 1)
        if not name.startswith("-"):
            raise UsageError(f"{command} 不接受位置参数",
                             {"command": command, "argument": token},
                             f"按 `{COMMAND_HELP[command]}` 修正参数")
        if command == "upgrade" and name in ("--confirm", "--python"):
            raise UsageError(f"{name} 不适用于 upgrade",
                             {"command": command, "flag": name},
                             "升级用 --apply + 终端预览令牌；解释器沿用已确认执行器")
        if name in RETIRED:
            raise UsageError(f"{name} 已停用：{RETIRED[name]}",
                             {"command": command, "retired": name,
                              "known": sorted(booleans | values)},
                             f"按 `{COMMAND_HELP[command]}` 修正参数")
        if name in booleans:
            if inline is not None:
                raise UsageError(f"{name} 不接受取值", {"flag": name, "value": inline},
                                 f"按 `{COMMAND_HELP[command]}` 修正参数")
            if name == "--json":
                parsed["json"] = True
            else:
                parsed[name] = True
            index += 1
            continue
        if name in values:
            if inline is None:
                if index + 1 >= len(argv) or argv[index + 1].startswith("--"):
                    raise UsageError(f"{name} 缺取值", {"flag": name},
                                     f"按 `{COMMAND_HELP[command]}` 修正参数")
                inline = argv[index + 1]
                index += 2
            else:
                index += 1
            if name in repeated:
                repeated[name].append(inline)
            else:
                if parsed.get(name) is not None:
                    raise UsageError(f"{name} 重复", {"flag": name},
                                     f"按 `{COMMAND_HELP[command]}` 修正参数")
                parsed[name] = inline
            continue
        raise UsageError(f"未知参数：{name}",
                         {"command": command, "unknown": name,
                          "known": sorted(booleans | values | set(RETIRED))},
                         f"按 `{COMMAND_HELP[command]}` 修正参数；不用未登记参数试探")
    for name, items in repeated.items():
        if items:
            parsed[name] = items
    return parsed


def _project_value(parsed, leading):
    explicit = parsed.get("--project")
    if explicit and leading and os.path.realpath(explicit) != os.path.realpath(leading):
        raise UsageError("--project 出现两次且取值不同",
                         {"before_command": leading, "after_command": explicit},
                         "只保留一个 --project")
    return explicit or leading


def _blocked(exc, json_mode=False):
    if isinstance(exc, UsageError):
        return blocked(exc.code, exc.message, exc.facts, exc.exit_hint, json_mode)
    if isinstance(exc, (ProjectError, ReleaseError, SelfUpgradeError)):
        warnings = getattr(exc, "warnings", None)
        return blocked(exc.code, exc.message, exc.facts, exc.exit_hint, json_mode,
                       warnings=warnings)
    if isinstance(exc, VersionError):
        return blocked("WF_CAPABILITY_UNAVAILABLE", str(exc), {},
                       "从发行 tag 安装系统 wf；不把未知版本当作发行身份", json_mode)
    if isinstance(exc, FileNotFoundError):
        return blocked("WF_CAPABILITY_UNAVAILABLE", f"入口不存在：{exc}",
                       {"missing": str(exc)},
                       "核对安装记录与发行入口；不按猜测路径重试", json_mode)
    if isinstance(exc, OSError):
        return blocked("WF_PERSISTENCE_FAILED", f"文件/进程操作失败：{exc}",
                       {"detail": str(exc)},
                       "核对权限/路径后重试；不把失败当成功", json_mode)
    raise exc


def _status(message, json_mode):
    if not json_mode:
        sys.stdout.write(message + "\n")
        sys.stdout.flush()


def cmd_install(argv, leading, exec_fn):
    parsed = _parse_flags("install", argv)
    json_mode = parsed["json"]
    if parsed.get("help"):
        sys.stdout.write(command_text("install"))
        return 0
    target = _project_value(parsed, leading) or os.getcwd()
    project = open_project(target)
    version = require_release_version(cli_version())
    installed = installed_version(project)
    if installed is not None and installed != version:
        return blocked(
            "WF_RELEASE_CONFLICT",
            f"目标已安装 {installed}，系统 wf 为 {version}：install 只核对同版",
            {"installed": installed, "system": version, "project": project.root},
            "升级用 `wf upgrade`（取最新发行）；要按系统版本核对，先安装对应版本的 wf 命令",
            json_mode,
        )
    root = ensure_release(version)
    command = commands.installer_command(
        root, project.root, confirm=bool(parsed.get("--confirm")),
        python=parsed.get("--python"), json_mode=json_mode)
    _status(f"系统 wf {version} → 发行 {tag_name(version)}；入口 {root}", json_mode)
    return commands.exec_replace(command, exec_fn)


def cmd_upgrade(argv, leading, exec_fn):
    parsed = _parse_flags("upgrade", argv)
    json_mode = parsed["json"]
    if parsed.get("help"):
        sys.stdout.write(command_text("upgrade"))
        return 0
    project = open_project(_project_value(parsed, leading), require=True)
    if project.installation is None:
        return blocked("WF_RECORD_INVALID", "目标未安装 wf：没有安装记录",
                       {"project": project.root},
                       "先在目标项目运行 `wf install`", json_mode)
    installed = installed_version(project)
    release = latest_release()
    if installed == release.version and not parsed.get("--export-deviations"):
        return passed(f"目标已是最新发行 {release.tag}，无需升级",
                      {"project": project.root, "version": release.version,
                       "tag": release.tag},
                      "需要回源导出本地偏离时加 --export-deviations", json_mode)
    root = ensure_release(release.version, repo=release.repo)
    command = commands.installer_command(
        root, project.root, upgrade=True, apply=bool(parsed.get("--apply")),
        export_deviations=bool(parsed.get("--export-deviations")), out=parsed.get("--out"),
        keep=parsed.get("--keep") or (), restore=parsed.get("--restore") or (),
        json_mode=json_mode)
    _status(
        f"已安装 {installed}；最新发行 {release.tag}（{release.commit[:12]}）；"
        f"入口 {root}",
        json_mode,
    )
    return commands.exec_replace(command, exec_fn)


def _independent(kind, argv, leading, exec_fn):
    parsed = _parse_flags(kind, argv)
    json_mode = parsed["json"]
    if parsed.get("help"):
        sys.stdout.write(command_text(kind))
        return 0
    project = open_project(_project_value(parsed, leading), require=True)
    local_script = os.path.join(project.root, ".wf", "bin", f"{kind}.py")
    release_root = None
    if not os.path.isfile(local_script):
        if project.installation is None:
            return blocked("WF_CAPABILITY_UNAVAILABLE", f"缺少独立 {kind}.py 且无安装记录",
                           {"project": project.root, "missing": local_script},
                           "按安装记录从对应发行重取该单文件；不从目录形状猜", json_mode)
        version = installed_version(project)
        release_root = ensure_release(version)
    command = commands.independent_command(
        project.root, kind, local_script=local_script, release_root=release_root,
        purge=bool(parsed.get("--purge")), apply=bool(parsed.get("--apply")),
        dispose=parsed.get("--dispose"), json_mode=json_mode)
    return commands.exec_replace(command, exec_fn)


def cmd_uninstall(argv, leading, exec_fn):
    return _independent("uninstall", argv, leading, exec_fn)


def cmd_repair(argv, leading, exec_fn):
    return _independent("repair", argv, leading, exec_fn)


def cmd_self_upgrade(argv, leading, exec_fn):
    parsed = _parse_flags("self-upgrade", argv)
    json_mode = parsed["json"]
    if parsed.get("help"):
        sys.stdout.write(command_text("self-upgrade"))
        return 0
    if leading:
        return blocked("WF_USAGE_INVALID", "self-upgrade 升级系统命令，不作用于项目",
                       {"project": leading},
                       "去掉 --project；项目升级用 `wf upgrade`", json_mode)
    version = require_release_version(cli_version())
    latest = latest_release()
    if latest.version == version:
        return passed(f"系统 wf 已是最新发行 {latest.tag}，无需升级",
                      {"version": version, "tag": latest.tag},
                      "需要修复安装时用 bootstrap 安装脚本重装", json_mode)
    _status(f"系统 wf {version} → 最新发行 {latest.tag}", json_mode)
    facts = selfupdate.perform(
        version, latest, manager=parsed.get("--manager"), token=selfupdate._token())
    return passed(f"系统 wf 已升级到 {latest.tag}（下次调用生效）", facts,
                  "运行 `wf version` 核对系统命令版本", json_mode)


def cmd_self_uninstall(argv, leading, exec_fn):
    parsed = _parse_flags("self-uninstall", argv)
    json_mode = parsed["json"]
    if parsed.get("help"):
        sys.stdout.write(command_text("self-uninstall"))
        return 0
    if leading:
        return blocked("WF_USAGE_INVALID", "self-uninstall 卸载系统命令，不作用于项目",
                       {"project": leading},
                       "去掉 --project；项目卸载用 `wf uninstall`", json_mode)
    manager = parsed.get("--manager")
    # 预览只做管理器识别与命令展示；不调用 subprocess。
    detected = selfupdate.manager_for(requested=manager)
    if detected is None:
        return blocked("WF_CAPABILITY_UNAVAILABLE", "无法识别系统 wf 的安装管理器", {},
                       "用 --manager uv|pipx|pip 指定", json_mode)
    command = selfupdate.uninstall_command(detected)
    if not parsed.get("--apply"):
        return passed("系统 wf 卸载预览（未执行）",
                      {"manager": detected, "command": command},
                      "确认后加 --apply 重跑", json_mode)
    result = selfupdate.perform_uninstall(manager=detected)
    return passed("系统 wf 已卸载（当前进程退出后命令消失）",
                  {"manager": result["manager"], "command": result["command"],
                   "output": result["output"][-800:]},
                  "如仍存在命令，检查 uv/pipx 的 bin 目录", json_mode)


def cmd_version(argv, leading, exec_fn):
    parsed = _parse_flags("version", argv)
    json_mode = parsed["json"]
    if parsed.get("help"):
        sys.stdout.write(command_text("version"))
        return 0
    version = require_release_version(cli_version())
    explicit = _project_value(parsed, leading)
    project = open_project(explicit) if explicit else open_project()
    installed = installed_version(project) if project is not None else None
    facts = {"version": version, "source": current_source_url()}
    if project is not None:
        facts["project"] = project.root
    if installed is not None:
        facts["installed"] = installed
    message = f"wf {version}"
    return passed(message, facts, "用 `wf install` / `wf upgrade` / `wf uninstall` 维护项目",
                  json_mode)


def _forward_help(argv, leading, exec_fn):
    if not argv:
        sys.stdout.write(HELP + "\n")
        return 0
    if argv[0] in COMMAND_HELP:
        sys.stdout.write(command_text(argv[0]))
        return 0
    project = open_project(leading, require=True)
    command = commands.bootstrap_command(project.root, ["help", *argv])
    return commands.exec_replace(command, exec_fn)


def _runtime(command, rest, leading, exec_fn):
    if command in RETIRED:
        raise UsageError(f"{command} 已停用：{RETIRED[command]}",
                         {"unknown": command, "retired": command},
                         "先给子命令；发行参数不再属于系统 wf 的调用面")
    if command.startswith("-"):
        raise UsageError(f"未知全局参数：{command}", {"unknown": command},
                         "先给命令名；全局只认前置 --project <绝对路径>")
    project = open_project(leading, require=True)
    if command in MAINTENANCE:
        raise UsageError(f"{command} 必须由系统 wf 维护入口执行",
                         {"command": command}, "按 `wf help {command}` 修正入口")
    command_line = commands.bootstrap_command(project.root, [command, *rest])
    return commands.exec_replace(command_line, exec_fn)


def main(argv=None, exec_fn=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    json_mode = "--json" in argv
    try:
        leading, rest = _extract_leading_project(argv)
        if not rest:
            sys.stdout.write(HELP + "\n")
            return 0
        head = rest[0]
        tail = rest[1:]
        if head in ("-h", "--help", "help"):
            return _forward_help(tail, leading, exec_fn)
        if head in ("version", "--version"):
            return cmd_version(tail, leading, exec_fn)
        if head == "self-upgrade":
            return cmd_self_upgrade(tail, leading, exec_fn)
        if head == "self-uninstall":
            return cmd_self_uninstall(tail, leading, exec_fn)
        if head == "install":
            return cmd_install(tail, leading, exec_fn)
        if head == "upgrade":
            return cmd_upgrade(tail, leading, exec_fn)
        if head == "uninstall":
            return cmd_uninstall(tail, leading, exec_fn)
        if head == "repair":
            return cmd_repair(tail, leading, exec_fn)
        return _runtime(head, tail, leading, exec_fn)
    except (UsageError, ProjectError, ReleaseError, SelfUpgradeError, VersionError, FileNotFoundError, OSError) as exc:
        return _blocked(exc, json_mode)


def entry():
    raise SystemExit(main())


if __name__ == "__main__":
    entry()