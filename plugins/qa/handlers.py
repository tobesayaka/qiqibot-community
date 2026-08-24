from __future__ import annotations

import base64
import json
import re

import httpx
from nonebot import on_regex
from nonebot.adapters.onebot.v11 import (
    Message,
    MessageEvent,
    MessageSegment,
)
from nonebot.matcher import Matcher
from nonebot.typing import T_State
from sqlalchemy import select

from .config import Config
from .database import async_session
from .models import QA
from utils.permission import is_allowed

try:
    from nonebot import get_plugin_config

    config = get_plugin_config(Config)
except (ValueError, RuntimeError):
    config = Config()

HELP_TEXT = (
    "你可以这样问我：\n"
    "  记一下 / 添加问答 — 新增一条\n"
    "  查一下 <关键词> / 搜 <关键词> — 搜索\n"
    "  看看问答 / 最近记了啥 — 列出最近的\n"
    "  第<id>条 — 查看详情\n"
    "  改一下第<id>条 — 编辑\n"
    "  删掉第<id>条 — 删除"
)


# ── helpers ──────────────────────────────────────────────


async def _download_image(url: str) -> str | None:
    """Download image from URL and return base64 string."""
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return base64.b64encode(resp.content).decode()
    except (httpx.HTTPError, OSError):
        return None


def _extract_content(event: MessageEvent) -> tuple[str, list[str]]:
    """Extract text and image URLs from message."""
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
    """Download images and return base64 list."""
    results: list[str] = []
    for url in urls[: config.qa_max_images]:
        b64 = await _download_image(url)
        if b64:
            results.append(b64)
    return results


def _build_answer_msg(qa_item: QA) -> Message:
    """Build a Message with text + images for a QA answer."""
    msg = Message()
    msg += MessageSegment.text(
        f"#{qa_item.id}\nQ: {qa_item.question}\nA: {qa_item.answer}"
    )
    for b64 in qa_item.image_list:
        msg += MessageSegment.text("\n")
        msg += MessageSegment.image(f"base64://{b64}")
    return msg


# ── 帮助 ────────────────────────────────────────────────

qa_help = on_regex(r"\A(?:帮助|怎么用|qa\s+help)\Z", priority=20, block=True, rule=is_allowed())


@qa_help.handle()
async def handle_qa_help():
    await qa_help.finish(HELP_TEXT)


# ── 添加问答 ────────────────────────────────────────────

qa_add = on_regex(r"\A(?:记一下|添加问答|我来加一条)", priority=15, block=True, rule=is_allowed())


@qa_add.handle()
async def handle_qa_add_start(event: MessageEvent, state: T_State):
    text = event.message.extract_plain_text().strip()
    # 尝试一步式：记一下 问题 | 答案
    m = re.search(r"\A(?:记一下|添加问答|我来加一条)\s*(.+?)\s*\|\s*(.+)", text)
    if m:
        question, answer = m.group(1).strip(), m.group(2).strip()
        if question and answer:
            text_content, image_urls = _extract_content(event)
            images = await _resolve_images(image_urls) if image_urls else []
            async with async_session() as session:
                item = QA(
                    question=question,
                    answer=answer,
                    images=json.dumps(images, ensure_ascii=False) if images else None,
                    created_by=str(event.user_id),
                )
                session.add(item)
                await session.commit()
                await session.refresh(item)
            await qa_add.finish(f"好嘞，加好了，编号{item.id}")
    # 交互式：先问问题
    state["flow"] = "add_question"
    await qa_add.pause("要记什么问题呀？")


# ── 列出问答 ────────────────────────────────────────────

qa_list = on_regex(r"\A(?:看看问答|问答列表|最近都记了啥|qa\s+list)", priority=15, block=True, rule=is_allowed())


@qa_list.handle()
async def handle_qa_list():
    async with async_session() as session:
        result = await session.execute(
            select(QA).order_by(QA.id.desc()).limit(config.qa_list_limit)
        )
        items = list(result.scalars().all())
    if not items:
        await qa_list.finish("还没有记录呢")
    lines = [it.format_short() for it in items]
    await qa_list.finish("最近记了这些：\n" + "\n".join(lines))


# ── 搜索问答 ────────────────────────────────────────────

qa_find = on_regex(
    r"\A(?:查一下|搜|搜索|查找|查询)\s*(.+)\Z", priority=15, block=True, rule=is_allowed()
)


@qa_find.handle()
async def handle_qa_find(event: MessageEvent, state: T_State):
    keyword: str = state["_matched"].group(1).strip()
    if not keyword:
        return
    async with async_session() as session:
        result = await session.execute(
            select(QA)
            .where(QA.question.contains(keyword))
            .order_by(QA.id.desc())
            .limit(config.qa_list_limit)
        )
        items = list(result.scalars().all())
    if not items:
        await qa_find.finish(f"没找到和\"{keyword}\"相关的")
    lines = [it.format_short() for it in items]
    await qa_find.finish(f"搜到了这些（{keyword}）：\n" + "\n".join(lines))


# ── 查看详情 ────────────────────────────────────────────

qa_get = on_regex(r"\A(?:第\s*(\d+)\s*条|#(\d+))\Z", priority=18, block=True, rule=is_allowed())


@qa_get.handle()
async def handle_qa_get(event: MessageEvent, state: T_State):
    m = state["_matched"]
    item_id = int(m.group(1) or m.group(2))
    async with async_session() as session:
        item = await session.get(QA, item_id)
    if not item:
        await qa_get.finish(f"没找到第{item_id}条")
    await qa_get.finish(_build_answer_msg(item))


# ── 编辑问答 ────────────────────────────────────────────

qa_edit = on_regex(r"\A改一下第\s*(\d+)\s*条\Z", priority=15, block=True, rule=is_allowed())


@qa_edit.handle()
async def handle_qa_edit_start(state: T_State):
    item_id = int(state["_matched"].group(1))
    async with async_session() as session:
        item = await session.get(QA, item_id)
    if not item:
        await qa_edit.finish(f"没找到第{item_id}条")
    state["flow"] = "edit_choose"
    state["edit_id"] = item_id
    await qa_edit.send(
        f"当前内容：\nQ: {item.question}\nA: {item.answer}\n\n"
        "要改哪个？1.问题 2.答案"
    )
    await qa_edit.pause("")


# ── 删除问答 ────────────────────────────────────────────

qa_del = on_regex(r"\A(?:删掉|删除)第?\s*(\d+)\s*条\Z", priority=15, block=True, rule=is_allowed())


@qa_del.handle()
async def handle_qa_del_start(state: T_State):
    del_id = int(state["_matched"].group(1))
    state["flow"] = "del_confirm"
    state["del_id"] = del_id
    await qa_del.pause(f"确定要删第{del_id}条吗？回复\"是\"确认")


# ── 多轮对话续接 ────────────────────────────────────────

# 这些 matcher 优先级最低，只在多轮流程中匹配用户回复
qa_continue = on_regex(r".+", priority=99, block=True, rule=is_allowed())


@qa_continue.handle()
async def handle_continuation(event: MessageEvent, state: T_State, matcher: Matcher):
    # 检查是否有活跃的多轮流程
    flow = state.get("flow")
    if not flow:
        matcher.skip()

    if flow == "add_question":
        question = event.message.extract_plain_text().strip()
        if not question:
            await qa_continue.reject("问题不能为空，重新说一个吧")
        state["question"] = question
        state["flow"] = "add_answer"
        await qa_continue.pause("答案是什么呢？（可以发文字或图片）")

    elif flow == "add_answer":
        text, image_urls = _extract_content(event)
        if not text and not image_urls:
            await qa_continue.reject("答案不能为空呀，再发一次")
        images = await _resolve_images(image_urls) if image_urls else []
        async with async_session() as session:
            item = QA(
                question=state["question"],
                answer=text,
                images=json.dumps(images, ensure_ascii=False) if images else None,
                created_by=str(event.user_id),
            )
            session.add(item)
            await session.commit()
            await session.refresh(item)
        new_id = item.id
        state.clear()
        await qa_continue.finish(f"好嘞，加好了，编号{new_id}")

    elif flow == "edit_choose":
        item_id = state["edit_id"]
        async with async_session() as session:
            item = await session.get(QA, item_id)
        if not item:
            state.clear()
            await qa_continue.finish("这条好像被删了")
        await qa_continue.send(
            f"当前内容：\nQ: {item.question}\nA: {item.answer}\n\n"
            "要改哪个？1.问题 2.答案"
        )
        state["flow"] = "edit_field"
        await qa_continue.pause("")

    elif flow == "edit_field":
        choice = event.message.extract_plain_text().strip()
        if choice == "1":
            state["flow"] = "edit_question"
            await qa_continue.pause("新的问题是什么？")
        elif choice == "2":
            state["flow"] = "edit_answer"
            await qa_continue.pause("新的答案是什么？（可以发文字或图片）")
        else:
            await qa_continue.reject("回复 1 或 2 就行")

    elif flow == "edit_question":
        new_q = event.message.extract_plain_text().strip()
        if not new_q:
            await qa_continue.reject("问题不能为空，重新说一个吧")
        async with async_session() as session:
            item = await session.get(QA, state["edit_id"])
            if not item:
                state.clear()
                await qa_continue.finish("这条好像被删了")
            item.question = new_q
            await session.commit()
        state.clear()
        await qa_continue.finish("好，问题改好了")

    elif flow == "edit_answer":
        text, image_urls = _extract_content(event)
        if not text and not image_urls:
            await qa_continue.reject("答案不能为空呀，再发一次")
        images = await _resolve_images(image_urls) if image_urls else []
        async with async_session() as session:
            item = await session.get(QA, state["edit_id"])
            if not item:
                state.clear()
                await qa_continue.finish("这条好像被删了")
            item.answer = text
            item.images = json.dumps(images, ensure_ascii=False) if images else None
            await session.commit()
        state.clear()
        await qa_continue.finish("好，答案改好了")

    elif flow == "del_confirm":
        answer = event.message.extract_plain_text().strip()
        if answer == "是":
            del_id = state["del_id"]
            async with async_session() as session:
                item = await session.get(QA, del_id)
                if item:
                    await session.delete(item)
                    await session.commit()
                    state.clear()
                    await qa_continue.finish(f"好，第{del_id}条删掉了")
                else:
                    state.clear()
                    await qa_continue.finish("这条好像已经被删了")
        else:
            state.clear()
            await qa_continue.finish("那就不删了")
