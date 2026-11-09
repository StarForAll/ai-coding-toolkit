"""maintenance.py — 维护入口的共享形状（第三轮交付 upgrade 的预览/令牌）。

repair 与 uninstall 的应用逻辑自含于各自单文件入口（实现稿 §4.5.1、§6.2 D09），
本模块只承载第三轮的 upgrade 预览与令牌，以及两份自含实现的形状说明。
"""

from __future__ import annotations

from . import assets

ROUND = 3

# 两份自含实现的形状（不得漂移）：nonce 128 位、令牌绑定预览摘要、同进程失效。
TOKEN_SHAPE = {
    "nonce_bits": 128,
    "nonce_source": "secrets.token_hex(16)",
    "binding": "sha256: + sha256(C(preview object))",
    "lifetime": "same interactive process; re-preview destroys previous nonce",
}


def preview(*_args, **_kwargs):
    raise assets.CapabilityUnavailable("upgrade preview (D37)", ROUND)


def token_confirm(*_args, **_kwargs):
    raise assets.CapabilityUnavailable("upgrade apply token (D28)", ROUND)


def apply(*_args, **_kwargs):
    raise assets.CapabilityUnavailable("asset.apply (D37)", ROUND)
