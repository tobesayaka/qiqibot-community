"""production 制作配方数据库工具函数。

数据通过 scripts/fetch_production.py 下载写入 SQLite。
"""

from __future__ import annotations

from pathlib import Path

from utils.db import query_one, query_all

DB_PATH = Path("data/production.db")


async def search_productions(keyword: str, limit: int = 10) -> list[dict]:
    """模糊搜索制作配方名称。"""
    if "*" in keyword:
        pattern = f"%{keyword.replace('*', '%')}%"
    else:
        parts = keyword.split()
        pattern = f"%{'%'.join(parts)}%"
    return await query_all(
        DB_PATH,
        "SELECT * FROM productions WHERE name LIKE ? ORDER BY item_id LIMIT ?",
        (pattern, limit),
    )


async def get_production(item_id: int) -> dict | None:
    """按成品物品 ID 获取配方。"""
    return await query_one(
        DB_PATH, "SELECT * FROM productions WHERE item_id = ?", (item_id,)
    )


async def get_item_image(item_id: int) -> str | None:
    """获取物品图片的 base64 编码。"""
    row = await query_one(
        DB_PATH, "SELECT image_b64 FROM item_images WHERE item_id = ?", (item_id,)
    )
    return row["image_b64"] if row else None
