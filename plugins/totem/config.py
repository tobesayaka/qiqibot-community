
from pydantic import BaseModel


class Config(BaseModel):
    totem_db: str = "data/totem.db"
    totem_search_limit: int = 10
