from pydantic import BaseModel


class Config(BaseModel):
    """Demo 插件配置"""

    demo_enabled: bool = True
    demo_echo: bool = True
