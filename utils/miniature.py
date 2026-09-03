"""农场物数据库工具函数。

数据通过 scripts/fetch_miniature.py 从 prilus 资源服务器下载写入 SQLite。
"""

from __future__ import annotations

from pathlib import Path

from utils.db import query_one, query_all

DB_PATH = Path("data/miniature.db")


async def search_miniatures(keyword: str, limit: int = 10) -> list[dict]:
    """模糊搜索农场物名称。"""
    if "*" in keyword:
        pattern = f"%{keyword.replace('*', '%')}%"
    else:
        parts = keyword.split()
        pattern = f"%{'%'.join(parts)}%"
    return await query_all(
        DB_PATH,
        "SELECT * FROM miniatures WHERE name LIKE ? ORDER BY id LIMIT ?",
        (pattern, limit),
    )


async def get_miniature(miniature_id: int) -> dict | None:
    """按 ID 获取农场物。"""
    return await query_one(DB_PATH, "SELECT * FROM miniatures WHERE id = ?", (miniature_id,))


async def get_miniature_image(miniature_id: int) -> str | None:
    """获取农场物图片的 base64 编码。"""
    row = await query_one(
        DB_PATH, "SELECT image_b64 FROM miniature_images WHERE id = ?", (miniature_id,)
    )
    return row["image_b64"] if row else None
