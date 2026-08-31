
from pydantic import BaseModel


class Config(BaseModel):
    production_db: str = "data/production.db"
    production_search_limit: int = 10
