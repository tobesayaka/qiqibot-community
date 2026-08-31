from nonebot.plugin import PluginMetadata

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="视频下载",
    description="解析并下载短视频平台的视频",
    usage="/video <视频链接>",
    config=Config,
)


from . import handlers as handlers
