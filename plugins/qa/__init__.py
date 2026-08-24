from nonebot import get_plugin_config
from nonebot.plugin import PluginMetadata

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="QA 知识库",
    description="通过聊天框管理问答知识库，支持文字+图片",
    usage="/qa add|list|find|get|edit|del|help",
    config=Config,
)

config = get_plugin_config(Config)

from . import handlers as handlers
