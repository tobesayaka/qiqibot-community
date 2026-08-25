from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name="使用帮助",
    description="查看各插件的使用方法",
    usage="帮助 / help / 怎么用 / 指令列表",
)

from . import handlers as handlers
