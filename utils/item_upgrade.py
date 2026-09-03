"""装备改造数据库工具函数。

数据通过 scripts/fetch_item_upgrade.py 从 prilus 资源服务器下载写入 SQLite。
"""

from __future__ import annotations

import json
from pathlib import Path

from utils.db import query_one, query_all

DB_PATH = Path("data/item_upgrade.db")


async def search_item_upgrades(keyword: str, limit: int = 10) -> list[dict]:
    """模糊搜索可改造物品名称。"""
    if "*" in keyword:
        pattern = f"%{keyword.replace('*', '%')}%"
    else:
        parts = keyword.split()
        pattern = f"%{'%'.join(parts)}%"
    return await query_all(
        DB_PATH,
        "SELECT * FROM item_upgrades WHERE name LIKE ? ORDER BY item_id LIMIT ?",
        (pattern, limit),
    )


async def get_item_upgrades(item_id: int) -> dict | None:
    """按物品 ID 获取改造信息（含全部改造项详情）。"""
    ext = await query_one(DB_PATH, "SELECT * FROM item_upgrades WHERE item_id = ?", (item_id,))
    if not ext:
        return None

    upgrade_ids = json.loads(ext["upgrade_ids"])
    if not upgrade_ids:
        ext["upgrades"] = []
        return ext

    placeholders = ",".join("?" * len(upgrade_ids))
    upgrades = await query_all(
        DB_PATH,
        f"SELECT * FROM upgrades WHERE id IN ({placeholders})",
        tuple(upgrade_ids),
    )
    ext["upgrades"] = upgrades
    return ext


async def get_upgrade(upgrade_id: int) -> dict | None:
    """按改造项 ID 获取单条改造详情。"""
    return await query_one(DB_PATH, "SELECT * FROM upgrades WHERE id = ?", (upgrade_id,))


async def get_item_image(item_id: int) -> str | None:
    """获取装备图片的 base64 编码。"""
    row = await query_one(DB_PATH, "SELECT image_b64 FROM item_images WHERE item_id = ?", (item_id,))
    return row["image_b64"] if row else None
