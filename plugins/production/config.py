from pydantic import BaseModel


class Config(BaseModel):
    production_db: str = "data/production.db"
    production_search_limit: int = 10
    production_font: str = "/Users/ming/Library/Fonts/NotoSansSC.ttf"
