"""codes.py — 固定原因码表与结果结构（机制稿 §11.1）。

码值语义一经发布不改、只能新增；本模块是唯一登记处。
"""

from __future__ import annotations

# 34 枚首版固定码：code -> (tier, exit, prohibited_repairs)
CODES = {
    "WF_OK": ("pass", "继续当前绑定步骤；不推断其他对象已完成", None),
    "WF_NOT_ENABLED": (
        "blocked",
        "提示人调用 start；不靠绑定文件伪造启用",
        "不把持久绑定、定位缓存或写权记录当作人调用事实",
    ),
    "WF_FLOW_CONFLICT": (
        "blocked",
        "清理来源后在新会话重新核对；不以人工豁免继续混跑",
        "不在已加载冲突指令的会话继续；不修改其他框架资产",
    ),
    "WF_IDENTITY_UNRESOLVED": (
        "needs_decision",
        "核实受支持宿主身份与会话连续性能力，或显式选择 wf 签发路径",
        "不猜环境变量；不退回项目全局指针；不先绑定后补核验",
    ),
    "WF_BINDING_MISMATCH": (
        "blocked",
        "原对象结束后由新会话重新选择",
        "不在本会话改绑；不以定位缓存重建绑定",
    ),
    "WF_WRITER_BUSY": (
        "blocked",
        "等待或走已确认的交接/恢复出口",
        "不超时抢占；不删除锁或写权记录",
    ),
    "WF_GENERATION_STALE": (
        "blocked",
        "停止写入并重新读取当前代次后重试",
        "不自行递增代次；不按当前 holder 补用新代次",
    ),
    "WF_RECORD_INVALID": (
        "blocked",
        "保留原文并经 repair 处理",
        "不覆盖同名任务；不静默补齐缺字段",
    ),
    "WF_CAPABILITY_UNAVAILABLE": (
        "blocked",
        "改用已交付路径，或等所属轮次交付",
        "不退回无锁运行；不猜兼容格式",
    ),
    "WF_PATH_INVALID": (
        "blocked",
        "修正授权输入中的非法路径条目",
        "不跳过非法 touch_paths；不自动扩 glob",
    ),
    "WF_SCOPE_UNRESOLVED": (
        "needs_decision",
        "人核对归属/范围意图，或回 Plan 补声明并重新批准",
        "不自动扩 glob；不以宽命中证明合规",
    ),
    "WF_SCOPE_VIOLATION": (
        "blocked",
        "回 Plan 扩范围或经人确认必要变更后重新批准",
        "不自动扩 glob；不追认越界提交",
    ),
    "WF_APPROVAL_MISSING": (
        "blocked",
        "对当前规划版本取得人批准",
        "不补写伪批准；不沿用旧版本批准",
    ),
    "WF_DEPENDENCY_UNMET": (
        "blocked",
        "等待前置正常完成，或由人确认返工/重连",
        "不把异常归档当地依赖满足",
    ),
    "WF_WORKSPACE_UNRESOLVED": (
        "needs_decision",
        "逐路径核实归属并落实实际处置",
        "不 stash、不捎带、不丢弃他人改动",
    ),
    "WF_WIP_UNRESOLVED": (
        "blocked",
        "同对象核对指纹后恢复，或实际处置后重入",
        "不当空闲放行；不捎带待处置组",
    ),
    "WF_ACTION_INCOMPLETE": (
        "blocked",
        "按原动作意图恢复未完成步骤",
        "不另生成重复对象；不重放业务副作用",
    ),
    "WF_HISTORY_UNRESOLVED": (
        "needs_decision",
        "只读核对 Git/原文，人确认后 repair",
        "不改写历史；不猜锚点或来源",
    ),
    "WF_TARGET_COLLISION": (
        "blocked",
        "保留双方并确认目标",
        "不先改状态后覆盖",
    ),
    "WF_CHECK_FAILED": (
        "blocked",
        "修复后重跑未通过的检查项",
        "不称基本通过；不以无关命令补位",
    ),
    "WF_CHECK_STALE": (
        "blocked",
        "重算锚点后重新 Check / 重新审查",
        "不按归属豁免变化；不复用旧 pass",
    ),
    "WF_SPEC_INCOMPLETE": (
        "blocked",
        "分批读取全文后重试",
        "不以摘要或提醒当已读",
    ),
    "WF_SEMANTIC_DECISION": (
        "needs_decision",
        "列出具体冲突与人的可选出口，由人裁定",
        "不由脚本臆造判据；不把待决当通过",
    ),
    "WF_REVIEW_INVALID": (
        "blocked",
        "补真实审查或重新发起",
        "不伪造异种身份；不复用旧报告",
    ),
    "WF_REVIEW_UNAVAILABLE": (
        "blocked",
        "仍属复杂则暂停或异常归档",
        "不把不可用当 pass；不以环境不足降级",
    ),
    "WF_EXECUTOR_UNCONFIRMED": (
        "blocked",
        "人执行 confirm-executor 确认当前解释器，或按批准修复配置",
        "不自动回退到低优先级执行器",
    ),
    "WF_PREVIEW_STALE": (
        "blocked",
        "重新预览并确认",
        "不扩大旧许可；不复用旧令牌",
    ),
    "WF_RELEASE_CONFLICT": (
        "blocked",
        "核对正确的发行引用与清单",
        "不以名称替代内容校验",
    ),
    "WF_ASSET_DECISION": (
        "needs_decision",
        "预览逐项选择保留/恢复/合并/移走/删除",
        "不认领未知文件；不覆盖本地偏离",
    ),
    "WF_COMMIT_NOT_AUTHORIZED": (
        "blocked",
        "等人给出本次提交及其精确路径的授权",
        "不借维护确认执行提交；不捎带授权外路径",
    ),
    "WF_PERSISTENCE_FAILED": (
        "blocked",
        "报告命令、影响与读回/恢复出口",
        "不盲重试；不宣称成功",
    ),
    "WF_VERIFICATION_UNREADY": (
        "blocked",
        "补齐真实来源/设施后重新解析",
        "不以「定义可解析」替代就绪",
    ),
    "WF_DEFINITION_INVALID": (
        "blocked",
        "按静态校验清单修正定义",
        "不猜测承载步骤；不用自由文本占位",
    ),
    "WF_TEMPLATE_INCOMPLETE": (
        "blocked",
        "填写模板声明的待填位置并重新核验",
        "不以删除标记充当填完",
    ),
}

TIER_EXIT_CODES = {"pass": 0, "blocked": 1, "needs_decision": 2}
INTERNAL_ERROR_EXIT = 70


class CodeUnknown(Exception):
    pass


def tier_of(code: str) -> str:
    try:
        return CODES[code][0]
    except KeyError as exc:
        raise CodeUnknown(code) from exc


def exit_of(code: str) -> str:
    return CODES[code][1]


def prohibited_of(code: str) -> str | None:
    return CODES[code][2]


def process_exit(code: str) -> int:
    return TIER_EXIT_CODES[tier_of(code)]


def position(scope=None, phase=None, step_id=None, task_id=None, action_id=None, action_state=None):
    return {
        "scope": scope,
        "phase": phase,
        "step_id": step_id,
        "task_id": task_id,
        "action_id": action_id,
        "action_state": action_state,
    }


def result(
    code,
    *,
    object=None,
    position_=None,
    next_=None,
    facts=None,
    warnings=None,
    issues=None,
):
    """构造 §11.1 的单一结果结构。"""
    payload = {
        "tier": tier_of(code),
        "code": code,
        "object": object,
        "position": position_ or position(),
        "next": next_,
        "facts": facts or {},
        "exit": exit_of(code),
        "prohibited_repairs": prohibited_of(code) if tier_of(code) != "pass" else None,
        "warnings": warnings or [],
    }
    if issues:
        payload["issues"] = issues
    return payload
