from nonebot import get_plugin_config
from nonebot.plugin import PluginMetadata

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="Demo 插件",
    description="一个简单的示例插件，演示 NoneBot2 插件开发",
    usage="/echo <内容> - 复读消息",
    config=Config,
)

config = get_plugin_config(Config)

from . import handlers as handlers
