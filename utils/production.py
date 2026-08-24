"""production 制作配方数据库工具函数。

数据通过 scripts/fetch_production.py 下载写入 SQLite。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path("data/production.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


async def search_productions(keyword: str, limit: int = 10) -> list[dict]:
    """模糊搜索制作配方名称。

    两种模式：
    - 通配符模式：含 * 时直接作为通配符，如 "释魂*琴" → LIKE '%释魂%琴%'
    - 分词模式：空格分隔，按顺序匹配，如 "释魂 琴" → LIKE '%释魂%琴%'
    """
    conn = _connect()
    if "*" in keyword:
        pattern = f"%{keyword.replace('*', '%')}%"
    else:
        parts = keyword.split()
        pattern = f"%{'%'.join(parts)}%"
    rows = conn.execute(
        "SELECT * FROM productions WHERE name LIKE ? ORDER BY item_id LIMIT ?",
        (pattern, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


async def get_production(item_id: int) -> dict | None:
    """按成品物品 ID 获取配方。"""
    conn = _connect()
    row = conn.execute(
        "SELECT * FROM productions WHERE item_id = ?", (item_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


async def get_item_image(item_id: int) -> str | None:
    """获取物品图片的 base64 编码。"""
    conn = _connect()
    row = conn.execute(
        "SELECT image_b64 FROM item_images WHERE item_id = ?", (item_id,)
    ).fetchone()
    conn.close()
    return row[0] if row else None
