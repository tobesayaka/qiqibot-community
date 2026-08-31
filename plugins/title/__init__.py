from nonebot.plugin import PluginMetadata

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="头衔查询",
    description="查询洛奇游戏头衔信息",
    usage="title <关键词> 搜索 / title <id> 查看详情",
    config=Config,
)


from . import handlers as handlers
