"""图腾数据库工具函数。

数据通过 scripts/fetch_totem.py 从 prilus 资源服务器下载写入 SQLite。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path("data/totem.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


async def search_totems(keyword: str, limit: int = 10) -> list[dict]:
    """模糊搜索图腾名称。

    两种模式：
    - 通配符模式：含 * 时直接作为通配符
    - 分词模式：空格分隔，按顺序匹配
    """
    conn = _connect()
    if "*" in keyword:
        pattern = f"%{keyword.replace('*', '%')}%"
    else:
        parts = keyword.split()
        pattern = f"%{'%'.join(parts)}%"
    rows = conn.execute(
        "SELECT * FROM totems WHERE name LIKE ? ORDER BY id LIMIT ?",
        (pattern, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


async def get_totem(totem_id: int) -> dict | None:
    """按 ID 获取图腾。"""
    conn = _connect()
    row = conn.execute("SELECT * FROM totems WHERE id = ?", (totem_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


async def get_totem_image(totem_id: int) -> str | None:
    """获取图腾图片的 base64 编码。"""
    conn = _connect()
    row = conn.execute(
        "SELECT image_b64 FROM totem_images WHERE id = ?", (totem_id,)
    ).fetchone()
    conn.close()
    return row[0] if row else None
