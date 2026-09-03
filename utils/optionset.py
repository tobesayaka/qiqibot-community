"""optionset 游戏道具数据库工具函数。

数据通过 scripts/fetch_optionset.py 从 prilus 资源服务器下载写入 SQLite。
"""

from __future__ import annotations

from pathlib import Path

from utils.db import query_one, query_all

DB_PATH = Path("data/optionset.db")


async def search_items(keyword: str, limit: int = 10) -> list[dict]:
    """模糊搜索道具名称。"""
    return await query_all(
        DB_PATH,
        "SELECT * FROM items WHERE name LIKE ? ORDER BY id LIMIT ?",
        (f"%{keyword}%", limit),
    )


async def get_item(item_id: int) -> dict | None:
    """按 ID 获取单条道具。"""
    return await query_one(DB_PATH, "SELECT * FROM items WHERE id = ?", (item_id,))
