from __future__ import annotations

import base64
import io

from nonebot import on_regex
from nonebot.adapters.onebot.v11 import MessageEvent, MessageSegment
from nonebot.typing import T_State
from PIL import Image, ImageDraw, ImageFont

from utils.config import GlobalConfig
from utils.optionset import get_item, search_items
from utils.permission import is_allowed

from .config import Config

try:
    from nonebot import get_plugin_config

    config = get_plugin_config(Config)
except (ValueError, RuntimeError):
    config = Config()
try:
    global_cfg = get_plugin_config(GlobalConfig)
except (ValueError, RuntimeError):
    global_cfg = GlobalConfig()

_FONT_SIZE = 22
_LINE_SPACING = 8
_PADDING = 24
_BG_COLOR = (30, 30, 30)
_TITLE_COLOR = (255, 255, 255)
_TEXT_COLOR = (173, 216, 230)
_WARN_COLOR = (255, 80, 80)

# opt <id> → 精准查询（优先级更高，先匹配纯数字）
opt_id = on_regex(r"\Aopt\s+(\d+)\Z", priority=14, block=True, rule=is_allowed())

# opt <关键词> → 模糊搜索
opt_search = on_regex(r"\Aopt\s+(\D.*)\Z", priority=15, block=True, rule=is_allowed())


@opt_id.handle()
async def handle_opt_id(event: MessageEvent, state: T_State):
    item_id = int(state["_matched"].group(1))
    item = await get_item(item_id)
    if not item:
        await opt_id.finish(f"没找到 ID {item_id} 的道具")
    await opt_id.finish(MessageSegment.image(_render_item(item)))


@opt_search.handle()
async def handle_opt_search(event: MessageEvent, state: T_State):
    keyword: str = state["_matched"].group(1).strip()
    if not keyword:
        return

    results = await search_items(keyword, limit=config.optionset_search_limit)
    if not results:
        await opt_search.finish(f"没找到和\"{keyword}\"相关的道具")

    if len(results) == 1:
        await opt_search.finish(MessageSegment.image(_render_item(results[0])))

    lines = [f"opt {r['id']} | [{r['usage_text']}]{r['name']}(Rank {r['level_text']})" for r in results]
    await opt_search.finish(
        f"找到 {len(results)} 个：\n" + "\n".join(lines)
    )


def _render_item(item: dict) -> str:
    """将道具信息渲染为图片，返回 base64 data URI。"""
    name = item.get("name", "未知")
    usage_text = item.get("usage_text", "")
    level_text = item.get("level_text", "")
    desc = item.get("desc", "")
    item_id = item.get("id", "")

    font = ImageFont.truetype(global_cfg.qiqibot_font, _FONT_SIZE)

    # 组装所有行: (text, color)
    styled_lines: list[tuple[str, tuple[int, int, int]]] = [
        (f"【{usage_text}】{name} {level_text}rank (ID: {item_id})", _TITLE_COLOR),
    ]
    if desc:
        for seg in desc.replace("\\n", "\n").split("\n"):
            color = _WARN_COLOR if seg.startswith("[") else _TEXT_COLOR
            styled_lines.append((seg, color))

    # 计算尺寸
    tmp_img = Image.new("RGB", (1, 1))
    tmp_draw = ImageDraw.Draw(tmp_img)
    max_w = 0
    line_heights: list[int] = []
    for text, _ in styled_lines:
        bbox = tmp_draw.textbbox((0, 0), text, font=font)
        max_w = max(max_w, bbox[2] - bbox[0])
        line_heights.append(bbox[3] - bbox[1])

    img_w = max_w + _PADDING * 2
    img_h = sum(line_heights) + _LINE_SPACING * (len(styled_lines) - 1) + _PADDING * 2

    # 绘制
    img = Image.new("RGB", (img_w, img_h), _BG_COLOR)
    draw = ImageDraw.Draw(img)

    y = _PADDING
    for i, ((text, color), lh) in enumerate(zip(styled_lines, line_heights)):
        draw.text((_PADDING, y), text, fill=color, font=font)
        y += lh + _LINE_SPACING

    # 转 base64
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return f"base64://{base64.b64encode(buf.getvalue()).decode()}"
