# -*- coding: utf-8 -*-
"""六爻（纳甲筮法）.

学理依据:
  《京氏易传》(汉·京房)        —— 八宫卦序、纳甲、世应
  《增删卜易》(清·野鹤老人)    —— 用神、旺衰、动变、旬空、月破
  《卜筮正宗》(清·王洪绪)      —— 装卦体例、六亲六神、伏神
  《梅花易数》(宋·邵雍)        —— 时间起卦（辅法，本程序可选）

体例说明:
  - 爻位自下而上，初爻为 1、上爻为 6；阳爻记「—」，阴爻记「- -」；
  - 老阳(9)、老阴(6) 为动爻，动则生变卦；少阳(7)、少阴(8) 为静爻；
  - 六亲以卦宫五行为「我」，爻支五行为「彼」：生我父母、我生子孙、
    克我官鬼、我克妻财、比和兄弟（《卜筮正宗·六亲》）。
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime

from . import constants as C
from .textutil import pad

GAN, ZHI = C.GAN, C.ZHI
ZHI_WX = C.ZHI_WUXING
WX_SHENG = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
WX_KE = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}

# 地支六合、六冲、三合
LIUHE_PAIRS = {frozenset(p) for p in [(("子", "丑")), (("寅", "亥")), (("卯", "戌")),
                                      (("辰", "酉")), (("巳", "申")), (("午", "未"))]}
LIUCHONG_PAIRS = {frozenset(p) for p in [(("子", "午")), (("丑", "未")), (("寅", "申")),
                                         (("卯", "酉")), (("辰", "戌")), (("巳", "亥"))]}

# --------------------------------------------------------------------------- #
# 八卦：爻自下而上，1 阳 0 阴；na = (内卦三爻、外卦三爻) 纳甲干支
# --------------------------------------------------------------------------- #
TRI = {
    "乾": dict(sym="☰", bits=(1, 1, 1), wx="金", na=(("甲子", "甲寅", "甲辰"), ("壬午", "壬申", "壬戌")), num=1),
    "兑": dict(sym="☱", bits=(1, 1, 0), wx="金", na=(("丁巳", "丁卯", "丁丑"), ("丁亥", "丁酉", "丁未")), num=2),
    "离": dict(sym="☲", bits=(1, 0, 1), wx="火", na=(("己卯", "己丑", "己亥"), ("己酉", "己未", "己巳")), num=3),
    "震": dict(sym="☳", bits=(1, 0, 0), wx="木", na=(("庚子", "庚寅", "庚辰"), ("庚午", "庚申", "庚戌")), num=4),
    "巽": dict(sym="☴", bits=(0, 1, 1), wx="木", na=(("辛丑", "辛亥", "辛酉"), ("辛未", "辛巳", "辛卯")), num=5),
    "坎": dict(sym="☵", bits=(0, 1, 0), wx="水", na=(("戊寅", "戊辰", "戊午"), ("戊申", "戊戌", "戊子")), num=6),
    "艮": dict(sym="☶", bits=(0, 0, 1), wx="土", na=(("丙辰", "丙午", "丙申"), ("丙戌", "丙子", "丙寅")), num=7),
    "坤": dict(sym="☷", bits=(0, 0, 0), wx="土", na=(("乙未", "乙巳", "乙卯"), ("癸丑", "癸亥", "癸酉")), num=8),
}
TRI_BY_BITS = {v["bits"]: k for k, v in TRI.items()}
TRI_ORDER = ["乾", "兑", "离", "震", "巽", "坎", "艮", "坤"]  # 先天数一至八

# 京房八宫：本宫卦 + 一世至五世、游魂、归魂（世应位置依《京氏易传》）
PALACES = [
    ("乾", ["乾为天", "天风姤", "天山遁", "天地否", "风地观", "山地剥", "火地晋", "火天大有"]),
    ("坎", ["坎为水", "水泽节", "水雷屯", "水火既济", "泽火革", "雷火丰", "地火明夷", "地水师"]),
    ("艮", ["艮为山", "山火贲", "山天大畜", "山泽损", "火泽睽", "天泽履", "风泽中孚", "风山渐"]),
    ("震", ["震为雷", "雷地豫", "雷水解", "雷风恒", "地风升", "水风井", "泽风大过", "泽雷随"]),
    ("巽", ["巽为风", "风天小畜", "风火家人", "风雷益", "天雷无妄", "火雷噬嗑", "山雷颐", "山风蛊"]),
    ("离", ["离为火", "火山旅", "火风鼎", "火水未济", "山水蒙", "风水涣", "天水讼", "天火同人"]),
    ("坤", ["坤为地", "地雷复", "地泽临", "地天泰", "雷天大壮", "泽天夬", "水天需", "水地比"]),
    ("兑", ["兑为泽", "泽水困", "泽地萃", "泽山咸", "水山蹇", "地山谦", "雷山小过", "雷泽归妹"]),
]
SHI_YING = [(6, 3), (1, 4), (2, 5), (3, 6), (4, 1), (5, 2), (4, 1), (3, 6)]
GEN_NAMES = ["本宫", "一世", "二世", "三世", "四世", "五世", "游魂", "归魂"]


def _gen_palace(bits: tuple[int, ...]) -> list[tuple[int, ...]]:
    """由本宫卦推出八宫卦序的八个卦（自下而上变爻）。"""
    b = list(bits)
    out = [tuple(b)]
    for k in range(1, 6):                       # 一世~五世：变初爻起逐爻上变
        nb = list(bits)
        for i in range(k):
            nb[i] ^= 1
        out.append(tuple(nb))
    youhun = list(out[5])
    youhun[3] ^= 1                              # 游魂：五世卦再变外卦下爻
    out.append(tuple(youhun))
    guihun = list(youhun)
    guihun[0:3] = b[0:3]                        # 归魂：游魂内卦复归本宫
    out.append(tuple(guihun))
    return out


@dataclass(frozen=True)
class Gua:
    name: str
    bits: tuple[int, ...]
    palace: str
    wx: str
    shi: int
    ying: int
    kind: str
    na: tuple[str, ...]          # 六爻纳甲（初→上）

    @property
    def upper(self) -> str:
        return TRI_BY_BITS[self.bits[3:]]

    @property
    def lower(self) -> str:
        return TRI_BY_BITS[self.bits[0:3]]

    @property
    def full_name(self) -> str:
        return f"{self.name}（{self.palace}宫·{self.kind}卦）"


def _build_guas() -> dict[tuple[int, ...], Gua]:
    table: dict[tuple[int, ...], Gua] = {}
    for palace, names in PALACES:
        base = TRI[palace]["bits"] * 2          # 本宫卦：内外同卦
        bits_list = _gen_palace(base)
        assert len(bits_list) == 8
        for idx, bits in enumerate(bits_list):
            up, low = TRI_BY_BITS[bits[3:]], TRI_BY_BITS[bits[0:3]]
            na = tuple(TRI[low]["na"][0] + TRI[up]["na"][1])
            shi, ying = SHI_YING[idx]
            table[bits] = Gua(names[idx], bits, palace, TRI[palace]["wx"], shi, ying,
                              GEN_NAMES[idx], na)
    assert len(table) == 64, len(table)
    return table


GUAS = _build_guas()


# --------------------------------------------------------------------------- #
# 五行生克与六亲
# --------------------------------------------------------------------------- #
def liuqin(me: str, other: str) -> str:
    if me == other:
        return "兄弟"
    if WX_SHENG[other] == me:
        return "父母"
    if WX_SHENG[me] == other:
        return "子孙"
    if WX_KE[other] == me:
        return "官鬼"
    return "妻财"


def zhi_wx(gz: str) -> str:
    return ZHI_WX[gz[-1]]


def kong_wang(gz: str) -> str:
    """旬空（以日干支推）。"""
    g, z = GAN.index(gz[0]), ZHI.index(gz[1])
    start = (z - g) % 12
    return ZHI[(start + 10) % 12] + ZHI[(start + 11) % 12]


LIUSHEN = ["青龙", "朱雀", "勾陈", "螣蛇", "白虎", "玄武"]


def liushen_of_day(day_gan: str) -> list[str]:
    """六神起例：甲乙起青龙、丙丁起朱雀、戊起勾陈、己起螣蛇、庚辛起白虎、壬癸起玄武。"""
    head = {"甲": 0, "乙": 0, "丙": 1, "丁": 1, "戊": 2, "己": 3, "庚": 4, "辛": 4, "壬": 5, "癸": 5}[day_gan]
    return [LIUSHEN[(head + i) % 6] for i in range(6)]


def wangshuai(x: str, ling: str) -> str:
    """旺相休囚死：同令旺、令生我相、我生令休、我克令囚、令克我死。"""
    if x == ling:
        return "旺"
    if WX_SHENG[ling] == x:
        return "相"
    if WX_SHENG[x] == ling:
        return "休"
    if WX_KE[x] == ling:
        return "囚"
    return "死"


# --------------------------------------------------------------------------- #
# 起卦
# --------------------------------------------------------------------------- #
def cast_coins(n: int = 6) -> list[int]:
    """摇钱法：三枚铜钱（正 3、反 2），三枚之和 6/7/8/9，自初爻至上爻。"""
    return [sum(3 if random.getrandbits(1) else 2 for _ in range(3)) for _ in range(n)]


def cast_time(dt: datetime) -> list[int]:
    """梅花易数时间起卦：年支数+月+日为上卦，再加时支数为下卦，总数取动爻。"""
    from lunar_python import Solar
    s = Solar.fromYmdHms(dt.year, dt.month, dt.day, dt.hour, dt.minute, 0)
    lu = s.getLunar()
    yz = ZHI.index(lu.getYearInGanZhi()[1]) + 1
    month, day = abs(lu.getMonth()), lu.getDay()
    hz = ((dt.hour + 1) // 2) % 12 + 1
    up = (yz + month + day - 1) % 8 + 1
    low = (yz + month + day + hz - 1) % 8 + 1
    dong = (yz + month + day + hz - 1) % 6 + 1
    up_bits, low_bits = TRI[TRI_ORDER[up - 1]]["bits"], TRI[TRI_ORDER[low - 1]]["bits"]
    lines = [7] * 6
    for i in range(3):
        lines[i] = 9 if low_bits[i] else 8
        lines[i + 3] = 9 if up_bits[i] else 8
    # 动爻：阳动取 9、阴动取 6
    lines[dong - 1] = 9 if lines[dong - 1] in (7, 9) else 6
    return lines


def from_coins_text(text: str) -> list[int]:
    """解析手动输入，如 "789789"（初爻在前）或 "6,7,8,9,7,8"。"""
    nums = [int(ch) for ch in text if ch.isdigit()]
    if len(nums) != 6 or any(n not in (6, 7, 8, 9) for n in nums):
        raise ValueError("请按「初爻到上爻」输入 6 位数字，每位取 6/7/8/9（6 老阴、7 少阳、8 少阴、9 老阳）")
    return nums


# --------------------------------------------------------------------------- #
# 用神取用（《增删卜易·用神章》）
# --------------------------------------------------------------------------- #
YONGSHEN = {
    "财运": "妻财", "求财": "妻财", "生意": "妻财", "投资": "妻财", "工资": "妻财",
    "事业": "官鬼", "工作": "官鬼", "官运": "官鬼", "功名": "官鬼", "考试": "官鬼",
    "官司": "官鬼", "疾病": "官鬼", "健康": "官鬼",
    "文书": "父母", "房产": "父母", "学业": "父母", "长辈": "父母", "合同": "父母",
    "子女": "子孙", "孕产": "子孙", "宠物": "子孙", "出行": "子孙",
    "兄弟": "兄弟", "朋友": "兄弟", "合伙": "兄弟", "竞争": "兄弟",
    "感情": "世爻", "婚姻": "世爻", "寻人": "世爻", "失物": "妻财",
}


@dataclass
class Line:
    pos: int                 # 1~6，初爻为 1
    yinyang: int             # 1 阳 0 阴
    dong: bool
    gz: str                  # 本卦纳甲
    liuqin: str
    liushen: str
    shi_ying: str            # 世 / 应 / ""
    wang: str                # 旺相休囚死（对月建）
    kong: bool
    yuepo: bool
    ri_chong: bool
    bian_gz: str = ""
    bian_liuqin: str = ""
    bian_wx: str = ""
    ping: str = ""           # 断语

    @property
    def wx(self) -> str:
        return zhi_wx(self.gz)

    @property
    def yao(self) -> str:
        return "—" if self.yinyang else "- -"

    @property
    def dong_mark(self) -> str:
        if not self.dong:
            return ""
        return " ○→" if self.yinyang else " ×→"


@dataclass
class Cast:
    method: str
    when: datetime
    day_gz: str
    month_gz: str
    year_gz: str
    xunkong: str
    ben: Gua
    bian: Gua | None
    lines: list[Line]
    question: str
    yongshen: str
    verdict: str
    score: int
    notes: list[str] = field(default_factory=list)
    fushen: list[tuple[int, str, str]] = field(default_factory=list)  # (爻位, 六亲, 干支)


def build(method: str, lines: list[int], when: datetime,
          question: str = "财运", day_gz: str = "", month_gz: str = "",
          year_gz: str = "") -> Cast:
    """按六爻数值（6/7/8/9）装卦并作断。"""
    if len(lines) != 6:
        raise ValueError("六爻须为 6 个数值")
    if not day_gz or not month_gz or not year_gz:
        from lunar_python import Solar
        lu = Solar.fromYmdHms(when.year, when.month, when.day, when.hour, when.minute, 0).getLunar()
        day_gz = day_gz or lu.getDayInGanZhi()
        month_gz = month_gz or lu.getMonthInGanZhi()
        year_gz = year_gz or lu.getYearInGanZhi()
    ben_bits = tuple(1 if v in (7, 9) else 0 for v in lines)
    dong_idx = [i for i, v in enumerate(lines) if v in (6, 9)]
    bian_bits = tuple(b ^ 1 if i in dong_idx else b for i, b in enumerate(ben_bits))
    ben = GUAS[ben_bits]
    bian = GUAS[bian_bits] if dong_idx else None

    month_zhi = month_gz[-1]
    ling = ZHI_WX[month_zhi]
    day_zhi = day_gz[-1]
    ls = liushen_of_day(day_gz[0])
    kong = kong_wang(day_gz)
    shi, ying = ben.shi, ben.ying

    rows: list[Line] = []
    for i in range(6):
        gz = ben.na[i]
        bian_gz = bian.na[i] if bian and i in dong_idx else ""
        ln = Line(pos=i + 1, yinyang=ben_bits[i], dong=i in dong_idx, gz=gz,
                  liuqin=liuqin(ben.wx, zhi_wx(gz)), liushen=ls[i],
                  shi_ying="世" if i + 1 == shi else ("应" if i + 1 == ying else ""),
                  wang=wangshuai(zhi_wx(gz), ling),
                  kong=gz[-1] in kong,
                  yuepo=frozenset((gz[-1], month_zhi)) in LIUCHONG_PAIRS,
                  ri_chong=frozenset((gz[-1], day_zhi)) in LIUCHONG_PAIRS,
                  bian_gz=bian_gz,
                  bian_liuqin=liuqin(bian.wx, zhi_wx(bian_gz)) if bian_gz else "",
                  bian_wx=zhi_wx(bian_gz) if bian_gz else "")
        rows.append(ln)

    yong = YONGSHEN.get(question, "世爻")
    fushen = []
    if yong == "世爻":
        yong_line = rows[shi - 1]
        yong_desc = f"世爻（第 {shi} 爻 {yong_line.gz}）"
    else:
        hit = [r for r in rows if r.liuqin == yong]
        if not hit:
            # 用神不上卦，取本宫卦同位之爻为伏神（《卜筮正宗·伏神》）
            base = GUAS[TRI[ben.palace]["bits"] + TRI[ben.palace]["bits"]]
            for i in range(6):
                if liuqin(base.wx, zhi_wx(base.na[i])) == yong:
                    fushen.append((i + 1, yong, base.na[i]))
                    break
            yong_line = None
            yong_desc = f"{yong}（不上卦，伏于第 {fushen[0][0]} 爻 {fushen[0][2]}）" if fushen else yong
        else:
            yong_line = max(hit, key=lambda r: (r.dong, r.wang != "死"))
            yong_desc = f"{yong}（第 {yong_line.pos} 爻 {yong_line.gz}）"

    score, notes = _judge(rows, yong_line, yong, kong, month_zhi, day_zhi, ben, bian, shi)
    verdict = "吉" if score >= 3 else ("凶" if score <= -3 else "平")
    cast = Cast(method=method, when=when, day_gz=day_gz, month_gz=month_gz, year_gz=year_gz,
                xunkong=kong, ben=ben, bian=bian, lines=rows, question=question,
                yongshen=yong_desc, verdict=verdict, score=score, notes=notes, fushen=fushen)
    return cast


def _judge(rows: list[Line], yong: Line | None, yong_name: str, kong: str,
           month_zhi: str, day_zhi: str, ben: Gua, bian: Gua | None, shi: int) -> tuple[int, list[str]]:
    """简断：月建日辰、动爻生克、旬空月破、化进化退、六冲六合。"""
    notes: list[str] = []
    score = 0

    if yong is not None:
        if yong.wang in ("旺", "相"):
            score += 2
            notes.append(f"用神{yong.liuqin}临{yong.wang}地（月建{month_zhi}），本身有力。")
        elif yong.wang == "死":
            score -= 2
            notes.append(f"用神{yong.liuqin}处死地（月建{month_zhi}克之），力量不足。")
        if yong.ri_chong:
            if yong.wang in ("旺", "相"):
                notes.append("日辰冲用神而用神旺，为「暗动」，反主有力、事发突然。")
                score += 1
            else:
                score -= 2
                notes.append("日辰冲用神且用神衰弱，为「日破」，主事难成。")
        if frozenset((yong.gz[-1], day_zhi)) in LIUHE_PAIRS:
            notes.append(f"用神与日辰{day_zhi}相合，为「合起」，得日辰扶助。")
            score += 1
        if yong.kong:
            score -= 1
            notes.append(f"用神旬空（空亡 {kong}），主暂不落实，出空之月日方见分晓。")
        if yong.yuepo:
            score -= 2
            notes.append("用神逢月破，主损伤、破败，须待出破之期。")
        # 动爻对用神的作用
        for r in rows:
            if not r.dong or r is yong:
                continue
            if WX_SHENG[r.wx] == yong.wx:
                score += 1
                notes.append(f"第 {r.pos} 爻{r.liuqin}（{r.gz}）发动生用神，谓之「原神发动」，吉。")
            elif WX_KE[r.wx] == yong.wx:
                score -= 2
                notes.append(f"第 {r.pos} 爻{r.liuqin}（{r.gz}）发动克用神，谓之「忌神发动」，凶。")
        # 变爻回头生克
        if yong.dong and yong.bian_gz:
            if WX_SHENG[yong.bian_wx] == yong.wx:
                score += 1
                notes.append(f"用神化出{yong.bian_gz}回头生，愈动愈强。")
            elif WX_KE[yong.bian_wx] == yong.wx:
                score -= 2
                notes.append(f"用神化出{yong.bian_gz}回头克，动而受伤。")
    else:
        score -= 1
        notes.append("用神不上卦，须待伏神透出或用神值日，事多迟滞。")

    if bian is not None and bian.bits != ben.bits:
        notes.append(f"本卦{ben.name}之{bian.name}，事有变动；{_bian_hint(ben, bian)}")
    chong = _is_liuchong(ben)
    he = _is_liuhe(ben)
    if chong:
        notes.append("本卦为六冲卦，主散、主快，事宜速决不宜拖。")
    if he:
        notes.append("本卦为六合卦，主成、主和，事易成而多纠缠。")
    shi_line = rows[shi - 1]
    if shi_line.dong:
        notes.append(f"世爻（第 {shi} 爻）发动，主自己主动求变。")
    if not notes:
        notes.append("卦象平稳，无显著生克，宜守常待时。")
    return score, notes


def _is_liuchong(g: Gua) -> bool:
    pairs = [(g.na[0], g.na[3]), (g.na[1], g.na[4]), (g.na[2], g.na[5])]
    return all(frozenset((a[-1], b[-1])) in LIUCHONG_PAIRS for a, b in pairs)


def _is_liuhe(g: Gua) -> bool:
    pairs = [(g.na[0], g.na[3]), (g.na[1], g.na[4]), (g.na[2], g.na[5])]
    return all(frozenset((a[-1], b[-1])) in LIUHE_PAIRS for a, b in pairs)


def _bian_hint(ben: Gua, bian: Gua) -> str:
    if WX_SHENG[bian.wx] == ben.wx:
        return "变卦生本卦，得外助。"
    if WX_KE[bian.wx] == ben.wx:
        return "变卦克本卦，外象相迫。"
    if bian.wx == ben.wx:
        return "变卦与本卦同气，事体一贯。"
    return "变卦与本卦异气，前后境况有别。"


# --------------------------------------------------------------------------- #
# 输出
# --------------------------------------------------------------------------- #
def _pad(text: str, width: int) -> str:
    """按显示宽度补空格（中日韩字符占 2 列）。"""
    return pad(text, width)


YAO_TITLE = {1: "初", 2: "二", 3: "三", 4: "四", 5: "五", 6: "上"}


def yao_title(pos: int, yinyang: int) -> str:
    """爻题：初九、九二 … 九五、上六。"""
    num = "九" if yinyang else "六"
    if pos == 1:
        return "初" + num
    if pos == 6:
        return "上" + num
    return num + YAO_TITLE[pos]


def render(c: Cast) -> str:
    L = [f"【六爻 · 纳甲筮法】占问：{c.question}　　起卦：{c.method}",
         f"　　起卦时间：{c.when:%Y-%m-%d %H:%M}　　{c.year_gz}年 {c.month_gz}月 {c.day_gz}日"
         f"　　旬空：{c.xunkong}",
         f"　　本卦：{c.ben.name}（{c.ben.palace}宫{c.ben.kind}卦，世{c.ben.shi}应{c.ben.ying}）"
         + (f"　　变卦：{c.bian.name}（{c.bian.palace}宫{c.bian.kind}卦）"
            if c.bian else "　　变卦：无（六爻皆静）"), ""]
    if c.fushen:
        L.append("　　伏神：" + "、".join(f"{f} {gz} 伏于第{p}爻" for p, f, gz in c.fushen))
        L.append("")
    L.append("　　" + _pad("爻位", 5) + _pad("六神", 5) + _pad("伏神", 10)
             + _pad("六亲", 5) + _pad("纳甲", 7) + _pad("旺", 3) + _pad("状态", 9)
             + _pad("卦象", 12) + _pad("世应", 5) + "动变")
    fu = {p: f"{f} {gz}" for p, f, gz in c.fushen}
    for r in reversed(c.lines):
        flags = "/".join(f for f, cond in (("空", r.kong), ("月破", r.yuepo), ("日冲", r.ri_chong)) if cond)
        mark = f"动→ {r.bian_gz}{r.bian_wx} {r.bian_liuqin}" if (r.dong and r.bian_gz) else ""
        L.append("　　" + _pad(yao_title(r.pos, r.yinyang), 5)
                 + _pad(r.liushen, 5) + _pad(fu.get(r.pos, "－"), 10)
                 + _pad(r.liuqin, 5) + _pad(r.gz + r.wx, 7) + _pad(r.wang, 3)
                 + _pad(flags or "－", 9)
                 + _pad("▅▅▅▅▅" if r.yinyang else "▅▅　▅▅", 12)
                 + _pad(r.shi_ying or "－", 5) + mark)
    L += ["", f"　【用神】{c.yongshen}", f"　【断】{c.verdict}（评分 {c.score:+d}）"]
    for n in c.notes:
        L.append(f"　　· {n}")
    L += ["", "　※ 六爻以用神为断事之枢：用神旺相、不受冲克、动而化吉则事成。"
              "本程序依《增删卜易》体例作规则化简断，未及神煞、飞神之细，结论仅供参考。"]
    return "\n".join(L)
