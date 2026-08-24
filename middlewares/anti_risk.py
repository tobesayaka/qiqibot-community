from __future__ import annotations

import asyncio
import random

from nonebot.matcher import Matcher
from nonebot.message import run_preprocessor


@run_preprocessor
async def anti_risk_delay(matcher: Matcher):
    """给消息类 handler 加随机延迟，降低 QQ 风控检测概率。"""
    if matcher.type == "message":
        await asyncio.sleep(random.uniform(0.5, 2.0))
