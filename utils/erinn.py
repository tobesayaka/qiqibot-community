"""erinn 配方数据库工具函数。"""

from __future__ import annotations

from pathlib import Path

from utils.db import query_one, query_all

DB_PATH = Path("data/erinn.db")


async def get_item_name(item_id: int) -> str:
    row = await query_one(DB_PATH, "SELECT name FROM items WHERE item_id = ?", (item_id,))
    return row["name"] if row else f"ID:{item_id}"


async def get_item_image_b64(item_id: int) -> str | None:
    row = await query_one(DB_PATH, "SELECT image_b64 FROM item_images WHERE item_id = ?", (item_id,))
    return row["image_b64"] if row else None


async def get_skill_image_b64(skill_en: str) -> str | None:
    row = await query_one(
        DB_PATH,
        "SELECT si.image_b64 FROM skills s "
        "LEFT JOIN skill_images si ON s.skill_id = si.skill_id "
        "WHERE s.name_en = ?",
        (skill_en,),
    )
    return row["image_b64"] if row and row["image_b64"] else None


async def get_npc_image_b64(npc_id: int) -> str | None:
    row = await query_one(DB_PATH, "SELECT image_b64 FROM npc_images WHERE npc_id = ?", (npc_id,))
    return row["image_b64"] if row else None


async def get_skill_cn(skill_en: str) -> str:
    row = await query_one(DB_PATH, "SELECT name_cn FROM skills WHERE name_en = ?", (skill_en,))
    return row["name_cn"] if row else skill_en


async def search_items(keyword: str, limit: int = 10) -> list[dict]:
    """模糊搜索物品名称（有配方或有获取方式的物品）。"""
    if "*" in keyword:
        pattern = f"%{keyword.replace('*', '%')}%"
    else:
        parts = keyword.split()
        pattern = f"%{'%'.join(parts)}%"
    return await query_all(
        DB_PATH,
        "SELECT DISTINCT i.item_id, i.name FROM items i "
        "WHERE i.name LIKE ? "
        "AND (EXISTS (SELECT 1 FROM recipes r WHERE r.item_id = i.item_id) "
        "  OR EXISTS (SELECT 1 FROM acquisitions a WHERE a.item_id = i.item_id)) "
        "ORDER BY i.item_id LIMIT ?",
        (pattern, limit),
    )


async def get_recipes(item_id: int) -> list[dict]:
    return await query_all(
        DB_PATH,
        "SELECT * FROM recipes WHERE item_id = ? ORDER BY skill_name",
        (item_id,),
    )


async def query_all_raw(sql: str, params: tuple = ()) -> list[dict]:
    """通用查询（供 handlers 中的复杂查询使用）。"""
    return await query_all(DB_PATH, sql, params)


async def query_one_raw(sql: str, params: tuple = ()) -> dict | None:
    """通用单条查询。"""
    return await query_one(DB_PATH, sql, params)
