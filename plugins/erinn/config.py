from pydantic import BaseModel


class Config(BaseModel):
    erinn_search_limit: int = 10
