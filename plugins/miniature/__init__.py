from nonebot import get_plugin_config
from nonebot.plugin import PluginMetadata

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="农场物查询",
    description="查询洛奇游戏农场物信息",
    usage="mini <关键词> 搜索 / mini <id> 查看详情",
    config=Config,
)

config = get_plugin_config(Config)

from . import handlers as handlers
