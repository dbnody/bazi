# -*- coding: utf-8 -*-
"""历法核心：公历/农历/干支/节气/真太阳时/万年历.

精度说明:
  - 农历、节气、干支、建除、宜忌、二十八宿等由 lunar-python（寿星天文历算法，
    节气精确到分）计算，与《中国天文年历》《协纪辨方书》通书一致。
  - 真太阳时 = 北京时间 + 经度时差 + 均时差（NOAA 近似式，误差 < 1 分钟）。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from lunar_python import Solar

from .constants import GAN, ZHI, MONTH_JIEQI

SHICHEN = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
SHICHEN_RANGE = ["23:00-00:59", "01:00-02:59", "03:00-04:59", "05:00-06:59",
                 "07:00-08:59", "09:00-10:59", "11:00-12:59", "13:00-14:59",
                 "15:00-16:59", "17:00-18:59", "19:00-20:59", "21:00-22:59"]
SHICHEN_MID_HOUR = [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22]  # 各时辰中点（子时取 00:00）


def shichen_index(dt: datetime) -> int:
    """时辰序号：子=0 … 亥=11（23:00 起为子时）。"""
    return (dt.hour + 1) // 2 % 12


def shichen_name(dt: datetime) -> str:
    return SHICHEN[shichen_index(dt)] + "时"


def equation_of_time(dt: datetime) -> float:
    """均时差（分钟），NOAA 近似式。"""
    doy = dt.timetuple().tm_yday
    g = 2 * math.pi / 365.0 * (doy - 1 + (dt.hour - 12) / 24.0)
    return 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g)
                     - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))


def true_solar_time(dt: datetime, longitude: float) -> tuple[datetime, float]:
    """返回 (真太阳时, 校正分钟数)。longitude 为东经度数，东经为正。"""
    offset = equation_of_time(dt) + 4.0 * (longitude - 120.0)
    return dt + timedelta(minutes=offset), offset


def julian_day(dt: datetime) -> float:
    y, m = dt.year, dt.month
    d = dt.day + (dt.hour + dt.minute / 60 + dt.second / 3600) / 24
    if m <= 2:
        y -= 1
        m += 12
    a = y // 100
    b = 2 - a + a // 4
    return int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + b - 1524.5


def _lunar(solar: Solar):
    return solar.getLunar()


def gz_to_index(gz: str) -> int:
    g, z = GAN.index(gz[0]), ZHI.index(gz[1])
    for i in range(60):
        if i % 10 == g and i % 12 == z:
            return i
    raise ValueError(gz)


@dataclass
class DayInfo:
    """单日通书信息。"""
    year: int
    month: int
    day: int
    weekday: int
    lunar_month_cn: str
    lunar_day_cn: str
    lunar_leap: bool
    lunar_date_cn: str
    gz_year: str
    gz_month: str
    gz_day: str
    gz_time: str = ""
    jieqi: str = ""
    zhixing: str = ""          # 建除十二神
    xiu: str = ""              # 二十八宿
    xiu_luck: str = ""
    tianshen: str = ""         # 黄道黑道十二神
    tianshen_luck: str = ""
    nayin: str = ""
    yi: list = field(default_factory=list)
    ji: list = field(default_factory=list)
    chong: str = ""
    sha: str = ""
    pengzu_gan: str = ""
    pengzu_zhi: str = ""
    jishen: list = field(default_factory=list)
    xiongsha: list = field(default_factory=list)
    festivals: list = field(default_factory=list)
    other_festivals: list = field(default_factory=list)
    shujiu: str = ""
    fushu: str = ""
    yuexiang: str = ""
    xingzuo: str = ""
    taishen: str = ""
    jiuxing: str = ""


def day_info(y: int, m: int, d: int) -> DayInfo:
    solar = Solar.fromYmd(y, m, d)
    lunar = _lunar(solar)
    return DayInfo(
        year=y, month=m, day=d, weekday=solar.getWeek(),
        lunar_month_cn=lunar.getMonthInChinese(), lunar_day_cn=lunar.getDayInChinese(),
        lunar_leap=bool(lunar.getMonth() < 0),
        lunar_date_cn=lunar.toString(),
        gz_year=lunar.getYearInGanZhiExact(), gz_month=lunar.getMonthInGanZhiExact(),
        gz_day=lunar.getDayInGanZhiExact(), jieqi=lunar.getJieQi() or "",
        zhixing=lunar.getZhiXing(), xiu=lunar.getXiu(), xiu_luck=lunar.getXiuLuck(),
        tianshen=lunar.getDayTianShen(), tianshen_luck=lunar.getDayTianShenLuck(),
        nayin=lunar.getDayNaYin(), yi=lunar.getDayYi(), ji=lunar.getDayJi(),
        chong=lunar.getDayChongDesc(), sha=lunar.getDaySha(),
        pengzu_gan=lunar.getPengZuGan(), pengzu_zhi=lunar.getPengZuZhi(),
        jishen=lunar.getDayJiShen(), xiongsha=lunar.getDayXiongSha(),
        festivals=lunar.getFestivals(), other_festivals=lunar.getOtherFestivals(),
        shujiu=lunar.getShuJiu() or "", fushu=lunar.getFu() or "",
        yuexiang=lunar.getYueXiang(), xingzuo=solar.getXingZuo(),
        taishen=lunar.getDayPositionTai(), jiuxing=str(lunar.getDayNineStar()),
    )


def month_grid(year: int, month: int) -> list[list[DayInfo]]:
    """返回 6x7 的月历网格（周一开头），跨月补位。"""
    first = date(year, month, 1)
    lead = first.weekday()  # 0=周一
    start = first - timedelta(days=lead)
    weeks = []
    cur = start
    for _ in range(6):
        row = []
        for _ in range(7):
            row.append(day_info(cur.year, cur.month, cur.day))
            cur += timedelta(days=1)
        weeks.append(row)
    return weeks


def jieqi_of_month(year: int, month: int) -> dict[str, str]:
    """该公历月内的节气：名称 -> 日期时间。"""
    lunar = _lunar(Solar.fromYmd(year, month, 1))
    out = {}
    for name, jq in lunar.getJieQiTable().items():
        if jq.getYear() == year and jq.getMonth() == month:
            out[name] = "%04d-%02d-%02d %02d:%02d" % (
                jq.getYear(), jq.getMonth(), jq.getDay(), jq.getHour(), jq.getMinute())
    return dict(sorted(out.items(), key=lambda kv: kv[1]))


def month_jieqi_name(month_zhi_index: int) -> str:
    """月支序号（寅=0）对应的节令。"""
    order = ["立春", "惊蛰", "清明", "立夏", "芒种", "小暑",
             "立秋", "白露", "寒露", "立冬", "大雪", "小寒"]
    return order[month_zhi_index % 12]


def ganzhi_from_index(i: int) -> str:
    return GAN[i % 10] + ZHI[i % 12]


def jdn_from_date(y: int, m: int, d: int) -> int:
    """儒略日数（整数，用于日柱推算校验）。"""
    return int(julian_day(datetime(y, m, d, 12, 0)) + 0.5)


def solar_terms_year(year: int) -> list[tuple[str, str]]:
    """公历年内二十四个节气的名称与时刻，按时间排序。"""
    lunar = _lunar(Solar.fromYmd(year, 6, 1))
    rows = []
    for name, jq in lunar.getJieQiTable().items():
        if jq.getYear() == year:
            rows.append((name, "%02d-%02d %02d:%02d" % (
                jq.getMonth(), jq.getDay(), jq.getHour(), jq.getMinute())))
    rows.sort(key=lambda r: r[1])
    return rows


def _solar_dt(s) -> datetime:
    return datetime(s.getYear(), s.getMonth(), s.getDay(), s.getHour(), s.getMinute(), s.getSecond())


def lichun_time(year: int) -> datetime:
    """该公历年立春交接时刻（八字年柱分界）。"""
    return _solar_dt(_lunar(Solar.fromYmd(year, 2, 4)).getJieQiTable()["立春"])


def nearest_jieqi(dt: datetime) -> tuple[str, datetime, str, datetime]:
    """离 dt 最近的前一个、后一个「节/气」。"""
    solar = Solar.fromYmdHms(dt.year, dt.month, dt.day, dt.hour, dt.minute, 0)
    lunar = _lunar(solar)
    prev = lunar.getPrevJieQi(True)
    nxt = lunar.getNextJieQi(True)
    return (prev.getName(), _solar_dt(prev.getSolar()),
            nxt.getName(), _solar_dt(nxt.getSolar()))
