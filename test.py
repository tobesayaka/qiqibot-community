"""视频下载功能测试脚本"""

import asyncio

from utils.video import download_video

# 代理配置（用于访问 X/YouTube 等需要翻墙的网站）
PROXY = "http://127.0.0.1:7890"

# 浏览器配置（用于读取 cookies，抖音等平台需要）
COOKIES_FROM_BROWSER = "chrome"


async def main():
    url = input("请输入视频分享链接: ").strip()
    if not url:
        print("链接不能为空")
        return

    print(f"开始下载: {url}")
    try:
        video_path = await download_video(
            url, proxy=PROXY, cookies_from_browser=COOKIES_FROM_BROWSER
        )
        print(f"下载成功: {video_path}")
    except Exception as e:
        print(f"下载失败: {e}")


if __name__ == "__main__":
    asyncio.run(main())
