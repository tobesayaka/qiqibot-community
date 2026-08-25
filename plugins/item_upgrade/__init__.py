from nonebot import get_plugin_config
from nonebot.plugin import PluginMetadata

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="装备改造查询",
    description="查询游戏装备改造信息",
    usage="up <关键词> 搜索 / up <id> 查看详情",
    config=Config,
)

config = get_plugin_config(Config)

from . import handlers as handlers
