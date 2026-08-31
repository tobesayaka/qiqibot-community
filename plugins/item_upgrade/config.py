
from pydantic import BaseModel


class Config(BaseModel):
    item_upgrade_db: str = "data/item_upgrade.db"
    item_upgrade_search_limit: int = 10
