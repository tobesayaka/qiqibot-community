from pydantic import BaseModel


class Config(BaseModel):
    qa_list_limit: int = 10
    qa_max_images: int = 5
