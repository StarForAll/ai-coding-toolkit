"""人给出的事实（乙口径）：人签名的确认文件 + 显式 source。

**为什么需要这一层**：`waived_by: human:…`、"人已看过预览"、抽样评价、K6 的外发确认，
此前都退化成**字符串前缀约定**——AI 持写权即可自写，人通道形同虚设。

**乙口径的边界（必须写清，别假装它是防伪）**：同一台机器上 AI 能写任何文件，所以这不是密码学防伪。
它保证的是三件事：
1. **形态可辨**：人给出的确认必须是独立文件，且带 `by/at/quote/source` 四个字段，
   `by` 必须是 `human:<来源>`；AI 自述（`by: ai` 或缺字段）一律不被接受；
2. **可审计**：确认文件的**摘要**随事实一起入库（committed），事后改动可被检测出不一致；
3. **非交互可用**：不要求 TTY（甲口径会挡住 CI 与非交互环境）。

真防伪需要人通道（TTY 输入 / 外部密钥），那是甲口径；这里明确记为**已知边界**，不夸大。
"""
from __future__ import annotations

import os

from . import records

REQUIRED_FIELDS = ("by", "at", "quote", "source")


def problems_of(payload, *, action):
    """校验人给出的事实（不写任何东西）。"""
    problems = []
    if not isinstance(payload, dict):
        return [{"reason": "人给出的确认必须是对象（人或宿主写的 JSON）", "action": action,
                 "example": {"by": "human:xzc", "at": "2026-11-10T12:00:00.000000Z",
                             "quote": "我确认…", "source": "user-declared"}}]
    for field in REQUIRED_FIELDS:
        if not str(payload.get(field) or "").strip():
            problems.append({"reason": f"缺 {field}（人给出的确认必须自带来源、时间与原话）",
                             "field": field, "action": action})
    by = str(payload.get("by") or "")
    if by and not by.startswith("human:"):
        problems.append({"reason": "by 必须是 human:<来源>；AI 自述不构成人的确认",
                         "by": by, "action": action})
    if payload.get("source") not in (None, "", "user-declared"):
        problems.append({"reason": "source 只接受 user-declared（其余来源未定义，不猜）",
                         "source": payload.get("source"), "action": action})
    return problems


def load(path, *, action):
    """读确认文件并校验；返回 (payload, digest, problems)。读不到也算问题，不静默放过。"""
    if not path:
        return None, None, [{"reason": "未提供人给出的确认文件", "action": action,
                             "exits": ["由人把确认写成 JSON 文件后，用 --attestation <文件> 传入",
                                       "AI 不得代替人书写该文件；确实无人可问时停下报告"]}]
    if not os.path.exists(path):
        return None, None, [{"reason": "确认文件不存在", "action": action, "path": str(path)}]
    payload = records.load_json(path, None)
    problems = problems_of(payload, action=action)
    digest = records.file_digest(path)
    return payload, digest, problems


def stamp(payload, digest):
    """把"人给出的事实"压成可入库的字段（摘要随事实走，事后可审计）。

    `quote` 与其它 committed 原话同口径：只存遮罩+截断摘要；原文由 digest 固定。
    """
    from . import authorize as authorize_mod

    payload = payload or {}
    return {"by": payload.get("by"), "at": payload.get("at"),
            "quote": authorize_mod.mask_quote(payload.get("quote")),
            "source": payload.get("source"), "attestation_digest": digest}
