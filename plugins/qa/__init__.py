from nonebot.plugin import PluginMetadata

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="QA 知识库",
    description="通过聊天框管理问答知识库，支持文字+图片",
    usage="qa 问题|答案 · qa 关键词 · #id · qa edit id|答案 · qa del id",
    config=Config,
)


from . import handlers as handlers
