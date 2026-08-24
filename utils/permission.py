"""插件白名单权限控制。

所有 handler 注册时传入 rule=is_allowed()，
只有白名单内的 QQ 用户/QQ 群才能触发。
白名单文件修改后即时生效，无需重启 bot。
"""

from __future__ import annotations

import yaml
from nonebot.adapters.onebot.v11 import MessageEvent
from nonebot.rule import Rule
from pathlib import Path

ALLOWLIST_PATH = Path("config/allowlist.yml")


def _load_allowlist() -> dict:
    if not ALLOWLIST_PATH.exists():
        return {"users": [], "groups": []}
    data = yaml.safe_load(ALLOWLIST_PATH.read_text()) or {}
    return {
        "users": [int(u) for u in data.get("users", [])],
        "groups": [int(g) for g in data.get("groups", [])],
    }


def is_allowed() -> Rule:
    """返回一个 Rule，检查消息发送者或所在群是否在白名单中。"""

    def _check(event: MessageEvent) -> bool:
        allow = _load_allowlist()
        if event.user_id in allow["users"]:
            return True
        if hasattr(event, "group_id") and event.group_id in allow["groups"]:
            return True
        return False

    return Rule(_check)
