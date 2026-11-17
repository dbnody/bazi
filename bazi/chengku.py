# -*- coding: utf-8 -*-
"""袁天罡称骨算命.

典籍: 《袁天罡称骨》（又称《称骨算命》《袁天罡称骨歌》，民间相术要籍）
方法: 以农历年干支、农历月份、农历日、时辰各定权重量，四者相加得「骨重」，
      再依骨重查歌诀断吉凶。骨重范围 2 两 1 钱 ~ 7 两 1 钱，共 51 等。
"""
from __future__ import annotations

from datetime import datetime
from functools import lru_cache

from lunar_python import Solar

from .calendar_core import SHICHEN, shichen_index

# 单位：钱（0.1 两 = 1 钱）
YEAR_WEIGHT = {
    "甲子": 12, "乙丑": 9, "丙寅": 6, "丁卯": 7, "戊辰": 12, "己巳": 5,
    "庚午": 9, "辛未": 8, "壬申": 7, "癸酉": 8, "甲戌": 15, "乙亥": 9,
    "丙子": 16, "丁丑": 8, "戊寅": 8, "己卯": 19, "庚辰": 12, "辛巳": 6,
    "壬午": 8, "癸未": 7, "甲申": 5, "乙酉": 15, "丙戌": 6, "丁亥": 16,
    "戊子": 15, "己丑": 7, "庚寅": 9, "辛卯": 12, "壬辰": 10, "癸巳": 7,
    "甲午": 15, "乙未": 6, "丙申": 5, "丁酉": 14, "戊戌": 14, "己亥": 9,
    "庚子": 7, "辛丑": 7, "壬寅": 9, "癸卯": 12, "甲辰": 8, "乙巳": 7,
    "丙午": 13, "丁未": 5, "戊申": 14, "己酉": 5, "庚戌": 9, "辛亥": 17,
    "壬子": 5, "癸丑": 7, "甲寅": 12, "乙卯": 8, "丙辰": 8, "丁巳": 6,
    "戊午": 19, "己未": 6, "庚申": 8, "辛酉": 16, "壬戌": 10, "癸亥": 6,
}

MONTH_WEIGHT = {1: 6, 2: 7, 3: 18, 4: 9, 5: 5, 6: 16,
                7: 9, 8: 15, 9: 18, 10: 8, 11: 9, 12: 5}

DAY_WEIGHT = {
    1: 5, 2: 10, 3: 8, 4: 15, 5: 16, 6: 15, 7: 8, 8: 16, 9: 8, 10: 16,
    11: 9, 12: 17, 13: 8, 14: 17, 15: 10, 16: 8, 17: 9, 18: 18, 19: 5, 20: 15,
    21: 10, 22: 9, 23: 8, 24: 9, 25: 15, 26: 18, 27: 7, 28: 8, 29: 16, 30: 6,
}

HOUR_WEIGHT = {"子": 16, "丑": 6, "寅": 7, "卯": 10, "辰": 9, "巳": 16,
               "午": 10, "未": 8, "申": 8, "酉": 9, "戌": 6, "亥": 6}

CN_NUM = "〇一二三四五六七八九"

TOTAL_COMBOS = 60 * 12 * 30 * 12


@lru_cache(maxsize=None)
def distribution() -> dict[int, int]:
    """60 年 × 12 月 × 30 日 × 12 时 = 259200 种组合的骨重分布（用于同骨重占比）。"""
    d: dict[int, int] = {}
    for wy in YEAR_WEIGHT.values():
        for wm in MONTH_WEIGHT.values():
            for wd in DAY_WEIGHT.values():
                base = wy + wm + wd
                for wh in HOUR_WEIGHT.values():
                    t = base + wh
                    d[t] = d.get(t, 0) + 1
    return d


# 51 首歌诀，键为骨重（钱）
POEMS = {
    21: "短命非业谓大空，平生灾难事重重；凶祸频临陷逆境，终世困苦事不成。",
    22: "身寒骨冷苦伶仃，此命推来行乞人；劳劳碌碌无度日，终年打拱过平生。",
    23: "此命推来骨格轻，求谋作事事难成；妻儿兄弟应难许，别处他乡作散人。",
    24: "此命推来福禄无，门庭困苦总难荣；六亲骨肉皆无靠，流浪他乡作老翁。",
    25: "此命推来祖业微，门庭营度似稀奇；六亲骨肉如冰炭，一世勤劳自把持。",
    26: "平生衣禄苦中求，独自营谋事不休；离祖出门宜早计，晚来衣禄自无忧。",
    27: "一生作事少商量，难靠祖宗作主张；独马单枪空做去，早年晚岁总无长。",
    28: "一生作事似飘蓬，祖宗产业在梦中；若不过房并改姓，也当移徙二三通。",
    29: "初年运限未曾亨，纵有功名在后成；须过四旬方可立，移居改姓始为良。",
    30: "劳劳碌碌苦中求，东奔西走何日休；若使终身勤与俭，老来稍可免忧愁。",
    31: "忙忙碌碌苦中求，何日云开见日头；难得祖基家可立，中年衣食渐无忧。",
    32: "初年运蹇事难谋，渐有财源如水流；到得中年衣食旺，那时名利一齐收。",
    33: "早年作事事难成，百计徒劳枉费心；半世自如流水去，后来运到得黄金。",
    34: "此命福气果如何，僧道门中衣禄多；离祖出家方为妙，朝晚拜佛念弥陀。",
    35: "生平福量不周全，祖业根基觉少传；营事生涯宜守旧，时来衣食胜从前。",
    36: "不须劳碌过平生，独自成家福不轻；早有福星常照命，任君行去百般成。",
    37: "此命般般事不成，弟兄少力自孤行；虽然祖业须微有，来得明时去不明。",
    38: "一生骨肉最清高，早入黉门姓名标；待看年将三十六，蓝衫脱去换红袍。",
    39: "此命终身运不通，劳劳作事尽皆空；苦心竭力成家计，到得那时在梦中。",
    40: "平生衣禄是绵长，件件心中自主张；前面风霜多受过，后来必定享安康。",
    41: "此命推来事不同，为人能干异凡庸；中年还有逍遥福，不比前时运未通。",
    42: "得宽怀处且宽怀，何用双眉皱不开；若使中年命运济，那时名利一齐来。",
    43: "为人心性最聪明，作事轩昂近贵人；衣禄一生天数定，不须劳碌是丰亨。",
    44: "万事由天莫苦求，须知福禄命里收；少壮名利难如意，晚景欣然更不忧。",
    45: "名利推来竟若何，前番辛苦后奔波；命中难养男和女，骨肉扶持也不多。",
    46: "东西南北尽皆通，出姓移居更觉隆；衣禄无亏天数定，中年晚景一般同。",
    47: "此命推来旺末年，妻荣子贵自怡然；平生原有滔滔福，可有财源如水泉。",
    48: "幼年运道未曾亨，若是蹉跎再不兴；兄弟六亲皆无靠，一身事业晚年成。",
    49: "此命推来福不轻，自成自立显门庭；从来富贵人钦敬，使婢差奴过一生。",
    50: "为利为名终日劳，中年福禄也多遭；老来是有财星照，不比前番目下高。",
    51: "一世荣华事事通，不须劳碌自亨通；弟兄叔侄皆如意，家业成时福禄宏。",
    52: "一世亨通事事能，不须劳思自然能；宗族欣然心皆好，家业丰亨自称心。",
    53: "此格推来气象真，兴家发达在其中；一生福禄安排定，却是人间一富翁。",
    54: "此命推来厚且清，诗书满腹看功成；丰衣足食自然稳，正是人间有福人。",
    55: "走马扬鞭争名利，少年做事费筹论；一朝福禄源源至，富贵荣华显六亲。",
    56: "此格推来礼义通，一生福禄用无穷；甜酸苦辣皆尝过，滚滚财源稳且丰。",
    57: "福禄丰盈万事全，一生荣耀显双亲；名扬威震人钦敬，处世逍遥似遇春。",
    58: "平生福禄自然来，名利兼全福寿偕；雁塔题名为贵客，紫袍金带走金阶。",
    59: "细推此格妙且清，必定才高礼义通；甲第之中应有分，扬鞭走马显威荣。",
    60: "一朝金榜快题名，显祖荣宗立大功；衣食定然原裕足，田园财帛更丰盈。",
    61: "不作朝中金榜客，定为世上大财翁；聪明天赋经书熟，名显高科自是荣。",
    62: "此命生来福不穷，读书必定显亲宗；紫衣金带为卿相，富贵荣华皆可同。",
    63: "命主为官福禄长，得来富贵实丰常；名题雁塔传金榜，大显门庭天下扬。",
    64: "此格威权不可当，紫袍金带坐高堂；荣华富贵谁能及，万古留名姓氏扬。",
    65: "细推此命福非轻，富贵荣华孰与争；定国安邦人极品，威声显赫震寰瀛。",
    66: "此格人间一福人，堆金积玉满堂春；从来富贵由天定，正笏垂绅谒圣君。",
    67: "此命生来福自宏，田园家业最高隆；平生衣禄丰盈足，一世荣华万事通。",
    68: "富贵由天莫苦求，万金家计不须谋；如今不比前番事，祖业根基千古留。",
    69: "君是人间衣禄星，一生富贵众人钦；纵然福禄由天定，安享荣华过一生。",
    70: "此命推来福不轻，何须愁虑苦劳心；荣华富贵已天定，正笏垂绅拜紫宸。",
    71: "此命生成大不同，公侯卿相在其中；一生自有逍遥福，富贵荣华极品隆。",
}

# 骨重等级评语（《称骨》通行本：轻主劳碌，重主富贵）
def grade(qian: int) -> str:
    if qian <= 29:
        return "极轻（劳碌辛苦之命）"
    if qian <= 39:
        return "偏轻（奔波求财之命）"
    if qian <= 49:
        return "中平（衣食渐丰之命）"
    if qian <= 59:
        return "偏重（福禄丰厚之命）"
    return "厚重（富贵极品之命）"


def _cn_num(n: int) -> str:
    if n < 10:
        return CN_NUM[n]
    if n < 20:
        return "十" + CN_NUM[n % 10] if n % 10 else "十"
    return CN_NUM[n // 10] + "十" + (CN_NUM[n % 10] if n % 10 else "")


def weight_text(qian: int) -> str:
    if qian < 10:
        return f"{_cn_num(qian)}钱"
    liang, rest = divmod(qian, 10)
    if rest == 0:
        return f"{_cn_num(liang)}两"
    return f"{_cn_num(liang)}两{_cn_num(rest)}钱"


def calc(dt: datetime, gender: str = "男", hour_known: bool = True,
         hour_label: str = "") -> dict:
    """按公历出生时刻推算骨重。

    hour_known=False 表示时辰不详：不计时柱权重（时柱为 6~16 钱），
    所得为「三柱骨重」，仅供参看，不作完整断语。
    """
    solar = Solar.fromYmdHms(dt.year, dt.month, dt.day, dt.hour, dt.minute, 0)
    lunar = solar.getLunar()
    gz_year = lunar.getYearInGanZhi()
    month = abs(lunar.getMonth())
    day = lunar.getDay()
    zhi = SHICHEN[shichen_index(dt)]

    y, m, d = YEAR_WEIGHT[gz_year], MONTH_WEIGHT[month], DAY_WEIGHT[day]
    parts = [("年（" + gz_year + "）", y), ("月（" + _cn_num(month) + "月）", m),
             ("日（" + _cn_num(day) + "日）", d)]
    if hour_known:
        h = HOUR_WEIGHT[zhi]
        parts.append(("时（" + zhi + "时）", h))
        total = y + m + d + h
        poem = POEMS.get(total, "（此骨重超出通行歌诀范围）")
    else:
        total = y + m + d
        poem = None
    return {
        "gender": gender,
        "birth": dt,
        "hour_known": hour_known,
        "hour_label": hour_label,
        "lunar": lunar.toString(),
        "gz_year": gz_year,
        "month": month,
        "day": day,
        "shichen": (zhi + "时") if hour_known else "时辰不详",
        "parts": parts,
        "total": total,
        "weight_text": weight_text(total),
        "grade": grade(total),
        "pct": distribution().get(total, 0) / TOTAL_COMBOS * 100,
        "poem": poem,
    }


def render(result: dict) -> str:
    birth_text = result.get("hour_label") or f"{result['birth']:%Y-%m-%d %H:%M}"
    L = [f"【称骨算命】{result['gender']}命　{birth_text}",
         f"　　农历 {result['lunar']}　{result['shichen']}",
         "",
         ("　　四柱权重：" if result["hour_known"] else "　　三柱权重：") + "　".join(f"{lb}{weight_text(q)}" for lb, q in result["parts"]),
         ""]
    if not result["hour_known"]:
        L.append(f"　　【三柱骨重】{result['weight_text']}　〔时辰不详，未含时柱〕")
        L.append("　　【说明】时柱权重在 六钱 ~ 一两六钱 之间，故实际骨重应在此值之上；")
        L.append("　　　　　　补上时辰后可再测算，方能得完整歌诀与评语。")
        lo, hi = result["total"] + min(HOUR_WEIGHT.values()), result["total"] + max(HOUR_WEIGHT.values())
        L.append(f"　　【区间】{weight_text(lo)} ~ {weight_text(hi)}"
                 f"（同区间组合占比约 {sum(distribution().get(x, 0) for x in range(lo, hi + 1)) / TOTAL_COMBOS * 100:.1f}%）")
    else:
        L.append(f"　　【骨重】{result['weight_text']}　〔{result['grade']}〕")
        L.append(f"　　【歌诀】{result['poem']}")
        L.append(f"　　【占比】同骨重者约 {result['pct']:.2f}%（{TOTAL_COMBOS} 种年月日时组合）")
    L.append("")
    L.append("　　注：称骨之法以农历年干支、月、日、时辰四柱重量相加，属《袁天罡称骨》传统相术，")
    L.append("　　　　仅供文化娱乐参考；同一骨重男命女命断语有别，古籍另有女命注文。")
    return "\n".join(L)
