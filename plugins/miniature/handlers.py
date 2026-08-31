from __future__ import annotations

import base64
import io

from nonebot import on_regex
from nonebot.adapters.onebot.v11 import MessageEvent, MessageSegment
from nonebot.typing import T_State
from PIL import Image, ImageDraw, ImageFont

from utils.config import GlobalConfig
from utils.miniature import get_miniature, get_miniature_image, search_miniatures
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

# mini <id> → 精准查询
mini_id = on_regex(r"\Amini\s+(\d+)\Z", priority=14, block=True, rule=is_allowed())

# mini <关键词> → 模糊搜索
mini_search = on_regex(r"\Amini\s+(\D.*)\Z", priority=15, block=True, rule=is_allowed())


@mini_id.handle()
async def handle_mini_id(event: MessageEvent, state: T_State):
    mid = int(state["_matched"].group(1))
    info = await get_miniature(mid)
    if not info:
        await mini_id.finish(f"没找到 ID {mid} 的农场物")
    await mini_id.finish(MessageSegment.image(await _render(info)))


@mini_search.handle()
async def handle_mini_search(event: MessageEvent, state: T_State):
    keyword: str = state["_matched"].group(1).strip()
    if not keyword:
        return

    results = await search_miniatures(keyword, limit=config.miniature_search_limit)
    if not results:
        await mini_search.finish(f"没找到和\"{keyword}\"相关的农场物")

    if len(results) == 1:
        await mini_search.finish(MessageSegment.image(await _render(results[0])))

    lines = [
        f"mini {r['id']} | {r['name']}"
        for r in results
    ]
    await mini_search.finish(f"找到 {len(results)} 个：\n" + "\n".join(lines))


async def _load_icon(mini_id: int) -> Image.Image | None:
    b64 = await get_miniature_image(mini_id)
    if not b64:
        return None
    try:
        raw = base64.b64decode(b64)
        return Image.open(io.BytesIO(raw)).convert("RGBA")
    except (OSError, ValueError):
        return None


async def _render(info: dict) -> str:
    """渲染农场物信息为图片，返回 base64 data URI。"""
    font = ImageFont.truetype(global_cfg.qiqibot_font, _FONT_SIZE)
    icon = await _load_icon(info["id"])

    tmp = Image.new("RGB", (1, 1))
    td = ImageDraw.Draw(tmp)
    _, text_h = _text_size(td, "测", font)
    line_h = text_h + _LINE_SPACING

    # 构建文本行
    lines: list[tuple[str, tuple[int, int, int]]] = []
    lines.append((f"{info['name']}  ID:{info['id']}", _WHITE))

    type_label = "额外农场物" if info.get("is_extra") else "普通农场物"
    auction = "可拍卖" if info.get("auction_searchable") else "不可拍卖"
    lines.append((f"{type_label} | {auction}", _DIM))

    if info.get("desc"):
        for dl in info["desc"].split("\n"):
            if dl.strip():
                lines.append((dl.strip(), _DIM))

    bonus_text = info.get("bonus_text", "")
    if bonus_text:
        lines.append(("属性加成:", _TEXT))
        for part in bonus_text.split(", "):
            lines.append((f"  {part}", _ACCENT))

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
