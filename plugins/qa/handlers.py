from __future__ import annotations

import base64
import json
import re as _re

import httpx
from nonebot import on_regex
from nonebot.adapters.onebot.v11 import (
    Message,
    MessageEvent,
    MessageSegment,
)
from nonebot.matcher import Matcher
from nonebot.message import event_preprocessor
from nonebot.typing import T_State
from sqlalchemy import select

from utils.permission import is_allowed

from .config import Config
from .database import async_session
from .models import QA

try:
    from nonebot import get_plugin_config

    config = get_plugin_config(Config)
except (ValueError, RuntimeError):
    config = Config()

_INVISIBLE_RE = _re.compile(
    "[\u00ad\u034f\u061c\u115f\u1160\u17b4\u17b5"
    "\u180b-\u180f\u200b-\u200f\u202a-\u202e\u2060-\u2064"
    "\u2066-\u206f\u3000\u3164\ufeff\uffa0\ufff0-\ufff8]"
)


def _normalize(text: str) -> str:
    text = _INVISIBLE_RE.sub("", text)
    text = text.strip()
    out: list[str] = []
    for ch in text:
        cp = ord(ch)
        if 0xFF01 <= cp <= 0xFF5E:
            out.append(chr(cp - 0xFEE0))
        elif cp == 0xFF03:
            out.append("#")
        else:
            out.append(ch)
    return "".join(out)


# ── helpers ──────────────────────────────────────────────


@event_preprocessor
async def _strip_invisible(event: MessageEvent):
    """全局预处理：清理不可见 Unicode 字符和全角符号。

    放在 QA 插件中是因为 QA 触发词（qa、#）最常受全角/零宽字符影响，
    但清理对所有插件都有益。
    """
    for seg in event.message:
        if seg.type == "text":
            raw = seg.data.get("text", "")
            cleaned = _normalize(raw)
            # 只在实际包含不可见字符或全角符号时才修改
            if cleaned != raw:
                seg.data["text"] = cleaned


async def _download_image(url: str) -> str | None:
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return base64.b64encode(resp.content).decode()
    except (httpx.HTTPError, OSError):
        return None


def _extract_content(event: MessageEvent) -> tuple[str, list[str]]:
    text_parts: list[str] = []
    images: list[str] = []
    for seg in event.message:
        if seg.type == "text":
            text_parts.append(seg.data.get("text", ""))
        elif seg.type == "image":
            url = seg.data.get("url") or seg.data.get("file", "")
            if url:
                images.append(url)
    return "".join(text_parts).strip(), images


async def _resolve_images(urls: list[str]) -> list[str]:
    results: list[str] = []
    for url in urls[: config.qa_max_images]:
        b64 = await _download_image(url)
        if b64:
            results.append(b64)
    return results


def _build_answer_msg(qa_item: QA) -> Message:
    msg = Message()
    msg += MessageSegment.text(
        f"#{qa_item.id}\nQ: {qa_item.question}\nA: {qa_item.answer}"
    )
    for b64 in qa_item.image_list:
        msg += MessageSegment.text("\n")
        msg += MessageSegment.image(f"base64://{b64}")
    return msg


# ── 编辑 (qa edit id|答案) ─────────────────────────────

qa_edit = on_regex(
    r"\Aqa\s+edit\s+(\d+)\|(.+)\Z", priority=13, block=True, rule=is_allowed()
)


@qa_edit.handle()
async def handle_qa_edit(event: MessageEvent, state: T_State):
    item_id = int(state["_matched"].group(1))
    new_answer = state["_matched"].group(2).strip()
    if not new_answer:
        await qa_edit.reject("答案不能为空")

    async with async_session() as session:
        item = await session.get(QA, item_id)
        if not item:
            await qa_edit.finish(f"没找到第{item_id}条")
        _, image_urls = _extract_content(event)
        item.answer = new_answer
        images = await _resolve_images(image_urls) if image_urls else []
        item.images = json.dumps(images, ensure_ascii=False) if images else None
        await session.commit()
    await qa_edit.finish(f"好，第{item_id}条改好了")


# ── 删除 (qa del id) ──────────────────────────────────

qa_del = on_regex(r"\Aqa\s+del\s+(\d+)\Z", priority=13, block=True, rule=is_allowed())


@qa_del.handle()
async def handle_qa_del(state: T_State):
    del_id = int(state["_matched"].group(1))
    async with async_session() as session:
        item = await session.get(QA, del_id)
        if not item:
            await qa_del.finish(f"没找到第{del_id}条")
        await session.delete(item)
        await session.commit()
    await qa_del.finish(f"好，第{del_id}条删掉了")


# ── 按ID查看 (#id) ───────────────────────────────────

qa_id = on_regex(r"\A\s*#\s*(\d+)\s*\Z", priority=14, block=True, rule=is_allowed())


@qa_id.handle()
async def handle_qa_id(state: T_State):
    item_id = int(state["_matched"].group(1))
    async with async_session() as session:
        item = await session.get(QA, item_id)
    if not item:
        await qa_id.finish(f"没找到第{item_id}条")
    await qa_id.finish(_build_answer_msg(item))


# ── 创建 (qa 问题|答案) ──────────────────────────────

qa_create = on_regex(
    r"\Aqa\s+(.+?)\|(.+)\Z", priority=15, block=True, rule=is_allowed()
)


@qa_create.handle()
async def handle_qa_create(event: MessageEvent, state: T_State):
    question = state["_matched"].group(1).strip()
    answer_text = state["_matched"].group(2).strip()
    if not question or not answer_text:
        await qa_create.reject("格式不对，试试：qa 问题|答案")

    _, image_urls = _extract_content(event)
    images = await _resolve_images(image_urls) if image_urls else []

    async with async_session() as session:
        item = QA(
            question=question,
            answer=answer_text,
            images=json.dumps(images, ensure_ascii=False) if images else None,
            created_by=str(event.user_id),
        )
        session.add(item)
        await session.commit()
        await session.refresh(item)
    await qa_create.finish(f"好嘞，加好了，编号{item.id}")


# ── 搜索 / 结果选择 (qa 关键词) ──────────────────────

qa_read = on_regex(r"\Aqa\s+(.+)\Z", priority=16, block=True, rule=is_allowed())


@qa_read.handle()
async def handle_qa_read(event: MessageEvent, state: T_State, matcher: Matcher):
    raw = state["_matched"].group(1).strip()
    if not raw:
        await qa_read.reject("给个关键词吧")

    # 如果有活跃的搜索结果，且用户输入 #id，按 id 从结果中选择
    search_ids = state.get("search_ids")
    if search_ids and raw.startswith("#") and raw[1:].isdigit():
        pick_id = int(raw[1:])
        if pick_id in search_ids:
            async with async_session() as session:
                item = await session.get(QA, pick_id)
            if item:
                state.clear()
                await qa_read.finish(_build_answer_msg(item))
        state.clear()
        await qa_read.finish(f"列表里没有第{pick_id}条")

    # 纯数字 → 先按 ID 查
    if raw.isdigit():
        item_id = int(raw)
        async with async_session() as session:
            item = await session.get(QA, item_id)
        if item:
            await qa_read.finish(_build_answer_msg(item))

    # 按关键词搜
    async with async_session() as session:
        result = await session.execute(
            select(QA)
            .where(QA.question.contains(raw))
            .order_by(QA.id.desc())
            .limit(config.qa_list_limit)
        )
        items = list(result.scalars().all())

    if not items:
        await qa_read.finish(f'没找到和"{raw}"相关的')

    if len(items) == 1:
        await qa_read.finish(_build_answer_msg(items[0]))

    # 多条结果 → 列出列表，暂停等待用户选择
    lines = [it.format_short() for it in items]
    state["search_ids"] = [it.id for it in items]
    await matcher.send(f"搜到了这些（{raw}）：\n" + "\n".join(lines))
    await matcher.pause("输入 #编号 查看详情")
