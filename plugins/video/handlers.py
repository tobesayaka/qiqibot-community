from __future__ import annotations

import asyncio
import base64
import logging
from pathlib import Path

import httpx
from nonebot import get_bot, on_regex
from nonebot.adapters.onebot.v11 import (
    MessageEvent,
    MessageSegment,
)
from nonebot.adapters.onebot.v11.exception import NetworkError
from nonebot.typing import T_State

from utils.permission import is_allowed
from utils.video import download_video

from .config import Config

try:
    from nonebot import get_plugin_config

    config = get_plugin_config(Config)
except (ValueError, RuntimeError):
    config = Config()

logger = logging.getLogger("plugins.video")
video = on_regex(r"\A下载\s*(https?://\S+)", priority=10, block=True, rule=is_allowed())


async def _send_via_http(event: MessageEvent, file_bytes: bytes, mime: str) -> bool:
    """通过 HTTP API 发送视频，绕过 WebSocket 大小限制。"""
    api_url = config.video_http_api_url
    token = config.video_http_api_token

    b64 = base64.b64encode(file_bytes).decode()
    data_uri = f"data:{mime};base64,{b64}"

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    if hasattr(event, "group_id"):
        endpoint = f"{api_url}/send_group_msg"
        payload = {
            "group_id": event.group_id,
            "message": [{"type": "video", "data": {"file": data_uri}}],
        }
    else:
        endpoint = f"{api_url}/send_private_msg"
        payload = {
            "user_id": event.user_id,
            "message": [{"type": "video", "data": {"file": data_uri}}],
        }

    async with httpx.AsyncClient(timeout=300, follow_redirects=True) as client:
        resp = await client.post(endpoint, json=payload, headers=headers)
        resp.raise_for_status()
        result = resp.json()
        return result.get("status") == "ok" or result.get("retcode") == 0


async def _download_and_send(bot, event: MessageEvent, url: str):
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

        suffix = video_path.suffix.lstrip(".")
        mime = "video/mp4" if suffix == "mp4" else f"video/{suffix}"
        file_size = await asyncio.to_thread(video_path.stat().st_size)
        threshold = config.video_http_threshold_mb * 1024 * 1024

        if file_size > threshold:
            logger.info(f"文件 {file_size / 1024 / 1024:.1f}MB，使用 HTTP API 发送")
            file_bytes = await asyncio.to_thread(video_path.read_bytes)
            try:
                ok = await _send_via_http(event, file_bytes, mime)
                if ok:
                    await bot.send(event=event, message="视频发送成功")
                else:
                    await bot.send(event=event, message="视频发送失败")
            except (httpx.HTTPError, OSError) as e:
                logger.exception("HTTP API 发送失败")
                await bot.send(event=event, message=f"视频太大，发送失败：{e}")
        else:
            file_bytes = await asyncio.to_thread(video_path.read_bytes)
            b64 = base64.b64encode(file_bytes).decode()
            data_uri = f"data:{mime};base64,{b64}"
            await bot.send(event=event, message=MessageSegment.video(file=data_uri))

    except (ValueError, httpx.HTTPError, OSError) as e:
        logger.exception("视频下载任务异常")
        try:
            await bot.send(event=event, message=f"下载出了点问题：{e}")
        except Exception:  # noqa: BLE001, S110
            pass
    finally:
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

    task = asyncio.create_task(_download_and_send(get_bot(), event, url))
    task.add_done_callback(_handle_task_error)


def _handle_task_error(task: asyncio.Task):
    if task.cancelled():
        return
    exc = task.exception()
    if exc:
        logger.exception("视频下载任务未捕获异常", exc_info=exc)
