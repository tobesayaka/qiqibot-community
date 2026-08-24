from __future__ import annotations

import asyncio
import base64
import logging
from pathlib import Path

from nonebot import get_bot, on_regex
from nonebot.adapters.onebot.v11 import (
    MessageEvent,
    MessageSegment,
)
from nonebot.adapters.onebot.v11.exception import NetworkError
from nonebot.typing import T_State

from utils.video import download_video
from utils.permission import is_allowed

from .config import Config

try:
    from nonebot import get_plugin_config

    config = get_plugin_config(Config)
except (ValueError, RuntimeError):
    config = Config()

logger = logging.getLogger("plugins.video")
video = on_regex(r"\A下载\s*(https?://\S+)", priority=10, block=True, rule=is_allowed())


async def _download_and_send(
    bot,
    event: MessageEvent,
    url: str,
):
    video_path: Path | None = None
    try:
        video_path = await download_video(
            url,
            save_dir=config.video_save_dir,
            proxy=config.video_proxy,
            cookies_from_browser=config.video_cookies_browser,
        )

        if not video_path.exists():
            await bot.send(event=event, message="好像下载出问题了，文件没找到")
            return

        # OneBot 实现跑在 Docker 里，无法直接读取宿主机文件路径
        # 用 base64 data URI 传文件内容
        file_bytes = await asyncio.to_thread(video_path.read_bytes)
        b64 = base64.b64encode(file_bytes).decode()
        suffix = video_path.suffix.lstrip(".")
        mime = "video/mp4" if suffix == "mp4" else f"video/{suffix}"
        data_uri = f"data:{mime};base64,{b64}"
        await bot.send(event=event, message=MessageSegment.video(file=data_uri))
    except Exception as e:
        logger.error(f"视频下载任务异常: {e}", exc_info=True)
        try:
            await bot.send(event=event, message=f"下载出了点问题：{e}")
        except Exception:
            pass
    finally:
        # 清理下载的临时文件
        if video_path and video_path.exists():
            try:
                await asyncio.to_thread(video_path.unlink)
            except OSError:
                pass


@video.handle()
async def handle_video(event: MessageEvent, state: T_State):
    url: str = state["_matched"].group(1).strip()
    try:
        await video.send("看看这个视频...")
    except NetworkError:
        pass

    asyncio.create_task(_download_and_send(get_bot(), event, url))
