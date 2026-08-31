"""erinn 配方数据库工具函数。"""

from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path("data/erinn.db")

_conn: sqlite3.Connection | None = None


def get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(str(DB_PATH))
        _conn.row_factory = sqlite3.Row
    return _conn


def close_conn():
    global _conn
    if _conn is not None:
        _conn.close()
        _conn = None


def query_one(sql: str, params: tuple = ()) -> sqlite3.Row | None:
    return get_conn().execute(sql, params).fetchone()


def query_all(sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    return get_conn().execute(sql, params).fetchall()


def get_item_name(item_id: int) -> str:
    row = query_one("SELECT name FROM items WHERE item_id = ?", (item_id,))
    return row[0] if row else f"ID:{item_id}"


def get_item_image_b64(item_id: int) -> str | None:
    row = query_one("SELECT image_b64 FROM item_images WHERE item_id = ?", (item_id,))
    return row[0] if row else None


def get_skill_image_b64(skill_en: str) -> str | None:
    row = query_one(
        "SELECT si.image_b64 FROM skills s "
        "LEFT JOIN skill_images si ON s.skill_id = si.skill_id "
        "WHERE s.name_en = ?",
        (skill_en,),
    )
    return row[1] if row and row[1] else None


def get_npc_image_b64(npc_id: int) -> str | None:
    row = query_one("SELECT image_b64 FROM npc_images WHERE npc_id = ?", (npc_id,))
    return row[0] if row else None


def get_skill_cn(skill_en: str) -> str:
    row = query_one("SELECT name_cn FROM skills WHERE name_en = ?", (skill_en,))
    return row[0] if row else skill_en


async def search_items(keyword: str, limit: int = 10) -> list[dict]:
    """模糊搜索物品名称（有配方或有获取方式的物品）。"""
    if "*" in keyword:
        pattern = f"%{keyword.replace('*', '%')}%"
    else:
        parts = keyword.split()
        pattern = f"%{'%'.join(parts)}%"
    rows = query_all(
        "SELECT DISTINCT i.item_id, i.name FROM items i "
        "WHERE i.name LIKE ? "
        "AND (EXISTS (SELECT 1 FROM recipes r WHERE r.item_id = i.item_id) "
        "  OR EXISTS (SELECT 1 FROM acquisitions a WHERE a.item_id = i.item_id)) "
        "ORDER BY i.item_id LIMIT ?",
        (pattern, limit),
    )
    return [dict(r) for r in rows]


async def get_recipes(item_id: int) -> list[dict]:
    rows = query_all(
        "SELECT * FROM recipes WHERE item_id = ? ORDER BY skill_name", (item_id,)
    )
    return [dict(r) for r in rows]
