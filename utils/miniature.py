"""农场物数据库工具函数。

数据通过 scripts/fetch_miniature.py 从 prilus 资源服务器下载写入 SQLite。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path("data/miniature.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


async def search_miniatures(keyword: str, limit: int = 10) -> list[dict]:
    """模糊搜索农场物名称。"""
    conn = _connect()
    if "*" in keyword:
        pattern = f"%{keyword.replace('*', '%')}%"
    else:
        parts = keyword.split()
        pattern = f"%{'%'.join(parts)}%"
    rows = conn.execute(
        "SELECT * FROM miniatures WHERE name LIKE ? ORDER BY id LIMIT ?",
        (pattern, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


async def get_miniature(miniature_id: int) -> dict | None:
    """按 ID 获取农场物。"""
    conn = _connect()
    row = conn.execute("SELECT * FROM miniatures WHERE id = ?", (miniature_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


async def get_miniature_image(miniature_id: int) -> str | None:
    """获取农场物图片的 base64 编码。"""
    conn = _connect()
    row = conn.execute(
        "SELECT image_b64 FROM miniature_images WHERE id = ?", (miniature_id,)
    ).fetchone()
    conn.close()
    return row[0] if row else None
