"""装备改造数据库工具函数。

数据通过 scripts/fetch_item_upgrade.py 从 prilus 资源服务器下载写入 SQLite。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path("data/item_upgrade.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


async def search_item_upgrades(keyword: str, limit: int = 10) -> list[dict]:
    """模糊搜索可改造物品名称。

    两种模式：
    - 通配符模式：含 * 时直接作为通配符，如 "释魂*弓" → LIKE '%释魂%弓%'
    - 分词模式：空格分隔，按顺序匹配，如 "释魂 弓" → LIKE '%释魂%弓%'
    """
    conn = _connect()
    if "*" in keyword:
        pattern = f"%{keyword.replace('*', '%')}%"
    else:
        parts = keyword.split()
        pattern = f"%{'%'.join(parts)}%"
    rows = conn.execute(
        "SELECT * FROM item_upgrades WHERE name LIKE ? ORDER BY item_id LIMIT ?",
        (pattern, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


async def get_item_upgrades(item_id: int) -> dict | None:
    """按物品 ID 获取改造信息（含全部改造项详情）。"""
    conn = _connect()
    ext = conn.execute(
        "SELECT * FROM item_upgrades WHERE item_id = ?", (item_id,)
    ).fetchone()
    if not ext:
        conn.close()
        return None

    ext = dict(ext)
    import json

    upgrade_ids = json.loads(ext["upgrade_ids"])
    if not upgrade_ids:
        ext["upgrades"] = []
        conn.close()
        return ext

    placeholders = ",".join("?" * len(upgrade_ids))
    rows = conn.execute(
        f"SELECT * FROM upgrades WHERE id IN ({placeholders})",
        upgrade_ids,
    ).fetchall()
    ext["upgrades"] = [dict(r) for r in rows]
    conn.close()
    return ext


async def get_upgrade(upgrade_id: int) -> dict | None:
    """按改造项 ID 获取单条改造详情。"""
    conn = _connect()
    row = conn.execute(
        "SELECT * FROM upgrades WHERE id = ?", (upgrade_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


async def get_item_image(item_id: int) -> str | None:
    """获取装备图片的 base64 编码。"""
    conn = _connect()
    row = conn.execute(
        "SELECT image_b64 FROM item_images WHERE item_id = ?", (item_id,)
    ).fetchone()
    conn.close()
    return row[0] if row else None
