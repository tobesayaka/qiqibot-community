"""视频下载工具函数"""

import asyncio
import time
from pathlib import Path
from typing import Any

import yt_dlp


def _download_video_sync(
    url: str,
    save_dir: str = "downloads",
    proxy: str | None = None,
    cookies_from_browser: str | None = None,
) -> Path:
    save_path = Path(save_dir)
    save_path.mkdir(parents=True, exist_ok=True)

    timestamp = int(time.time())
    output_template = str(save_path / f"%(extractor)s_%(id)s_{timestamp}.%(ext)s")

    ydl_opts: dict[str, Any] = {
        "outtmpl": output_template,
        "quiet": True,
        "no_warnings": True,
        "merge_output_format": "mp4",
    }

    if proxy:
        ydl_opts["proxy"] = proxy

    if cookies_from_browser:
        ydl_opts["cookiesfrombrowser"] = (cookies_from_browser,)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore[arg-type]
        info = ydl.extract_info(url, download=True)
        if info is None:
            raise ValueError(f"无法解析链接: {url}")

        # requested_downloads 包含合并/转码后的实际文件路径
        requested = info.get("requested_downloads")
        if requested and len(requested) > 0:
            return Path(requested[0]["filepath"])

        # fallback: prepare_filename + glob 找实际文件
        stem = Path(ydl.prepare_filename(info)).stem
        matches = list(save_path.glob(f"{stem}.*"))
        if matches:
            return matches[0]

        return Path(ydl.prepare_filename(info))


async def download_video(
    url: str,
    save_dir: str = "downloads",
    proxy: str | None = None,
    cookies_from_browser: str | None = None,
) -> Path:
    try:
        return await asyncio.to_thread(
            _download_video_sync, url, save_dir, proxy, cookies_from_browser
        )
    except (OSError, ValueError) as e:
        raise ValueError(f"下载失败: {e}") from e
