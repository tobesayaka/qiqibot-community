from nonebot.plugin import PluginMetadata

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="道具查询",
    description="从 optionset 数据库模糊搜索游戏道具信息",
    usage="opt <关键词> 搜索 / opt <id> 查看详情",
    config=Config,
)


from . import handlers as handlers
