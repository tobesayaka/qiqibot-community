from __future__ import annotations

import base64
import io

from nonebot import on_regex
from nonebot.adapters.onebot.v11 import MessageEvent, MessageSegment
from nonebot.typing import T_State
from PIL import Image, ImageDraw, ImageFont

from utils.permission import is_allowed

_FONT = "/Users/ming/Library/Fonts/NotoSansSC.ttf"
_FONT_SIZE = 16
_LINE_H = 26
_PAD = 20
_GAP = 10
_BG = (28, 28, 32)
_SECTION_BG = (38, 38, 44)
_TITLE = (255, 255, 255)
_CMD = (100, 200, 255)
_DESC = (200, 220, 235)
_EXAMPLE = (160, 175, 200)
_SECTION_TITLE = (255, 200, 100)
_DIM = (130, 130, 135)

# 每个 section: (title, [(cmd, desc, [examples])])
SECTIONS = [
    ("游戏数据查询", [
        ("opt <关键词/ID>", "查询释放卷轴道具", ["opt 暴风", "opt 10709"]),
        ("prd <关键词/ID>", "查询装备打造配方", ["prd 释魂 琴", "prd 释魂*琴", "prd 13814"]),
        ("up <关键词/ID>", "查询装备改造方案", ["up 释魂 弓", "up 释魂*弓", "up 1040054"]),
        ("title <关键词/ID>", "查询头衔信息", ["title 勇者", "title 11072"]),
        ("totem <关键词/ID>", "查询图腾信息", ["totem 攻击", "totem 52358"]),
    ]),
    ("问答知识库", [
        ("记一下", "添加问答（交互式引导）", []),
        ("记一下 问题 | 答案", "一步添加问答", ["记一下 洛奇官网 | https://mabinogi.nexon.com"]),
        ("查一下 <关键词>", "搜索问答", ["查一下 洛奇"]),
        ("看看问答", "查看最近添加的问答列表", []),
        ("第<N>条 / #<N>", "查看问答详情", ["第3条", "#3"]),
        ("改一下第<N>条", "编辑指定问答", ["改一下第3条"]),
        ("删掉第<N>条", "删除指定问答", ["删掉第3条"]),
    ]),
    ("其他功能", [
        ("复读 <内容>", "机器人原样回复", ["复读 你好世界"]),
        ("下载 <链接>", "下载视频（抖音/B站/YouTube）", ["下载 https://v.douyin.com/xxx"]),
        ("帮助 / help", "显示本帮助信息", []),
    ]),
]


def _render_help() -> str:
    font = ImageFont.truetype(_FONT, _FONT_SIZE)
    small_font = ImageFont.truetype(_FONT, _FONT_SIZE - 2)

    tmp = Image.new("RGB", (1, 1))
    td = ImageDraw.Draw(tmp)

    def tw(f, text):
        return td.textbbox((0, 0), text, font=f)[2]

    # 计算宽度
    max_w = 0
    for _, items in SECTIONS:
        for cmd, desc, examples in items:
            max_w = max(max_w, tw(font, cmd) + 20 + tw(font, desc))
            for ex in examples:
                max_w = max(max_w, 24 + tw(small_font, ex))

    img_w = _PAD * 2 + max_w + 20
    img_w = max(img_w, 460)

    # 计算高度
    total_h = _PAD
    for section_title, items in SECTIONS:
        total_h += _LINE_H + _GAP  # section title
        for cmd, desc, examples in items:
            total_h += _LINE_H
            total_h += len(examples) * (_LINE_H - 4)
        total_h += _GAP
    total_h += _PAD

    # 绘制
    img = Image.new("RGB", (img_w, total_h), _BG)
    draw = ImageDraw.Draw(img)

    y = _PAD

    # 标题
    draw.text((_PAD, y), "QiqiBot 使用指南", fill=_TITLE, font=ImageFont.truetype(_FONT, 20))
    y += _LINE_H + _GAP

    for si, (section_title, items) in enumerate(SECTIONS):
        # section 背景
        sec_h = _LINE_H + _GAP
        for cmd, desc, examples in items:
            sec_h += _LINE_H + len(examples) * (_LINE_H - 4)
        draw.rectangle([_PAD - 4, y - 2, img_w - _PAD + 4, y + sec_h], fill=_SECTION_BG)

        # section 标题
        draw.text((_PAD, y), f"▸ {section_title}", fill=_SECTION_TITLE, font=font)
        y += _LINE_H + 4

        for cmd, desc, examples in items:
            # 指令 + 描述
            draw.text((_PAD + 8, y), cmd, fill=_CMD, font=font)
            cmd_w = tw(font, cmd)
            draw.text((_PAD + 8 + cmd_w + 12, y), desc, fill=_DESC, font=font)
            y += _LINE_H

            # 示例
            for ex in examples:
                draw.text((_PAD + 24, y), f"例: {ex}", fill=_EXAMPLE, font=small_font)
                y += _LINE_H - 4

        y += _GAP

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return f"base64://{base64.b64encode(buf.getvalue()).decode()}"


help_cmd = on_regex(
    r"\A(help|帮助|怎么用|指令列表|使用方法|使用说明)\Z",
    priority=20,
    block=True,
    rule=is_allowed(),
)


@help_cmd.handle()
async def handle_help(event: MessageEvent, state: T_State):
    await help_cmd.finish(MessageSegment.image(_render_help()))
