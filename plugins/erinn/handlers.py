from __future__ import annotations

import base64
import io
import json
import sqlite3
from pathlib import Path

from nonebot import on_regex
from nonebot.adapters.onebot.v11 import MessageEvent, MessageSegment
from nonebot.typing import T_State
from PIL import Image, ImageDraw, ImageFont

from utils.erinn import search_items
from utils.permission import is_allowed

from .config import Config

try:
    from nonebot import get_plugin_config

    config = get_plugin_config(Config)
except (ValueError, RuntimeError):
    config = Config()

# ── 布局常量 ──────────────────────────────────────────

CARD_W = 860
LEFT_W = 180
SKILL_W = 80
MAT_CELL_W = 100
BORDER = 5
PAD = 6
ICON_SIZE = 50
SKILL_ICON = 50
NPC_ICON = 30

BG = (0, 0, 0)
CARD_BORDER = (255, 215, 0)
HEADER_BG = (136, 136, 136)
INGOT_BG = (170, 170, 170)
WHITE = (255, 255, 255)
GOLD_TEXT = (255, 215, 0)
DIM_TEXT = (160, 160, 160)

_FONT_PATH = "/Users/ming/Library/Fonts/NotoSansSC.ttf"

_CRAFT_ROW_H = ICON_SIZE + 22 + 16

# ── DB ────────────────────────────────────────────────

_DB_CONN: sqlite3.Connection | None = None


def _get_db() -> sqlite3.Connection:
    global _DB_CONN
    if _DB_CONN is None:
        _DB_CONN = sqlite3.connect(str(Path("data/erinn.db")))
        _DB_CONN.row_factory = sqlite3.Row
    return _DB_CONN


def _q(sql: str, params: tuple = ()) -> tuple | None:
    return _get_db().execute(sql, params).fetchone()


def _qa(sql: str, params: tuple = ()) -> list:
    return _get_db().execute(sql, params).fetchall()


def _get_item_name(item_id: int) -> str:
    row = _q("SELECT name FROM items WHERE item_id = ?", (item_id,))
    return row[0] if row else f"ID:{item_id}"


# ── 图标加载 ──────────────────────────────────────────


def _load_icon(item_id: int, size: int = ICON_SIZE) -> Image.Image | None:
    row = _q("SELECT image_b64 FROM item_images WHERE item_id = ?", (item_id,))
    if not row:
        return None
    try:
        raw = base64.b64decode(row[0])
        src = Image.open(io.BytesIO(raw)).convert("RGBA")
        ratio = (size - 2) / max(src.width, src.height)
        sw, sh = int(src.width * ratio), int(src.height * ratio)
        scaled = src.resize((sw, sh), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        canvas.paste(scaled, ((size - sw) // 2, (size - sh) // 2), scaled)
        return canvas
    except Exception:  # noqa: BLE001
        return None


def _load_skill_icon(skill_en: str) -> Image.Image | None:
    row = _q(
        "SELECT si.image_b64 FROM skills s "
        "LEFT JOIN skill_images si ON s.skill_id = si.skill_id "
        "WHERE s.name_en = ?",
        (skill_en,),
    )
    if not row or not row[0]:
        return None
    try:
        raw = base64.b64decode(row[0])
        src = Image.open(io.BytesIO(raw)).convert("RGBA")
        ratio = (SKILL_ICON - 2) / max(src.width, src.height)
        sw, sh = int(src.width * ratio), int(src.height * ratio)
        scaled = src.resize((sw, sh), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (SKILL_ICON, SKILL_ICON), (0, 0, 0, 0))
        canvas.paste(scaled, ((SKILL_ICON - sw) // 2, (SKILL_ICON - sh) // 2), scaled)
        return canvas
    except Exception:  # noqa: BLE001
        return None


def _load_npc_icon(npc_id: int) -> Image.Image | None:
    row = _q("SELECT image_b64 FROM npc_images WHERE npc_id = ?", (npc_id,))
    if not row:
        return None
    try:
        raw = base64.b64decode(row[0])
        src = Image.open(io.BytesIO(raw)).convert("RGBA")
        ratio = (NPC_ICON - 2) / max(src.width, src.height)
        sw, sh = int(src.width * ratio), int(src.height * ratio)
        scaled = src.resize((sw, sh), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (NPC_ICON, NPC_ICON), (0, 0, 0, 0))
        canvas.paste(scaled, ((NPC_ICON - sw) // 2, (NPC_ICON - sh) // 2), scaled)
        return canvas
    except Exception:  # noqa: BLE001
        return None


# ── 配方解析 ──────────────────────────────────────────

_MAX_DEPTH = 3


def _get_all_recipes(item_id: int) -> list[dict]:
    rows = _qa(
        "SELECT * FROM recipes WHERE item_id = ? ORDER BY skill_name", (item_id,)
    )
    return [dict(r) for r in rows]


def _parse_mats(data: list) -> list[dict]:
    mats: list[dict] = []
    i = 0
    while i < len(data):
        elem = data[i]
        if isinstance(elem, str):
            count = 1
            if i + 1 < len(data) and isinstance(data[i + 1], (int, float)):
                count = int(data[i + 1])
                i += 1
            mats.append({"item_id": elem, "name": elem, "count": count, "is_str": True})
        elif isinstance(elem, list) and len(elem) >= 2:
            mat_id = elem[0]
            qty = int(elem[1]) if isinstance(elem[1], (int, float)) else 1
            name = _get_item_name(mat_id) if isinstance(mat_id, int) else str(mat_id)
            mats.append({"item_id": mat_id, "name": name, "count": qty})
        elif isinstance(elem, (int, float)):
            count = 1
            if i + 1 < len(data) and isinstance(data[i + 1], (int, float)):
                count = int(data[i + 1])
                i += 1
            mats.append(
                {
                    "item_id": int(elem),
                    "name": _get_item_name(int(elem)),
                    "count": count,
                }
            )
        i += 1
    return mats


def _split_recipe(recipe_data: list) -> tuple[list[dict], list[dict]]:
    if len(recipe_data) == 1 and isinstance(recipe_data[0], list):
        recipe_data = recipe_data[0]
    sep = next((i for i, e in enumerate(recipe_data) if e == 0), None)
    if sep is not None:
        return _parse_mats(recipe_data[:sep]), _parse_mats(recipe_data[sep + 1 :])
    return _parse_mats(recipe_data), []


def _get_acquisitions(item_id: int) -> list[dict]:
    rows = _qa("SELECT * FROM acquisitions WHERE item_id = ?", (item_id,))
    return [dict(r) for r in rows]


def _collect_tree(
    item_id: int, visited: set[int] | None = None, depth: int = 0
) -> list[tuple[int, str, list[tuple[str, dict]]]]:
    """递归收集配方树。返回 [(item_id, item_name, sections), ...]。"""
    if visited is None:
        visited = set()
    if item_id in visited or depth > _MAX_DEPTH:
        return []
    visited.add(item_id)

    item_name = _get_item_name(item_id)
    recipes = _get_all_recipes(item_id)
    acquisitions = _get_acquisitions(item_id)

    if not recipes and not acquisitions:
        return []

    sections: list[tuple[str, dict]] = []
    child_ids: list[int] = []

    for recipe in recipes:
        sections.append(("craft", recipe))
        recipe_data = json.loads(recipe["recipe_data"])
        base_mats, finish_mats = _split_recipe(recipe_data)
        for mat in base_mats + finish_mats:
            mid = mat.get("item_id")
            if isinstance(mid, int) and mid not in visited:
                child_ids.append(mid)

    for acq in acquisitions:
        sections.append((acq["acq_type"], acq))

    result: list[tuple[int, str, list[tuple[str, dict]]]] = [
        (item_id, item_name, sections)
    ]
    for cid in child_ids:
        result.extend(_collect_tree(cid, visited, depth + 1))
    return result


# ── 绘制辅助 ──────────────────────────────────────────


def _text_size(
    draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont
) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return int(bbox[2] - bbox[0]), int(bbox[3] - bbox[1])


def _draw_border(draw, x, y, w, h, color, width=1):
    draw.rectangle([x, y, x + w - 1, y + h - 1], outline=color, width=width)


def _paste_centered(base, overlay, x, y, w, h):
    ox = x + (w - overlay.width) // 2
    oy = y + (h - overlay.height) // 2
    base.paste(overlay, (ox, oy), overlay if overlay.mode == "RGBA" else None)


def _truncate_text(text, max_w, font, draw):
    tw, _ = _text_size(draw, text, font)
    if tw <= max_w:
        return text
    for i in range(len(text) - 1, 0, -1):
        candidate = text[:i] + "..."
        tw, _ = _text_size(draw, candidate, font)
        if tw <= max_w:
            return candidate
    return "..."


# ── 行绘制函数 ────────────────────────────────────────


def _draw_craft_row(draw, img, y, right_x, recipe, font, small_font) -> int:
    """制作配方行：技能图标 + 材料网格。"""
    skill_en = recipe["skill_name"]
    skill_lv = recipe.get("skill_level")
    recipe_data = json.loads(recipe["recipe_data"])
    base_mats, finish_mats = _split_recipe(recipe_data)
    all_mats = base_mats + finish_mats

    mat_cols = 5
    mat_pad = 4
    mat_rows = (len(all_mats) + mat_cols - 1) // mat_cols if all_mats else 0
    row_h = max(mat_rows * _CRAFT_ROW_H, SKILL_ICON + 18)

    # 技能图标
    skill_x = right_x + PAD
    skill_icon = _load_skill_icon(skill_en)
    if skill_icon:
        _paste_centered(img, skill_icon, skill_x, y, SKILL_W, SKILL_ICON)
    if skill_lv is not None:
        lv_text = f"Lv{skill_lv}"
        lw, _ = _text_size(draw, lv_text, small_font)
        draw.text(
            (skill_x + (SKILL_W - lw) // 2, y + SKILL_ICON + 2),
            lv_text,
            fill=GOLD_TEXT,
            font=small_font,
        )

    # 材料网格
    mat_x = right_x + SKILL_W + PAD * 2
    for mi, mat in enumerate(all_mats):
        row = mi // mat_cols
        col = mi % mat_cols
        cx = mat_x + col * MAT_CELL_W
        cy = y + row * _CRAFT_ROW_H
        cell_bg = INGOT_BG if mat.get("is_str") else BG
        draw.rectangle(
            [cx, cy, cx + MAT_CELL_W - 1, cy + _CRAFT_ROW_H - 1], fill=cell_bg
        )
        mid = mat["item_id"]
        if isinstance(mid, int):
            ic = _load_icon(mid, ICON_SIZE)
            if ic:
                _paste_centered(img, ic, cx, cy, MAT_CELL_W, ICON_SIZE)
        name_y = cy + ICON_SIZE + 2
        draw.rectangle([cx, name_y, cx + MAT_CELL_W - 1, name_y + 15], fill=cell_bg)
        mname = _truncate_text(mat["name"], MAT_CELL_W - mat_pad * 2, small_font, draw)
        mw, _ = _text_size(draw, mname, small_font)
        draw.text(
            (cx + (MAT_CELL_W - mw) // 2, name_y + 1),
            mname,
            fill=WHITE,
            font=small_font,
        )
        cnt_y = name_y + 16
        draw.rectangle([cx, cnt_y, cx + MAT_CELL_W - 1, cnt_y + 15], fill=cell_bg)
        cnt_text = f"×{mat['count']}"
        cw, _ = _text_size(draw, cnt_text, small_font)
        draw.text(
            (cx + (MAT_CELL_W - cw) // 2, cnt_y + 1),
            cnt_text,
            fill=DIM_TEXT,
            font=small_font,
        )

    return y + row_h + 4


def _draw_sell_row(draw, img, y, right_x, acq, font, small_font) -> int:
    """NPC 购买行：价格 + NPC 图标网格。"""
    data = (
        json.loads(acq["data"])
        if isinstance(acq.get("data"), str)
        else acq.get("data", {})
    )
    price = data.get("price", 0)
    npcs = data.get("npcs", [])

    _, lh = _text_size(draw, "测", small_font)
    draw.text((right_x + PAD, y), "NPC 购买", fill=GOLD_TEXT, font=small_font)
    draw.text((right_x + PAD + 80, y), f"{price} Gold", fill=WHITE, font=small_font)

    npc_y = y + lh + 2
    npc_x = right_x + PAD
    per_row = 12
    for ni, nid in enumerate(npcs[:36]):
        nr = ni // per_row
        nc = ni % per_row
        nx = npc_x + nc * (NPC_ICON + 2)
        ny = npc_y + nr * (NPC_ICON + 2)
        npc_icon = _load_npc_icon(nid)
        if npc_icon:
            img.paste(npc_icon, (nx, ny), npc_icon if npc_icon.mode == "RGBA" else None)

    npc_rows = (min(len(npcs), 36) + per_row - 1) // per_row if npcs else 0
    return npc_y + npc_rows * (NPC_ICON + 2) + 4


def _draw_text_row(draw, y, right_x, label, detail, font, small_font) -> int:
    """文字信息行。"""
    _, lh = _text_size(draw, "测", small_font)
    draw.text((right_x + PAD, y), label, fill=GOLD_TEXT, font=small_font)
    if detail:
        detail = _truncate_text(detail, 500, small_font, draw)
        draw.text((right_x + PAD + 80, y), detail, fill=WHITE, font=small_font)
    return y + lh + 4


# ── 卡片绘制 ──────────────────────────────────────────


def _calc_card_height(sections, font, small_font) -> int:
    tmp = Image.new("RGB", (1, 1))
    td = ImageDraw.Draw(tmp)
    _, line_h = _text_size(td, "测", font)
    right_h = 0
    for stype, data in sections:
        if stype == "craft":
            rd = json.loads(data["recipe_data"])
            bm, fm = _split_recipe(rd)
            mr = (len(bm) + len(fm) + 4) // 5 if (bm or fm) else 0
            right_h += max(mr * _CRAFT_ROW_H, SKILL_ICON + 18) + 4
        elif stype == "sell":
            d = (
                json.loads(data["data"])
                if isinstance(data.get("data"), str)
                else data.get("data", {})
            )
            npc_count = min(len(d.get("npcs", [])), 36)
            npc_rows = (npc_count + 11) // 12 if npc_count else 0
            _, lh = _text_size(td, "测", small_font)
            right_h += lh + 2 + npc_rows * (NPC_ICON + 2) + 4
        else:
            _, lh = _text_size(td, "测", small_font)
            right_h += lh + 4
    left_h = ICON_SIZE + 4 + line_h
    return max(left_h, right_h) + PAD * 2 + BORDER * 2


def _draw_card(img, y, item_id, item_name, sections, font, small_font) -> int:
    """绘制一个物品的完整卡片。"""
    draw = ImageDraw.Draw(img)
    card_h = _calc_card_height(sections, font, small_font)
    card_x = (img.width - CARD_W) // 2

    _draw_border(draw, card_x, y, CARD_W, card_h, CARD_BORDER, BORDER)

    # 左侧
    left_x = card_x + BORDER
    left_y = y + BORDER
    left_h = card_h - BORDER * 2
    draw.rectangle(
        [left_x, left_y, left_x + LEFT_W - 1, left_y + left_h - 1], fill=HEADER_BG
    )
    _draw_border(draw, left_x, left_y, LEFT_W, left_h, GOLD_TEXT, 2)

    _, name_h = _text_size(draw, "测", font)
    block_h = ICON_SIZE + 4 + name_h
    block_y = left_y + (left_h - block_h) // 2

    item_icon = _load_icon(item_id)
    if item_icon:
        _paste_centered(img, item_icon, left_x, block_y, LEFT_W, ICON_SIZE)
    tname = _truncate_text(item_name, LEFT_W - 8, font, draw)
    nw, _ = _text_size(draw, tname, font)
    draw.text(
        (left_x + (LEFT_W - nw) // 2, block_y + ICON_SIZE + 4),
        tname,
        fill=WHITE,
        font=font,
    )

    # 右侧各行
    right_x = left_x + LEFT_W
    row_y = left_y + PAD

    for stype, data in sections:
        if stype == "craft":
            row_y = _draw_craft_row(draw, img, row_y, right_x, data, font, small_font)
        elif stype == "sell":
            row_y = _draw_sell_row(draw, img, row_y, right_x, data, font, small_font)
        elif stype == "gather":
            d = (
                json.loads(data["data"])
                if isinstance(data.get("data"), str)
                else data.get("data", {})
            )
            row_y = _draw_text_row(
                draw,
                row_y,
                right_x,
                "采集",
                f"{d.get('action', '')} {d.get('location', '')}".strip(),
                font,
                small_font,
            )
        elif stype == "herbalism":
            d = (
                json.loads(data["data"])
                if isinstance(data.get("data"), str)
                else data.get("data", {})
            )
            row_y = _draw_text_row(
                draw, row_y, right_x, "草药采集", d.get("name", ""), font, small_font
            )
        elif stype == "kill":
            d = (
                json.loads(data["data"])
                if isinstance(data.get("data"), str)
                else data.get("data", {})
            )
            row_y = _draw_text_row(
                draw, row_y, right_x, "怪物掉落", d.get("monster", ""), font, small_font
            )

    return y + card_h


# ── 主渲染 ────────────────────────────────────────────


async def _render(item_id: int) -> str | None:
    tree = _collect_tree(item_id)
    if not tree:
        return None

    font = ImageFont.truetype(_FONT_PATH, 14)
    small_font = ImageFont.truetype(_FONT_PATH, 12)

    # 预计算总高度
    total_h = BORDER * 2
    for iid, iname, sections in tree:
        total_h += _calc_card_height(sections, font, small_font) + 8

    canvas_w = CARD_W + BORDER * 2 + 20
    img = Image.new("RGB", (canvas_w, total_h), BG)

    y = BORDER
    for iid, iname, sections in tree:
        y = _draw_card(img, y, iid, iname, sections, font, small_font)
        y += 8

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return f"base64://{base64.b64encode(buf.getvalue()).decode()}"


# ── matchers ──────────────────────────────────────────

erinn_id = on_regex(r"\Aerinn\s+(\d+)\Z", priority=14, block=True, rule=is_allowed())
erinn_search = on_regex(
    r"\Aerinn\s+(\D.*)\Z", priority=15, block=True, rule=is_allowed()
)


@erinn_id.handle()
async def handle_erinn_id(event: MessageEvent, state: T_State):
    item_id = int(state["_matched"].group(1))
    png = await _render(item_id)
    if not png:
        await erinn_id.finish(f"没找到 ID {item_id} 的配方")
    await erinn_id.finish(MessageSegment.image(png))


@erinn_search.handle()
async def handle_erinn_search(event: MessageEvent, state: T_State):
    keyword: str = state["_matched"].group(1).strip()
    if not keyword:
        return

    results = await search_items(keyword, limit=config.erinn_search_limit)
    if not results:
        await erinn_search.finish(f'没找到和"{keyword}"相关的配方')

    if len(results) == 1:
        item_id = results[0]["item_id"]
        png = await _render(item_id)
        if png:
            await erinn_search.finish(MessageSegment.image(png))
        await erinn_search.finish("渲染失败")

    lines = [f"erinn {r['item_id']} | {r['name']}" for r in results]
    await erinn_search.finish(f"找到 {len(results)} 个：\n" + "\n".join(lines))
