"""头衔数据库工具函数。

数据通过 scripts/fetch_title.py 从 prilus 资源服务器下载写入 SQLite。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path("data/title.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


async def search_titles(keyword: str, limit: int = 10) -> list[dict]:
    """模糊搜索头衔名称和效果。

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
        "SELECT * FROM titles WHERE (display_name LIKE ? OR effect LIKE ?) ORDER BY type, id LIMIT ?",
        (pattern, pattern, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


async def get_title(title_id: int) -> dict | None:
    """按 ID 获取头衔。"""
    conn = _connect()
    row = conn.execute("SELECT * FROM titles WHERE id = ?", (title_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


async def get_title_image(title_id: int) -> str | None:
    """获取头衔图片的 base64 编码。"""
    conn = _connect()
    row = conn.execute(
        "SELECT image_b64 FROM title_images WHERE id = ?", (title_id,)
    ).fetchone()
    conn.close()
    return row[0] if row else None
