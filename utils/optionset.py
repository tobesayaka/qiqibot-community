"""optionset 游戏道具数据库工具函数。

数据通过 scripts/fetch_optionset.py 从 prilus 资源服务器下载写入 SQLite，
NoneBot 插件通过 search_items() 查询。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path("data/optionset.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


async def search_items(keyword: str, limit: int = 10) -> list[dict]:
    """模糊搜索道具名称。"""
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM items WHERE name LIKE ? ORDER BY id LIMIT ?",
        (f"%{keyword}%", limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


async def get_item(item_id: int) -> dict | None:
    """按 ID 获取单条道具。"""
    conn = _connect()
    row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    conn.close()
    return dict(row) if row else None
