"""erinn 配方数据库工具函数。"""

from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path("data/erinn.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


async def search_items(keyword: str, limit: int = 10) -> list[dict]:
    """模糊搜索物品名称（有配方或有获取方式的物品）。"""
    conn = _connect()
    if "*" in keyword:
        pattern = f"%{keyword.replace('*', '%')}%"
    else:
        parts = keyword.split()
        pattern = f"%{'%'.join(parts)}%"
    rows = conn.execute(
        "SELECT DISTINCT i.item_id, i.name FROM items i "
        "WHERE i.name LIKE ? "
        "AND (EXISTS (SELECT 1 FROM recipes r WHERE r.item_id = i.item_id) "
        "  OR EXISTS (SELECT 1 FROM acquisitions a WHERE a.item_id = i.item_id)) "
        "ORDER BY i.item_id LIMIT ?",
        (pattern, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
