"""共享数据库工具，提供 aiosqlite 连接管理。"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

import aiosqlite


@asynccontextmanager
async def open_db(db_path: Path) -> AsyncIterator[aiosqlite.Connection]:
    conn = await aiosqlite.connect(str(db_path))
    conn.row_factory = aiosqlite.Row
    try:
        yield conn
    finally:
        await conn.close()


async def query_one(db_path: Path, sql: str, params: tuple = ()) -> dict | None:
    async with open_db(db_path) as conn:
        cursor = await conn.execute(sql, params)
        row = await cursor.fetchone()
        return dict(row) if row else None


async def query_all(db_path: Path, sql: str, params: tuple = ()) -> list[dict]:
    async with open_db(db_path) as conn:
        cursor = await conn.execute(sql, params)
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
