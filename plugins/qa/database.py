from pathlib import Path

from nonebot import get_driver
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .models import Base

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
_DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = _DATA_DIR / "qa.db"
ENGINE = create_async_engine(f"sqlite+aiosqlite:///{DB_PATH}", echo=False)
async_session = async_sessionmaker(ENGINE, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    async with ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


driver = get_driver()


@driver.on_startup
async def _startup():
    await init_db()
