# -*- coding: utf-8 -*-
"""终端/文本框排版小工具（按显示宽度对齐，中日韩字符占两列）。"""
from __future__ import annotations

import unicodedata


def disp_width(text: str) -> int:
    return sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in text)


def pad(text: str, width: int) -> str:
    """右侧补空格至 width 显示列。"""
    return text + " " * max(0, width - disp_width(text))
