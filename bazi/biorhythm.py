# -*- coding: utf-8 -*-
"""七种生物钟（人体生物节律）.

渊源: 19 世纪末 Wilhelm Fliess（体力 23 天、情绪 28 天）与 Hermann Swoboda；
      20 世纪 Alfred Teltscher 增补智力 33 天，合称「经典三节律」；
      后世以斐波那契式递推（23/28/33 后每加 5 天）扩充为直觉 38、审美 43、
      心灵 48、灵性 53 天，共七种，称「七节律」。
公式: 值 = sin(2π · t / T) × 100%，t 为出生至目标时刻的天数。
判定: 值 > +6% 为高潮期，< -6% 为低潮期，其余为临界期。
说明: 生物节律属经验模型，未获主流生理学验证，宜作自我观察参考。
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta

CYCLES = [
    ("体力", 23, "Physical", "体能、耐力、抗病力"),
    ("情绪", 28, "Emotional", "心情、感受、人际"),
    ("智力", 33, "Intellectual", "思维、记忆、判断"),
    ("直觉", 38, "Intuitive", "灵感、预感、洞察"),
    ("审美", 43, "Aesthetic", "品味、情趣、创作"),
    ("心灵", 48, "Spiritual", "意志、信念、定力"),
    ("灵性", 53, "Awareness", "觉知、格局、智慧"),
]

PROFILES = {
    "经典三节律（Fleiss/Swoboda）": 3,
    "五节律（含直觉·审美）": 5,
    "七节律（完整七种）": 7,
}

HIGH, LOW, CRIT = "高潮期", "低潮期", "临界期"


@dataclass
class Point:
    name: str
    period: int
    value: float
    phase: str


def _phase(v: float) -> str:
    if v > 6:
        return HIGH
    if v < -6:
        return LOW
    return CRIT


def value(birth: datetime, target: datetime, period: int) -> float:
    t = (target - birth).total_seconds() / 86400.0
    return math.sin(2 * math.pi * t / period) * 100.0


def at(birth: datetime, target: datetime, count: int = 7) -> list[Point]:
    return [Point(n, p, round(value(birth, target, p), 1), _phase(value(birth, target, p)))
            for n, p, _en, _d in CYCLES[:count]]


def series(birth: datetime, start: datetime, days: int, count: int = 7) -> dict:
    """逐日序列：{周期名: [值...]}，另附日期列表。"""
    dates = [start + timedelta(days=i) for i in range(days)]
    out = {n: [round(value(birth, d, p), 1) for d in dates] for n, p, _e, _d in CYCLES[:count]}
    out["__dates__"] = dates
    return out


def critical_days(birth: datetime, start: datetime, days: int, count: int = 7) -> list[tuple[str, str, float]]:
    """区间内的临界日（|值| ≤ 6）。"""
    res = []
    for i in range(days):
        d = start + timedelta(days=i)
        for n, p, _e, _d in CYCLES[:count]:
            v = value(birth, d, p)
            if abs(v) <= 6:
                res.append((f"{d:%Y-%m-%d}", n, round(v, 1)))
    return res


def composite(birth: datetime, target: datetime) -> float:
    """三节律综合指数（体力 30% · 情绪 40% · 智力 30%）。"""
    v = {n: value(birth, target, p) for n, p, _e, _d in CYCLES[:3]}
    return round(v["体力"] * 0.3 + v["情绪"] * 0.4 + v["智力"] * 0.3, 1)


def advice(points: list[Point]) -> list[str]:
    tips = []
    for pt in points:
        if pt.phase == CRIT:
            tips.append(f"{pt.name}处于临界期（{pt.value:+.1f}%），身心转换之际，宜稳妥守常、避免重大决断。")
        elif pt.phase == HIGH and pt.value > 60:
            tips.append(f"{pt.name}处于高潮期（{pt.value:+.1f}%），可积极进取、承担压力。")
        elif pt.phase == LOW and pt.value < -60:
            tips.append(f"{pt.name}处于低潮期（{pt.value:+.1f}%），宜休养调整，避免透支与争执。")
    return tips or ["各项节律均处平缓区间，作息如常即可。"]


def render(birth: datetime, target: datetime, count: int = 7) -> str:
    pts = at(birth, target, count)
    L = [f"【生物钟】出生 {birth:%Y-%m-%d %H:%M}　测算 {target:%Y-%m-%d %H:%M}",
         f"　　已历 {(target - birth).days} 天　综合指数（三节律）{composite(birth, target):+.1f}%", ""]
    L.append("　　周期　名称　　数值　　　状态")
    for p in pts:
        L.append(f"　　{p.period:>3}天　{p.name}　{p.value:+6.1f}%　　{p.phase}")
    L.append("")
    for t in advice(pts):
        L.append(f"　　· {t}")
    return "\n".join(L)
