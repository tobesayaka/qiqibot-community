from pydantic import BaseModel


class Config(BaseModel):
    video_proxy: str | None = None
    video_cookies_browser: str | None = "chrome"
    video_save_dir: str = "downloads"
