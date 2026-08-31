"""全局共享配置，通过 .env 文件加载。"""

from pydantic import BaseModel


class GlobalConfig(BaseModel):
    qiqibot_font: str = "assets/fonts/NotoSansSC.ttf"
