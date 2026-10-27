#!/usr/bin/env python3
"""M8 record-phase edits: version fields, title, status, §10, appendix v47 note,
appendix C v48 entry, companion frontmatter + §36. Same discipline as the
manifest: each old string must occur exactly once before its replacement; the
new string must occur exactly once afterwards."""
import sys
from pathlib import Path

ROOT = Path("/home/xzc/projects/personal/ai-coding-toolkit")
MAIN = ROOT / "docs/workflows/workflow-design.md"
COMP = ROOT / "docs/workflows/依赖机制设计说明.md"

V48_SOURCE = (
    "- **源**：§10 自检场景串补尾端守卫与异常目标重连复合场景（补 v47 声称而缺失的场景，v47 源行末已注补落）；"
    "§6.4 第 2 步、逐窗口「标记内容已改写」与「创建调用中断」两行、§7.8 矩阵第 14 行写入时点格"
    "（登记期间冲突改写的标识 / 定位统一为改写随写出立即提交、自成提交组，发布取值读已提交标记）；"
    "§7.7 类型 1 P 分支与类型 5 的重连守卫加域（守卫限重连目标的存在性与成环，目标账本为“异常”时重连仍写入，"
    "其处分项按 §7.4 各自完成）、类型 5 补建分支承认继任者任意账本值、类型 1 一般任务分支去空归档；"
    "§0 写作约定尾句改命名条款（矩阵行逐格义务的唯一源），§0.1 口径 10⑥、§10 类迁移义务与自检括注降为按 §0 引用（⑥ 判据语义不变）。"
)
V48_COPIES = (
    "- **副本**：主稿 §6.4 逐窗口 ④（docs/workflows/workflow-design.md:684，已同步）、"
    "表 B9 继任验收句（docs/workflows/workflow-design.md:97，已同步）、"
    "§0 尾句源位（docs/workflows/workflow-design.md:37，已同步）、"
    "§0.1 口径 10⑥ 引用位（docs/workflows/workflow-design.md:66，已同步）、"
    "§10 类迁移义务引用位（docs/workflows/workflow-design.md:899，已同步）、"
    "§10 自检括注引用位（docs/workflows/workflow-design.md:910，已同步）、"
    "§6.5 向前完成结论句（M3h 同条件副本并入，docs/workflows/workflow-design.md:490，已同步）；"
    "配套 §6.4 结论句（docs/workflows/依赖机制设计说明.md:181，已同步）、"
    "§8 类型 5 句（docs/workflows/依赖机制设计说明.md:271，已同步）、"
    "发起清单两处作用域（docs/workflows/依赖机制设计说明.md:164 与 :194，已同步）、"
    "抬头版本行（docs/workflows/依赖机制设计说明.md:13，已同步）；"
    "M1 记录位：v47 源行行末补落注记（docs/workflows/workflow-design.md:953，已同步）。"
)
V48_VERSION = "- 版本：本文件 v48；配套文档 v48。"
V48_BLOCK = f"### v48\n\n{V48_SOURCE}\n{V48_COPIES}\n{V48_VERSION}\n\n"

EDITS = [
    (MAIN, "version: v47", "version: v48"),
    (MAIN,
     "口径 10⑥ 判据入闸口（写入路径格回指产生者，其余格写终值或不变理由）、图内任务成员补基线变更新建任务\nscope:",
     "口径 10⑥ 判据入闸口（写入路径格回指产生者，其余格写终值或不变理由）、图内任务成员补基线变更新建任务；v48 修复：自检场景补尾端守卫与异常目标重连、改写即提交、重连守卫加域、闸口义务单源、配套抬头与清单作用域、类型 1 分支去空归档\nscope:"),
    (MAIN, "# 工作流整体设计（v47 · 修订）", "# 工作流整体设计（v48 · 修订）"),
    (MAIN,
     "模块的 `implements_design` 必须等于本文件 frontmatter 版本（v47）；配套文档的 `design` 字段必须写明本文件版本（`workflow-design.md v47`）",
     "模块的 `implements_design` 必须等于本文件 frontmatter 版本（v48）；配套文档的 `design` 字段必须写明本文件版本（`workflow-design.md v48`）"),
    (MAIN,
     "§10 自检场景补\"先按类型 5 补建\"；§3 图内任务成员补基线变更新建任务。",
     "§10 自检场景补\"先按类型 5 补建\"；§3 图内任务成员补基线变更新建任务。（§10 场景句由 v48 补落）"),
    (MAIN, "## 附录 C：本版修订\n\n### v47", "## 附录 C：本版修订\n\n" + V48_BLOCK + "### v47"),
    (COMP, "version: v47", "version: v48"),
    (COMP, "design: workflow-design.md v47", "design: workflow-design.md v48"),
    (COMP,
     "- 主设计 §3 图内任务成员补「基线变更新建任务」；本文 §3 术语行同版镜像。\n- 版本 v47；与主设计 v47 同版。",
     "- 主设计 §3 图内任务成员补「基线变更新建任务」；本文 §3 术语行同版镜像。\n- 版本 v47；与主设计 v47 同版。\n\n"
     "## 36. 本版修订（v48）\n\n"
     "- 主设计 §10 自检场景串补尾端守卫与异常目标重连复合场景（补 v47 声称而缺失的场景）；场景面在主设计 §10，本文无镜像义务。\n"
     "- 主设计 §6.4 第 2 步、逐窗口两行与 §7.8 矩阵第 14 行统一冲突改写的提交时点（改写随写出立即提交、自成提交组，发布取值读已提交标记）；本文 §9 字段规则为引用式，无终值副本，未新增定义。\n"
     "- 主设计 §7.7 重连守卫加域（守卫限重连目标的存在性与成环，目标账本为“异常”时重连仍写入，其处分项按主设计 §7.4 各自完成）；本文 §6.4 结论句与 §8 类型 5 句同版镜像（docs/workflows/依赖机制设计说明.md:181 与 :271，已同步）。\n"
     "- 主设计 §7.7 类型 1 一般任务分支去空归档；本文 §8 类型 1 句为引用式（细则见主设计 §7.7），无需镜像改动。\n"
     "- 主设计 §0 闸口义务单源化（矩阵行逐格义务唯一源在 §0）；本文无副本（设计层闸口在主设计 §0）。\n"
     "- 本文发起清单两处补「含已预写标识」作用域（docs/workflows/依赖机制设计说明.md:164 与 :194，已同步）；抬头同步版本行改 v48（docs/workflows/依赖机制设计说明.md:13，已同步）。\n"
     "- 版本 v48；`design: workflow-design.md v48`；与主设计 v48 同版。逐条行号与验收位见主设计附录 C v48 与任务 fix-notes。"),
]


def main():
    for path, old, new in EDITS:
        text = path.read_text(encoding="utf-8")
        c = text.count(old)
        if c != 1:
            sys.exit(f"pre count={c} (expected 1) for: {old[:60]!r} in {path.name}")
    for path, old, new in EDITS:
        text = path.read_text(encoding="utf-8")
        text = text.replace(old, new, 1)
        assert text.count(new) == 1, new[:60]
        path.write_text(text, encoding="utf-8")
        print(f"ok\t{path.name}\t{new[:40]}")
    # 校验 v47 源行实际行号，与 v48 副本中引用的 :953 比对
    main_text = MAIN.read_text(encoding="utf-8")
    marker = "（§10 场景句由 v48 补落）"
    idx = main_text.index(marker)
    line_no = main_text[:idx].count("\n") + 1
    print(f"v47 源行实际行号: {line_no}（v48 副本引用 :953）")


if __name__ == "__main__":
    main()
