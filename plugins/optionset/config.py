from pydantic import BaseModel


class Config(BaseModel):
    optionset_db: str = "data/optionset.db"
    optionset_search_limit: int = 10
    optionset_font: str = "/Users/ming/Library/Fonts/NotoSansSC.ttf"
