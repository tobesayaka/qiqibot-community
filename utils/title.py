"""头衔数据库工具函数。

数据通过 scripts/fetch_title.py 从 prilus 资源服务器下载写入 SQLite。
"""

from __future__ import annotations

from pathlib import Path

from utils.db import query_one, query_all

DB_PATH = Path("data/title.db")


async def search_titles(keyword: str, limit: int = 10) -> list[dict]:
    """模糊搜索头衔名称和效果。"""
    if "*" in keyword:
        pattern = f"%{keyword.replace('*', '%')}%"
    else:
        parts = keyword.split()
        pattern = f"%{'%'.join(parts)}%"
    return await query_all(
        DB_PATH,
        "SELECT * FROM titles WHERE (display_name LIKE ? OR effect LIKE ?) ORDER BY type, id LIMIT ?",
        (pattern, pattern, limit),
    )


async def get_title(title_id: int) -> dict | None:
    """按 ID 获取头衔。"""
    return await query_one(DB_PATH, "SELECT * FROM titles WHERE id = ?", (title_id,))


async def get_title_image(title_id: int) -> str | None:
    """获取头衔图片的 base64 编码。"""
    row = await query_one(DB_PATH, "SELECT image_b64 FROM title_images WHERE id = ?", (title_id,))
    return row["image_b64"] if row else None
