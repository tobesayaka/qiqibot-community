from nonebot import on_regex
from nonebot.adapters.onebot.v11 import MessageEvent
from nonebot.typing import T_State

from utils.permission import is_allowed

echo = on_regex(r"\A复读\s*(.+)", priority=10, block=True, rule=is_allowed())


@echo.handle()
async def handle_echo(event: MessageEvent, state: T_State):
    text: str = state["_matched"].group(1).strip()
    if text:
        await echo.finish(text)
