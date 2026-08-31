from nonebot.plugin import PluginMetadata

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="图腾查询",
    description="查询洛奇游戏图腾信息",
    usage="totem <关键词> 搜索 / totem <id> 查看详情",
    config=Config,
)


from . import handlers as handlers
