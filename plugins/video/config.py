from pydantic import BaseModel


class Config(BaseModel):
    video_proxy: str | None = None
    video_cookies_browser: str | None = "chrome"
    video_save_dir: str = "downloads"
    video_http_api_url: str = "http://127.0.0.1:3002"
    video_http_api_token: str = ""
    video_http_threshold_mb: int = 20
