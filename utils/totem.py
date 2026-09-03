"""图腾数据库工具函数。

数据通过 scripts/fetch_totem.py 从 prilus 资源服务器下载写入 SQLite。
"""

from __future__ import annotations

from pathlib import Path

from utils.db import query_one, query_all

DB_PATH = Path("data/totem.db")


async def search_totems(keyword: str, limit: int = 10) -> list[dict]:
    """模糊搜索图腾名称。"""
    if "*" in keyword:
        pattern = f"%{keyword.replace('*', '%')}%"
    else:
        parts = keyword.split()
        pattern = f"%{'%'.join(parts)}%"
    return await query_all(
        DB_PATH,
        "SELECT * FROM totems WHERE name LIKE ? ORDER BY id LIMIT ?",
        (pattern, limit),
    )


async def get_totem(totem_id: int) -> dict | None:
    """按 ID 获取图腾。"""
    return await query_one(DB_PATH, "SELECT * FROM totems WHERE id = ?", (totem_id,))


async def get_totem_image(totem_id: int) -> str | None:
    """获取图腾图片的 base64 编码。"""
    row = await query_one(DB_PATH, "SELECT image_b64 FROM totem_images WHERE id = ?", (totem_id,))
    return row["image_b64"] if row else None
