from __future__ import annotations

import base64
import io

from nonebot import on_regex
from nonebot.adapters.onebot.v11 import MessageEvent, MessageSegment
from nonebot.typing import T_State
from PIL import Image, ImageDraw, ImageFont

from utils.title import get_title, get_title_image, search_titles
from utils.permission import is_allowed

from .config import Config

try:
    from nonebot import get_plugin_config

    config = get_plugin_config(Config)
except (ValueError, RuntimeError):
    config = Config()

_FONT_SIZE = 18
_LINE_SPACING = 6
_PADDING = 16
_ICON_W = 50
_ICON_H = 75
_ICON_PAD = 8
_BG = (28, 28, 32)
_TITLE_BG = (45, 50, 62)
_TEXT = (210, 225, 240)
_DIM = (140, 140, 145)
_ACCENT = (100, 200, 255)
_EFFECT = (130, 200, 255)
_WARN = (255, 100, 100)
_WHITE = (255, 255, 255)

# title <id> → 精准查询
title_id = on_regex(r"\Atitle\s+(\d+)\Z", priority=14, block=True, rule=is_allowed())

# title <关键词> → 模糊搜索
title_search = on_regex(r"\Atitle\s+(\D.*)\Z", priority=15, block=True, rule=is_allowed())


@title_id.handle()
async def handle_title_id(event: MessageEvent, state: T_State):
    tid = int(state["_matched"].group(1))
    info = await get_title(tid)
    if not info:
        await title_id.finish(f"没找到 ID {tid} 的头衔")
    await title_id.finish(MessageSegment.image(await _render(info)))


@title_search.handle()
async def handle_title_search(event: MessageEvent, state: T_State):
    keyword: str = state["_matched"].group(1).strip()
    if not keyword:
        return

    results = await search_titles(keyword, limit=config.title_search_limit)
    if not results:
        await title_search.finish(f"没找到和\"{keyword}\"相关的头衔")

    if len(results) == 1:
        await title_search.finish(MessageSegment.image(await _render(results[0])))

    lines = [
        f"title {r['id']} | [{r['type_text']}] {r['display_name']}"
        for r in results
    ]
    await title_search.finish(f"找到 {len(results)} 个：\n" + "\n".join(lines))


async def _render(info: dict) -> str:
    """渲染头衔信息为图片，返回 base64 data URI。"""
    font = ImageFont.truetype(config.title_font, _FONT_SIZE)

    title_img_b64 = await get_title_image(info["id"])
    icon = None
    if title_img_b64:
        try:
            raw = base64.b64decode(title_img_b64)
            icon = Image.open(io.BytesIO(raw)).convert("RGBA")
        except Exception:
            pass

    tmp = Image.new("RGB", (1, 1))
    td = ImageDraw.Draw(tmp)
    _, text_h = _text_size(td, "测", font)
    line_h = text_h + _LINE_SPACING

    # 构建文本行
    lines: list[tuple[str, tuple[int, int, int]]] = []
    type_label = info.get("type_text", "")
    name_line = f"{info['display_name']}  ID:{info['id']}  [{type_label}]"
    lines.append((name_line, _WHITE))

    if info.get("duration"):
        lines.append((f"持续时间: {info['duration']}秒", _ACCENT))

    effect = info.get("effect", "")
    if effect:
        for seg in effect.split("\n"):
            seg = seg.strip()
            if not seg:
                continue
            color = _WARN if seg.startswith("[") else _EFFECT
            lines.append((seg, color))

    # 计算尺寸
    icon_indent = _ICON_W + _ICON_PAD if icon else 0
    max_text_w = 0
    for text, _ in lines:
        w, _ = _text_size(td, text, font)
        max_text_w = max(max_text_w, w)

    img_w = _PADDING * 2 + icon_indent + max_text_w + 16
    img_w = max(img_w, 360)
    img_h = _PADDING + len(lines) * line_h + _PADDING

    # 绘制
    img = Image.new("RGB", (img_w, img_h), _BG)
    draw = ImageDraw.Draw(img)

    draw.rectangle([_PADDING - 4, _PADDING - 2, img_w - _PADDING + 4, img_h - _PADDING + 2], fill=_TITLE_BG)

    if icon:
        # 缩放图标到固定区域
        scale = min(_ICON_W / icon.width, _ICON_H / icon.height)
        scaled = icon.resize((int(icon.width * scale), int(icon.height * scale)), Image.Resampling.LANCZOS)
        ix = _PADDING + (_ICON_W - scaled.width) // 2
        iy = _PADDING + (img_h - 2 * _PADDING - scaled.height) // 2
        img.paste(scaled, (ix, iy), scaled)

    y = _PADDING
    tx = _PADDING + icon_indent
    for text, color in lines:
        draw.text((tx, y), text, fill=color, font=font)
        y += line_h

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return f"base64://{base64.b64encode(buf.getvalue()).decode()}"


def _text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]
