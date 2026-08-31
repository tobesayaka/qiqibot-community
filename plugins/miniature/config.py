
from pydantic import BaseModel


class Config(BaseModel):
    miniature_db: str = "data/miniature.db"
    miniature_search_limit: int = 10
