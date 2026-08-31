from __future__ import annotations

import base64
import io
import json

from nonebot import on_regex
from nonebot.adapters.onebot.v11 import MessageEvent, MessageSegment
from nonebot.typing import T_State
from PIL import Image, ImageDraw, ImageFont

from utils.config import GlobalConfig
from utils.permission import is_allowed
from utils.totem import get_totem, get_totem_image, search_totems

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

_FONT_SIZE = 18
_LINE_SPACING = 6
_PADDING = 16
_ICON_SIZE = 64
_ICON_PAD = 8
_BG = (28, 28, 32)
_TITLE_BG = (45, 50, 62)
_TEXT = (210, 225, 240)
_DIM = (140, 140, 145)
_ACCENT = (100, 200, 255)
_WHITE = (255, 255, 255)
_TAG_YES = (100, 220, 140)
_TAG_NO = (255, 100, 100)

# totem <id> → 精准查询
totem_id = on_regex(r"\Atotem\s+(\d+)\Z", priority=14, block=True, rule=is_allowed())

# totem <关键词> → 模糊搜索
totem_search = on_regex(r"\Atotem\s+(\D.*)\Z", priority=15, block=True, rule=is_allowed())


@totem_id.handle()
async def handle_totem_id(event: MessageEvent, state: T_State):
    tid = int(state["_matched"].group(1))
    info = await get_totem(tid)
    if not info:
        await totem_id.finish(f"没找到 ID {tid} 的图腾")
    await totem_id.finish(MessageSegment.image(await _render(info)))


@totem_search.handle()
async def handle_totem_search(event: MessageEvent, state: T_State):
    keyword: str = state["_matched"].group(1).strip()
    if not keyword:
        return

    results = await search_totems(keyword, limit=config.totem_search_limit)
    if not results:
        await totem_search.finish(f"没找到和\"{keyword}\"相关的图腾")

    if len(results) == 1:
        await totem_search.finish(MessageSegment.image(await _render(results[0])))

    lines = [
        f"totem {r['id']} | {r['name']} [{r['totem_type']}]"
        for r in results
    ]
    await totem_search.finish(f"找到 {len(results)} 个：\n" + "\n".join(lines))


async def _load_icon(totem_id: int) -> Image.Image | None:
    b64 = await get_totem_image(totem_id)
    if not b64:
        return None
    try:
        raw = base64.b64decode(b64)
        return Image.open(io.BytesIO(raw)).convert("RGBA")
    except (OSError, ValueError):
        return None


async def _render(info: dict) -> str:
    """渲染图腾信息为图片，返回 base64 data URI。"""
    font = ImageFont.truetype(global_cfg.qiqibot_font, _FONT_SIZE)
    icon = await _load_icon(info["id"])

    tmp = Image.new("RGB", (1, 1))
    td = ImageDraw.Draw(tmp)
    _, text_h = _text_size(td, "测", font)
    line_h = text_h + _LINE_SPACING

    bonuses = json.loads(info.get("bonuses", "[]"))

    # 构建文本行
    lines: list[tuple[str, tuple[int, int, int]]] = []
    lines.append((f"{info['name']}  ID:{info['id']}", _WHITE))
    lines.append((f"类型: {info['totem_type']}", _ACCENT))

    # 标签行
    tags = []
    tags.append("额外图腾" if info.get("is_extra") else None)
    tags.append("宠物图腾" if info.get("is_pet") else None)
    tags.append("可拍卖" if info.get("auction_searchable") else None)
    tag_str = " | ".join(t for t in tags if t)
    if tag_str:
        lines.append((tag_str, _DIM))

    # 属性加成
    if bonuses:
        lines.append(("属性加成:", _TEXT))
        for b in bonuses:
            val = str(b["min"]) if b["min"] == b["max"] else f"{b['min']}~{b['max']}"
            lines.append((f"  {b['stat_name']}: +{val}", _TEXT))

    # 计算尺寸
    icon_indent = _ICON_SIZE + _ICON_PAD if icon else 0
    max_text_w = 0
    for text, _ in lines:
        w, _ = _text_size(td, text, font)
        max_text_w = max(max_text_w, w)

    img_w = _PADDING * 2 + icon_indent + max_text_w + 16
    img_w = max(img_w, 400)
    img_h = _PADDING + len(lines) * line_h + _PADDING

    # 绘制
    img = Image.new("RGB", (img_w, img_h), _BG)
    draw = ImageDraw.Draw(img)
    draw.rectangle([_PADDING - 4, _PADDING - 2, img_w - _PADDING + 4, img_h - _PADDING + 2], fill=_TITLE_BG)

    if icon:
        area_h = img_h - _PADDING * 2
        scale = min(_ICON_SIZE / icon.width, area_h / icon.height)
        scaled = icon.resize((int(icon.width * scale), int(icon.height * scale)), Image.Resampling.LANCZOS)
        ix = _PADDING + (_ICON_SIZE - scaled.width) // 2
        iy = _PADDING + (area_h - scaled.height) // 2
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
