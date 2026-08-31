from nonebot import get_driver
from nonebot.plugin import PluginMetadata

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="爱琳配方百科",
    description="查询洛奇游戏中的制作配方，支持 20+ 种技能",
    usage="erinn <关键词/ID>",
    config=Config,
)


from . import handlers as handlers

driver = get_driver()


@driver.on_shutdown
async def _shutdown():
    from utils.erinn import close_conn

    close_conn()
