from nonebot.plugin import PluginMetadata

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="制作配方查询",
    description="查询游戏制作配方信息",
    usage="prd <关键词> 搜索 / prd <id> 查看详情",
    config=Config,
)


from . import handlers as handlers
