from __future__ import annotations

import base64
import io
import json

from nonebot import on_regex
from nonebot.adapters.onebot.v11 import MessageEvent, MessageSegment
from nonebot.typing import T_State
from PIL import Image, ImageDraw, ImageFont

from utils.config import GlobalConfig
from utils.db import query_one
from utils.permission import is_allowed
from utils.production import DB_PATH, get_item_image, get_production, search_productions

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

_FONT_SIZE = 20
_MAT_ICON = 32
_ICON_LINE_H = 40  # 材料行高度，确保图标不重叠
_LINE_SPACING = 6
_PADDING = 16
_SECTION_GAP = 4
_DIVIDER_H = 1
_BG = (30, 30, 30)
_SECTION_BG = (40, 40, 45)
_DIVIDER = (60, 60, 65)
_TITLE = (255, 255, 255)
_TEXT = (200, 220, 235)
_DIM = (140, 140, 140)
_ACCENT = (100, 200, 255)
_LABEL = (160, 180, 200)
_LINK = (120, 180, 140)

_STAT_NAME_MAP = {
    "attack_min": "最小伤害",
    "attack_max": "最大伤害",
    "balance": "平衡",
    "critical": "暴击率",
    "defense": "防御",
    "dex": "敏捷",
    "durability_filled_max": "最大耐久",
    "int": "智力",
    "luck": "幸运",
    "magic_damage": "魔法攻击力",
    "magic_defense": "魔法防御力",
    "magic_protect": "魔法保护",
    "mana_recover": "魔法回复速度",
    "mana_reduce_percent": "魔法消耗减少%",
    "max_mana_increase": "最大魔力增加",
    "musicbuff_bonus": "音乐buff效果",
    "musicbuff_duration": "音乐buff持续时间",
    "protect": "保护",
    "str": "力量",
    "will": "意志",
    "astrologist_damage": "占星术伤害",
}

# prd <id> → 精准查询
prd_id = on_regex(r"\Aprd\s+(\d+)\Z", priority=14, block=True, rule=is_allowed())

# prd <关键词> → 模糊搜索
prd_search = on_regex(r"\Aprd\s+(\D.*)\Z", priority=15, block=True, rule=is_allowed())


@prd_id.handle()
async def handle_prd_id(event: MessageEvent, state: T_State):
    item_id = int(state["_matched"].group(1))
    prod = await get_production(item_id)
    if not prod:
        await prd_id.finish(f"没找到 ID {item_id} 的配方")
    await prd_id.finish(MessageSegment.image(await _render(prod)))


@prd_search.handle()
async def handle_prd_search(event: MessageEvent, state: T_State):
    keyword: str = state["_matched"].group(1).strip()
    if not keyword:
        return

    results = await search_productions(keyword, limit=config.production_search_limit)
    if not results:
        await prd_search.finish(f"没找到和\"{keyword}\"相关的配方")

    if len(results) == 1:
        await prd_search.finish(MessageSegment.image(await _render(results[0])))

    lines = [f"prd {r['item_id']} | {r['name']} [{r['type_text']}]{r['level_text']}" for r in results]
    await prd_search.finish(
        f"找到 {len(results)} 个：\n" + "\n".join(lines)
    )


# ── 图片渲染 ──────────────────────────────────────────


async def _load_icon(item_id: int, size: int | None = None) -> Image.Image | None:
    b64 = await get_item_image(item_id)
    if not b64:
        return None
    try:
        raw = base64.b64decode(b64)
        img = Image.open(io.BytesIO(raw)).convert("RGBA")
        if size:
            ratio = size / max(img.width, img.height)
            img = img.resize(
                (int(img.width * ratio), int(img.height * ratio)),
                Image.Resampling.LANCZOS,
            )
        return img
    except (OSError, ValueError):
        return None


def _text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _fmt_range(min_v: int, max_v: int) -> str:
    return str(min_v) if min_v == max_v else f"{min_v}~{max_v}"


async def _get_mat_recipe(item_id: int) -> str | None:
    """查询材料是否在 productions 表中有制作配方。"""
    row = await query_one(
        DB_PATH,
        "SELECT type_text, level_text FROM productions WHERE item_id = ?", (item_id,)
    )
    if row:
        return f"{row['type_text']} Rank{row['level_text']}"
    return None


async def _render(prod: dict) -> str:
    """渲染制作配方为图片，返回 base64 data URI。"""
    font = ImageFont.truetype(global_cfg.qiqibot_font, _FONT_SIZE)
    icon = await _load_icon(prod["item_id"])

    materials: list[dict] = json.loads(prod["materials"])
    finish_mats: list[dict] = json.loads(prod["finish_materials"]) if prod.get("finish_materials") else []
    set_items: list[dict] = json.loads(prod["set_items"]) if prod.get("set_items") else []
    random_stats: list[dict] = json.loads(prod["random_stats"]) if prod.get("random_stats") else []

    # ── 构建各段落 ──
    # section = list of (icon | None, text, color)
    Section = list[tuple[Image.Image | None, str, tuple[int, int, int]]]

    # 标题段
    title_sec: Section = [
        (icon, f"{prod['name']} (ID:{prod['item_id']})", _TITLE),
        (None, f"{prod['type_text']} Rank {prod['level_text']}", _ACCENT),
    ]
    if prod.get("need_prop"):
        title_sec.append((None, f"需要: {prod['need_prop']}", _DIM))

    sections: list[Section] = [title_sec]

    # 材料段
    mat_sec: Section = [(None, "材料:", _LABEL)]
    for m in materials:
        alt_names = [a["name"] for a in m.get("alternatives", [])]
        name_str = f"{m['name']}/{'/'.join(alt_names)}" if alt_names else m["name"]
        recipe = await _get_mat_recipe(m["item_id"])
        recipe_str = f"（{recipe}）" if recipe else ""
        mat_icon = await _load_icon(m["item_id"], _MAT_ICON)
        mat_sec.append((mat_icon, f"{name_str} x{m['count']}{recipe_str}", _TEXT))
    sections.append(mat_sec)

    if finish_mats:
        fin_sec: Section = [(None, "收尾材料:", _LABEL)]
        for m in finish_mats:
            alt_names = [a["name"] for a in m.get("alternatives", [])]
            name_str = f"{m['name']}/{'/'.join(alt_names)}" if alt_names else m["name"]
            recipe = await _get_mat_recipe(m["item_id"])
            recipe_str = f"（{recipe}）" if recipe else ""
            mat_icon = await _load_icon(m["item_id"], _MAT_ICON)
            fin_sec.append((mat_icon, f"{name_str} x{m['count']}{recipe_str}", _TEXT))
        sections.append(fin_sec)

    if set_items:
        si_sec: Section = [(None, "套装效果:", _LABEL)]
        for s in set_items:
            if "threshold" in s:
                bonuses = ", ".join(
                    f"{_STAT_NAME_MAP.get(b['name'], b['name'])} {_fmt_range(b['min'], b['max'])}"
                    for b in s.get("bonuses", [])
                )
                si_sec.append((None, f"  品质≥{s['threshold']}: {bonuses}", _TEXT))
            else:
                sn = _STAT_NAME_MAP.get(s["name"], s["name"])
                si_sec.append((None, f"  {sn}: {_fmt_range(s['min'], s['max'])}", _TEXT))
        sections.append(si_sec)

    if random_stats:
        rs_sec: Section = [(None, "随机属性:", _LABEL)]
        for r in random_stats:
            rn = _STAT_NAME_MAP.get(r["name"], r["name"])
            rs_sec.append((None, f"  {rn}: {_fmt_range(r['min'], r['max'])}", _TEXT))
        sections.append(rs_sec)

    # ── 计算尺寸 ──
    tmp = Image.new("RGB", (1, 1))
    td = ImageDraw.Draw(tmp)
    _, text_h = _text_size(td, "测", font)
    line_h = text_h + _LINE_SPACING

    # 最大文本宽度（不含图标）
    max_text_w = 0
    for sec in sections:
        for _, text, _ in sec:
            w, _ = _text_size(td, text, font)
            max_text_w = max(max_text_w, w)

    text_indent = _MAT_ICON + 6  # 材料行缩进，给图标留位
    section_w = _PADDING * 2 + text_indent + max_text_w

    # 计算总高度（有图标的行用 _ICON_LINE_H）
    total_h = _PADDING
    for si, sec in enumerate(sections):
        first_icon = sec[0][0]
        first_h = max(first_icon.height if first_icon else 0, line_h)
        sec_h = first_h
        for li in range(1, len(sec)):
            has_icon = sec[li][0] is not None
            sec_h += _ICON_LINE_H if has_icon else line_h
        total_h += sec_h + _SECTION_GAP
    total_h += _PADDING

    # ── 绘制 ──
    img = Image.new("RGB", (section_w, total_h), _BG)
    draw = ImageDraw.Draw(img)

    y = _PADDING
    for si, sec in enumerate(sections):
        # 段背景高度
        first_icon = sec[0][0]
        first_h = max(first_icon.height if first_icon else 0, line_h)
        sec_h = first_h
        for li in range(1, len(sec)):
            has_icon = sec[li][0] is not None
            sec_h += _ICON_LINE_H if has_icon else line_h
        draw.rectangle(
            [_PADDING - 4, y - 2, section_w - _PADDING + 4, y + sec_h + 2],
            fill=_SECTION_BG,
        )

        for li, (icon_img, text, color) in enumerate(sec):
            text_x = _PADDING
            cur_h = first_h if li == 0 else (_ICON_LINE_H if icon_img else line_h)
            if li == 0 and icon_img:
                img.paste(icon_img, (_PADDING, y), icon_img if icon_img.mode == "RGBA" else None)
                text_x = _PADDING + icon_img.width + 8
            elif icon_img:
                icon_y = y + (cur_h - icon_img.height) // 2
                img.paste(icon_img, (_PADDING, icon_y), icon_img if icon_img.mode == "RGBA" else None)
                text_x = _PADDING + text_indent
            text_y = y + (cur_h - text_h) // 2
            draw.text((text_x, text_y), text, fill=color, font=font)
            y += cur_h

        y += _SECTION_GAP

        # 分隔线（最后一段不画）
        if si < len(sections) - 1:
            draw.line(
                [_PADDING, y, section_w - _PADDING, y],
                fill=_DIVIDER, width=_DIVIDER_H,
            )
            y += _SECTION_GAP

    # 转 base64
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return f"base64://{base64.b64encode(buf.getvalue()).decode()}"
