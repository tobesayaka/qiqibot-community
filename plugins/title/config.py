from pydantic import BaseModel


class Config(BaseModel):
    title_db: str = "data/title.db"
    title_search_limit: int = 10
    title_font: str = "/Users/ming/Library/Fonts/NotoSansSC.ttf"
