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
from utils.item_upgrade import DB_PATH, get_item_image, get_item_upgrades, search_item_upgrades
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
_LINE_SPACING = 8
_PADDING = 16
_SECTION_GAP = 8
_ICON_SIZE = 64
_ICON_PAD = 8
_BG = (28, 28, 32)
_TITLE_BG = (45, 50, 62)
_SECTION_BG = (38, 38, 44)
_UPGRADE_BG = (44, 44, 52)
_DIVIDER = (60, 60, 68)
_TITLE = (255, 255, 255)
_TEXT = (210, 225, 240)
_DIM = (140, 140, 145)
_ACCENT = (100, 200, 255)
_LABEL = (160, 175, 200)
_GEM_COLOR = (100, 225, 160)
_LUCKY_COLOR = (255, 200, 100)
_WARN = (255, 100, 100)

_STAT_NAME_MAP = {
    "attack_min": "最小伤害",
    "attack_max": "最大伤害",
    "attack_range": "攻击范围",
    "balance": "平衡",
    "casting_speed": "施法速度",
    "chain_casting": "连续施法",
    "collecting_bonus": "采集加成",
    "collecting_speed": "采集速度",
    "critical": "暴击率",
    "defense": "防御",
    "dex": "敏捷",
    "durability_filled_max": "最大耐久",
    "durability_max": "最大耐久",
    "hp_recover": "生命回复",
    "immune_magic": "魔法免疫",
    "immune_melee": "近战免疫",
    "immune_ranged": "远程免疫",
    "int": "智力",
    "lance_piercing": "穿透",
    "luck": "幸运",
    "magic_damage": "魔法攻击力",
    "magic_defense": "魔法防御力",
    "magic_protect": "魔法保护",
    "mana_recover": "魔法回复速度",
    "mana_reduce_percent": "魔法消耗减少%",
    "manaburn_revised": "魔烧修正",
    "manause_revised": "魔法消耗修正",
    "matk_max": "最大魔法攻击力",
    "max_bullet": "最大弹药数",
    "max_mana_increase": "最大魔力增加",
    "musicbuff_bonus": "音乐buff效果",
    "musicbuff_duration": "音乐buff持续时间",
    "protect": "保护",
    "splash_damage": "溅射伤害",
    "splash_radius": "溅射范围",
    "stamina_recover": "体力回复",
    "str": "力量",
    "will": "意志",
    "wound_max": "最大负伤率",
    "wound_min": "最小负伤率",
    "range": "射程",
    "attack_speed": "攻击速度",
    "astrologist_damage": "占星术伤害",
    "marionette_damage": "人偶伤害",
    "pierce": "穿透",
}

# up <id> → 精准查询
up_id = on_regex(r"\Aup\s+(\d+)\Z", priority=14, block=True, rule=is_allowed())

# up <关键词> → 模糊搜索
up_search = on_regex(r"\Aup\s+(\D.*)\Z", priority=15, block=True, rule=is_allowed())


def _stat_name(raw: str) -> str:
    return _STAT_NAME_MAP.get(raw, raw)


def _fmt_val(min_v: float, max_v: float) -> str:
    if min_v == max_v:
        return f"{min_v:g}"
    return f"{min_v:g}~{max_v:g}"


def _text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


@up_id.handle()
async def handle_up_id(event: MessageEvent, state: T_State):
    item_id = int(state["_matched"].group(1))
    info = await get_item_upgrades(item_id)
    if not info:
        await up_id.finish(f"没找到 ID {item_id} 的可改造装备")
    await up_id.finish(MessageSegment.image(await _render(info)))


@up_search.handle()
async def handle_up_search(event: MessageEvent, state: T_State):
    keyword: str = state["_matched"].group(1).strip()
    if not keyword:
        return

    results = await search_item_upgrades(keyword, limit=config.item_upgrade_search_limit)
    if not results:
        await up_search.finish(f"没找到和\"{keyword}\"相关的可改造装备")

    if len(results) == 1:
        full = await get_item_upgrades(results[0]["item_id"])
        if full:
            await up_search.finish(MessageSegment.image(await _render(full)))

    lines = [
        f"up {r['item_id']} | {r['name']} [普{r['upgrade_max']} 宝{r['gem_upgrade_max']}]"
        for r in results
    ]
    await up_search.finish(f"找到 {len(results)} 个：\n" + "\n".join(lines))


# ── 图片渲染 ──────────────────────────────────────────

_ICON_AREA_W = 72       # 图标区域固定宽度
_ICON_PAD = 8
_COL_PAD = 12           # 列间距
_SLOT_W = 22        # 每个槽位圆点列宽
_DOT_R = 6          # 圆点半径
_HEADER_BG = (35, 38, 48)
_EVEN_ROW_BG = (42, 42, 50)
_ODD_ROW_BG = (48, 48, 56)
_DOT_ACTIVE_N = (90, 180, 255)   # 普通改造亮灯 - 蓝
_DOT_ACTIVE_G = (80, 220, 140)   # 宝石改造亮灯 - 绿
_DOT_INACTIVE = (65, 65, 72)     # 灭灯 - 暗灰
_COL_NAME = 0
_COL_COST = 1
_COL_STAT = 2


async def _load_icon(item_id: int) -> Image.Image | None:
    b64 = await get_item_image(item_id)
    if not b64:
        return None
    try:
        raw = base64.b64decode(b64)
        return Image.open(io.BytesIO(raw)).convert("RGBA")
    except (OSError, ValueError):
        return None


def _text_w(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> int:
    return draw.textbbox((0, 0), text, font=font)[2]


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
    """将文本按像素宽度自动换行。"""
    if _text_w(draw, text, font) <= max_w:
        return [text]
    lines = []
    line = ""
    for ch in text:
        if _text_w(draw, line + ch, font) > max_w:
            lines.append(line)
            line = ch
        else:
            line += ch
    if line:
        lines.append(line)
    return lines


def _prepare_upgrade_rows(upgrades: list[dict]) -> list[dict]:
    """预处理改造项，生成每行的渲染数据。"""
    rows = []
    for up in upgrades:
        is_gem = bool(up.get("need_gems"))

        # 消耗文本
        cost_parts = []
        if up.get("need_ep"):
            cost_parts.append(f"熟练度{up['need_ep']}")
        if up.get("need_gold"):
            cost_parts.append(f"金币{up['need_gold']:,}")
        cost_text = " ".join(cost_parts)
        if up.get("need_gems"):
            gems = json.loads(up["need_gems"])
            gem_strs = [f"{g['name']} {g['size']:g}cm" for g in gems]
            cost_text += ("\n" if cost_text else "") + "\n".join(gem_strs)

        # 属性文本（每行一个）
        stat_lines = []
        if up.get("modify_stats"):
            for s in json.loads(up["modify_stats"]):
                sn = _stat_name(s["name"])
                val = _fmt_val(s["min"], s["max"])
                sign = "+" if s["min"] > 0 else ""
                extra = f" (+{s['extra']})" if s.get("extra") else ""
                stat_lines.append(f"{sn} {sign}{val}{extra}")

        # 幸运改造也放到属性列
        if up.get("lucky_upgrade"):
            lu = json.loads(up["lucky_upgrade"])
            stat_lines.append("[幸运改造]")
            ct = lu.get("count_total_rate", 0)
            for cr in lu.get("count_rates", []):
                pct = f"{cr['rate'] / ct * 100:.0f}%" if ct else "?"
                stat_lines.append(f"  选项数{cr['count']}: {pct}")
            ot = lu.get("random_option_total_rate", 0)
            for ro in lu.get("random_option_rates", []):
                pct = f"{ro['rate'] / ot * 100:.0f}%" if ot else "?"
                stat_lines.append(f"  {ro['name']}: {pct}")
            for fo in lu.get("fixed_options", []):
                stat_lines.append(f"  固定: {fo['name']}")

        # 选项集（含换行描述拆成多行）
        if up.get("option_set_ids"):
            os_items = json.loads(up["option_set_ids"])
            stat_lines.append("选项:")
            for item in os_items:
                for sub in item["name"].split("\n"):
                    if sub.strip():
                        stat_lines.append(f"  {sub.strip()}")

        if up.get("personalize"):
            stat_lines.append("⚠ 专用化装备")

        if not stat_lines:
            stat_lines.append("")

        rows.append({
            "name": up["name"],
            "is_gem": is_gem,
            "cost": cost_text,
            "stats": stat_lines,
            "slot_min": up["upgraded_min"],
            "slot_max": up["upgraded_max"],
        })
    return rows


async def _render(info: dict) -> str:
    """渲染装备改造信息为表格图片，返回 base64 data URI。"""
    font = ImageFont.truetype(global_cfg.qiqibot_font, _FONT_SIZE)
    icon = await _load_icon(info["item_id"])

    upgrade_max = info["upgrade_max"]
    gem_max = info["gem_upgrade_max"]
    total_slots = upgrade_max + gem_max

    upgrades: list[dict] = info.get("upgrades", [])
    rows = _prepare_upgrade_rows(upgrades)

    # ── 计算列宽 ──
    tmp = Image.new("RGB", (1, 1))
    td = ImageDraw.Draw(tmp)
    _, text_h = _text_size(td, "测", font)
    line_h = text_h + 6

    name_w = _text_w(td, "改造项", font)
    cost_w = _text_w(td, "消耗", font)
    stat_w = _text_w(td, "属性", font)

    for r in rows:
        name_w = max(name_w, _text_w(td, r["name"], font))
        for cl in r["cost"].split("\n"):
            cost_w = max(cost_w, _text_w(td, cl, font))
        for sl in r["stats"]:
            stat_w = max(stat_w, _text_w(td, sl, font))

    # 加 padding
    name_w += 16
    cost_w += 16
    stat_w += 16

    slots_w = total_slots * _SLOT_W

    # 列 x 坐标
    col_x = [_PADDING]
    col_x.append(col_x[-1] + name_w + _COL_PAD)
    col_x.append(col_x[-1] + cost_w + _COL_PAD)
    slots_x = col_x[-1] + stat_w + _COL_PAD

    img_w = slots_x + slots_w + _PADDING
    icon_indent = _ICON_AREA_W + _ICON_PAD if icon else 0
    img_w = max(img_w, 400 + icon_indent)

    # ── 构建行数据 ──
    # title section - 描述自动换行
    desc_text = info.get("desc", "")
    desc_lines = _wrap_text(td, desc_text, font, img_w - icon_indent - _PADDING * 2) if desc_text else []

    title_h = line_h  # 名称行
    title_h += len(desc_lines) * line_h  # 描述行（可能多行）
    title_h += line_h  # 槽位信息
    title_h += _PADDING  # 上下 padding

    # header row
    header_h = line_h + 8

    # upgrade rows
    row_heights = []
    for r in rows:
        n_lines = max(len(r["stats"]), len(r["cost"].split("\n")))
        n_lines = max(n_lines, 1)
        row_heights.append(n_lines * line_h + 8)

    total_h = title_h + header_h + sum(row_heights) + _PADDING

    # ── 绘制 ──
    img = Image.new("RGB", (img_w, total_h), _BG)
    draw = ImageDraw.Draw(img)

    # ── 标题区 ──
    y = _PADDING
    draw.rectangle([_PADDING - 4, y - 2, img_w - _PADDING + 4, y + title_h - 6], fill=_TITLE_BG)

    tx = _PADDING
    if icon:
        # 图标铺满标题区左侧
        area_h = title_h - _PADDING - 4
        area_w = _ICON_AREA_W
        scale = min(area_w / icon.width, area_h / icon.height)
        scaled = icon.resize((int(icon.width * scale), int(icon.height * scale)), Image.Resampling.LANCZOS)
        ix = _PADDING + (area_w - scaled.width) // 2
        iy = y + (area_h - scaled.height) // 2
        img.paste(scaled, (ix, iy), scaled)
        tx = _PADDING + icon_indent

    draw.text((tx, y), f"{info['name']}  ID:{info['item_id']}", fill=_TITLE, font=font)
    y += line_h

    for dl in desc_lines:
        draw.text((tx, y), dl, fill=_DIM, font=font)
        y += line_h

    slot_info = f"改造次数: {upgrade_max}"
    if gem_max:
        slot_info += f"  宝石改造: {gem_max}"
    draw.text((tx, y), slot_info, fill=_ACCENT, font=font)
    y += line_h + _PADDING

    # ── 表头 ──
    draw.rectangle([_PADDING - 4, y - 2, img_w - _PADDING + 4, y + header_h], fill=_HEADER_BG)
    draw.text((col_x[_COL_NAME], y + 4), "改造项", fill=_LABEL, font=font)
    draw.text((col_x[_COL_COST], y + 4), "消耗", fill=_LABEL, font=font)
    draw.text((col_x[_COL_STAT], y + 4), "属性", fill=_LABEL, font=font)

    # 槽位编号
    for si in range(upgrade_max):
        cx = slots_x + si * _SLOT_W + _SLOT_W // 2
        draw.text((cx - 4, y + 4), str(si + 1), fill=_LABEL, font=font)
    for si in range(gem_max):
        cx = slots_x + (upgrade_max + si) * _SLOT_W + _SLOT_W // 2
        draw.text((cx - 6, y + 4), f"G{si + 1}", fill=_GEM_COLOR, font=font)

    y += header_h

    # ── 改造行 ──
    for ri, (r, rh) in enumerate(zip(rows, row_heights)):
        bg = _EVEN_ROW_BG if ri % 2 == 0 else _ODD_ROW_BG
        draw.rectangle([_PADDING - 4, y, img_w - _PADDING + 4, y + rh], fill=bg)

        # 名称
        name_color = _GEM_COLOR if r["is_gem"] else _TITLE
        draw.text((col_x[_COL_NAME], y + 4), r["name"], fill=name_color, font=font)

        # 消耗（多行，超长自动换行）
        cost_avail = img_w - col_x[_COL_COST] - _PADDING
        draw_y = y + 4
        for cl in r["cost"].split("\n"):
            if cl:
                wrapped = _wrap_text(draw, cl, font, cost_avail)
                for wl in wrapped:
                    draw.text((col_x[_COL_COST], draw_y), wl, fill=_TEXT, font=font)
                    draw_y += line_h
            else:
                draw_y += line_h

        # 属性（多行，超长自动换行）
        stat_avail = img_w - col_x[_COL_STAT] - _PADDING
        draw_y = y + 4
        for sl in r["stats"]:
            color = _LUCKY_COLOR if sl.startswith("[") or sl.startswith("  ") else _TEXT
            if sl.startswith("选项:") or sl.startswith("⚠"):
                color = _DIM
            wrapped = _wrap_text(draw, sl, font, stat_avail)
            for wl in wrapped:
                draw.text((col_x[_COL_STAT], draw_y), wl, fill=color, font=font)
                draw_y += line_h

        # 槽位圆点（宝石改造槽位需偏移到 G 列）
        dot_y = y + rh // 2
        s_min = r["slot_min"] + upgrade_max if r["is_gem"] else r["slot_min"]
        s_max = r["slot_max"] + upgrade_max if r["is_gem"] else r["slot_max"]
        for si in range(total_slots):
            cx = slots_x + si * _SLOT_W + _SLOT_W // 2
            if s_min <= si <= s_max:
                color = _DOT_ACTIVE_G if r["is_gem"] else _DOT_ACTIVE_N
                draw.ellipse([cx - _DOT_R, dot_y - _DOT_R, cx + _DOT_R, dot_y + _DOT_R], fill=color)
            else:
                draw.ellipse([cx - _DOT_R, dot_y - _DOT_R, cx + _DOT_R, dot_y + _DOT_R], outline=_DOT_INACTIVE, width=1)

        y += rh

    # 转 base64
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return f"base64://{base64.b64encode(buf.getvalue()).decode()}"
