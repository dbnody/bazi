# -*- coding: utf-8 -*-
"""紫微斗数排盘.

安星体例依《紫微斗数全书》(明·陈希夷传/罗洪先序本) 及近代中州派通行法，
实现时与开源排盘器 iztro（SylarLong）逐条对照，以保一致。要点：

  · 命宫：寅起正月顺数至生月，再自该宫起子时逆数至生时；身宫同法而顺数至生时。
  · 命宫天干：五虎遁（甲己丙寅、乙庚戊寅、丙辛庚寅、丁壬壬寅、戊癸甲寅）。
  · 五行局：以命宫干支纳音定，水二局、木三局、金四局、土五局、火六局。
  · 紫微：以局数除生日，「六五四三二，酉午亥辰丑」，商数自寅宫顺行，
    补数奇则逆回、偶则顺行；天府与紫微相对（关于寅申轴）。
  · 紫微系逆行：紫微、天机（-1）、太阳（-3）、武曲（-4）、天同（-5）、廉贞（-8）。
  · 天府系顺行：天府、太阴（+1）、贪狼（+2）、巨门（+3）、天相（+4）、
    天梁（+5）、七杀（+6）、破军（+10）。
  · 生年四化依年干：禄、权、科、忌。
  · 大限：起于命宫，阳男阴女顺行、阴男阳女逆行，每宫十年，起运岁数即局数。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from . import constants as C
from .textutil import pad

GAN, ZHI = C.GAN, C.ZHI
JIAZI = [GAN[i % 10] + ZHI[i % 12] for i in range(60)]
ZHI_INDEX = {z: i for i, z in enumerate(ZHI)}

# 十二宫（自命宫起，随地支顺行）：命、父母、福德、田宅、官禄、交友、迁移、疾厄、财帛、子女、夫妻、兄弟
PALACE_NAMES = ["命宫", "父母", "福德", "田宅", "官禄", "交友",
                "迁移", "疾厄", "财帛", "子女", "夫妻", "兄弟"]
PALACE_MEANING = {
    "命宫": "本命格局、性格气质", "父母": "父母长辈、出身文书", "福德": "福泽精神、享受心性",
    "田宅": "不动产、家庭环境", "官禄": "事业功名、职位", "交友": "朋友部属、合作",
    "迁移": "外出际遇、社会活动", "疾厄": "健康体质、意外", "财帛": "财源理财、收入",
    "子女": "子女缘、才艺", "夫妻": "婚姻配偶、感情", "兄弟": "兄弟姐妹、同辈",
}

BUREAU = {"水": ("水二局", 2), "木": ("木三局", 3), "金": ("金四局", 4),
          "土": ("土五局", 5), "火": ("火六局", 6)}

YANG_ZHI = set("子寅辰午申戌")
SEX = {"男": "阳", "女": "阴"}

# 生年四化：年干 → (禄, 权, 科, 忌)
SIHUA = {
    "甲": ("廉贞", "破军", "武曲", "太阳"), "乙": ("天机", "天梁", "紫微", "太阴"),
    "丙": ("天同", "天机", "文昌", "廉贞"), "丁": ("太阴", "天同", "天机", "巨门"),
    "戊": ("贪狼", "太阴", "右弼", "天机"), "己": ("武曲", "贪狼", "天梁", "文曲"),
    "庚": ("太阳", "武曲", "太阴", "天同"), "辛": ("巨门", "太阳", "文曲", "文昌"),
    "壬": ("天梁", "紫微", "左辅", "武曲"), "癸": ("破军", "巨门", "太阴", "贪狼"),
}

MING_ZHU = dict(zip(ZHI, ["贪狼", "巨门", "禄存", "文曲", "廉贞", "武曲",
                          "破军", "武曲", "廉贞", "文曲", "禄存", "巨门"]))
SHEN_ZHU = dict(zip(ZHI, ["火星", "天相", "天梁", "天同", "文昌", "天机",
                          "火星", "天相", "天梁", "天同", "文昌", "天机"]))

STAR_MEANING = {
    "紫微": "帝座，主尊贵、领导", "天机": "谋略、机变、智慧", "太阳": "博爱、声名、男性长辈",
    "武曲": "财帛、刚毅、行动", "天同": "福气、享受、温和", "廉贞": "才情、是非、交际",
    "天府": "库储、稳重、保守", "太阴": "阴柔、内敛、不动产", "贪狼": "欲望、才艺、桃花",
    "巨门": "口舌、暗昧、专业", "天相": "辅佐、公正、外貌", "天梁": "荫庇、老成、医药",
    "七杀": "肃杀、开创、独断", "破军": "破旧立新、变动、损耗",
}


# --------------------------------------------------------------------------- #
# 基础工具
# --------------------------------------------------------------------------- #
def nayin_wuxing(gz: str) -> str:
    return C.NAYIN[JIAZI.index(gz) // 2][-1]


def wuhu_dun(year_gan: str) -> int:
    """五虎遁：年干推寅宫天干序号。"""
    return ({"甲": 2, "己": 2, "乙": 4, "庚": 4, "丙": 6, "辛": 6,
             "丁": 8, "壬": 8, "戊": 0, "癸": 0})[year_gan]


def xun_kong(gz: str) -> str:
    g, z = GAN.index(gz[0]), ZHI.index(gz[1])
    start = (z - g) % 12
    return ZHI[(start + 10) % 12] + ZHI[(start + 11) % 12]


def ziwei_index(day: int, bureau: int) -> int:
    """紫微星所在（子起 0）。日数须为农历日，局数 2~6。

    补数使日数能被局数整除，商数自寅宫顺行（寅为第一格）；
    补数奇则逆回补数宫，偶则顺行补数宫。
    """
    offset = (-day) % bureau
    quotient = (day + offset) // bureau
    base = 2 + (quotient - 1)                     # 寅宫为第一格
    if offset == 0:
        idx = base
    elif offset % 2:
        idx = base - offset
    else:
        idx = base + offset
    return idx % 12


# --------------------------------------------------------------------------- #
# 排盘
# --------------------------------------------------------------------------- #
@dataclass
class Palace:
    zhi: str
    gan: str
    name: str
    is_soul: bool = False
    is_body: bool = False
    major: list[str] = field(default_factory=list)
    minor: list[str] = field(default_factory=list)
    decade: tuple[int, int] | None = None
    liu_ji: list[str] = field(default_factory=list)   # 生年四化标注

    @property
    def gz(self) -> str:
        return self.gan + self.zhi


@dataclass
class ZiweiChart:
    when: datetime
    gender: str
    lunar_text: str
    year_gz: str
    month: int
    day: int
    leap: bool
    time_zhi: str
    soul_idx: int
    body_idx: int
    bureau_name: str
    bureau_num: int
    ziwei_idx: int
    tianfu_idx: int
    palaces: list[Palace]
    notes: list[str] = field(default_factory=list)

    @property
    def soul_palace(self) -> Palace:
        return self.palaces[self.soul_idx]

    @property
    def body_palace(self) -> Palace:
        return self.palaces[self.body_idx]

    @property
    def ming_zhu(self) -> str:
        return MING_ZHU[ZHI[self.soul_idx]]

    @property
    def shen_zhu(self) -> str:
        return SHEN_ZHU[self.year_gz[1]]

    @property
    def forward(self) -> bool:
        """大限顺行与否：阳男阴女顺行。"""
        year_yang = self.year_gz[1] in YANG_ZHI
        return year_yang == (SEX[self.gender] == "阳")


def build(dt: datetime, gender: str = "男", fix_leap: bool = True) -> ZiweiChart:
    from datetime import timedelta

    from lunar_python import Solar
    # 晚子时（23:00 后）作次日子时论，与紫微斗数通行的「日界在子初」一致
    d = dt + timedelta(days=1) if dt.hour >= 23 else dt
    lu = Solar.fromYmdHms(d.year, d.month, d.day, d.hour, d.minute, 0).getLunar()
    year_gz = lu.getYearInGanZhi()
    month, day, leap = abs(lu.getMonth()), lu.getDay(), lu.getMonth() < 0
    time_idx = ((dt.hour + 1) // 2) % 12
    if leap and fix_leap:
        month = month + 1 if day > 15 else month        # 闰月下半月作次月
    if month > 12:
        month = 1
    # 晚子时（23:00 后）按次日子时论，与节气历法一致
    start = 2 + (month - 1)                             # 寅起正月
    soul_idx = (start - time_idx) % 12
    body_idx = (start + time_idx) % 12

    tiger = wuhu_dun(year_gz[0])
    # 五虎遁起寅宫天干，十二宫顺行；天干十位一轮，故子宫与寅宫隔十位而同干
    gan_of = {z: GAN[(tiger + (i - 2) % 12) % 10] for i, z in enumerate(ZHI)}
    soul_gz = gan_of[ZHI[soul_idx]] + ZHI[soul_idx]
    wuxing = nayin_wuxing(soul_gz)
    bname, bnum = BUREAU[wuxing]

    zw = ziwei_index(day, bnum)
    tf = (4 - zw) % 12

    palaces = [Palace(ZHI[i], gan_of[ZHI[i]], PALACE_NAMES[(i - soul_idx) % 12],
                      is_soul=(i == soul_idx), is_body=(i == body_idx)) for i in range(12)]

    # 十四主星
    for star, delta in (("紫微", 0), ("天机", -1), ("太阳", -3), ("武曲", -4),
                        ("天同", -5), ("廉贞", -8)):
        palaces[(zw + delta) % 12].major.append(star)
    for star, delta in (("天府", 0), ("太阴", 1), ("贪狼", 2), ("巨门", 3),
                        ("天相", 4), ("天梁", 5), ("七杀", 6), ("破军", 10)):
        palaces[(tf + delta) % 12].major.append(star)

    # 年干系
    lucun = ZHI.index({"甲": "寅", "乙": "卯", "丙": "巳", "丁": "午", "戊": "巳",
                       "己": "午", "庚": "申", "辛": "酉", "壬": "亥", "癸": "子"}[year_gz[0]])
    kui_yue = {"甲": ("丑", "未"), "戊": ("丑", "未"), "庚": ("丑", "未"),
               "乙": ("子", "申"), "己": ("子", "申"), "辛": ("午", "寅"),
               "壬": ("卯", "巳"), "癸": ("卯", "巳"), "丙": ("亥", "酉"), "丁": ("亥", "酉")}[year_gz[0]]
    jie_kong = {"甲": "申酉", "己": "申酉", "乙": "午未", "庚": "午未", "丙": "辰巳",
                "辛": "辰巳", "丁": "寅卯", "壬": "寅卯", "戊": "子丑", "癸": "子丑"}[year_gz[0]]
    nk = xun_kong(year_gz)
    # 年支系
    yz = ZHI.index(year_gz[1])
    group3 = {"寅": 0, "午": 0, "戌": 0, "申": 1, "子": 1, "辰": 1,
              "巳": 2, "酉": 2, "丑": 2, "亥": 3, "卯": 3, "未": 3}[year_gz[1]]
    huo_ling = (("丑", "卯"), ("寅", "戌"), ("卯", "戌"), ("酉", "戌"))[group3]
    tianma = ("申", "寅", "亥", "巳")[group3]
    huagai = ("戌", "辰", "丑", "未")[group3]
    xianchi = ("卯", "酉", "午", "子")[group3]
    # 孤辰寡宿以三会方局定：亥子丑→孤寅寡戌，寅卯辰→孤巳寡丑，巳午未→孤申寡辰，申酉戌→孤亥寡未
    fang = {"亥": 11, "子": 11, "丑": 11, "寅": 2, "卯": 2, "辰": 2,
            "巳": 5, "午": 5, "未": 5, "申": 8, "酉": 8, "戌": 8}[year_gz[1]]
    gu_chen, gua_su = ZHI[(fang + 3) % 12], ZHI[(fang - 1) % 12]
    hongluan = (ZHI.index("卯") - yz) % 12
    tianku = (ZHI.index("午") - yz) % 12
    tianxu = (ZHI.index("午") + yz) % 12
    po_sui = {"子": "巳", "午": "巳", "卯": "巳", "酉": "巳", "寅": "酉", "申": "酉",
              "巳": "酉", "亥": "酉", "辰": "丑", "戌": "丑", "未": "丑", "丑": "丑"}[year_gz[1]]
    # 月系
    zuo = (ZHI.index("辰") + month - 1) % 12
    you = (ZHI.index("戌") - month + 1) % 12
    tianxing = (ZHI.index("酉") + month - 1) % 12
    tianyao = (ZHI.index("丑") + month - 1) % 12
    # 时系
    wenchang = (ZHI.index("戌") - time_idx) % 12
    wenqu = (ZHI.index("辰") + time_idx) % 12
    dikong = (ZHI.index("亥") - time_idx) % 12
    dijie = (ZHI.index("亥") + time_idx) % 12
    taifu = (ZHI.index("午") + time_idx) % 12
    fenggao = (ZHI.index("寅") + time_idx) % 12
    # 日系（三台八座恩光天贵）
    d = day - 1
    santai = (zuo + d) % 12
    bazuo = (you - d) % 12
    enguang = (wenchang + d - 1) % 12
    tiangui = (wenqu + d - 1) % 12

    add = [("左辅", zuo), ("右弼", you), ("文昌", wenchang), ("文曲", wenqu),
           ("天魁", ZHI_INDEX[kui_yue[0]]), ("天钺", ZHI_INDEX[kui_yue[1]]),
           ("禄存", lucun), ("擎羊", (lucun + 1) % 12), ("陀罗", (lucun - 1) % 12),
           ("火星", (ZHI.index(huo_ling[0]) + time_idx) % 12),
           ("铃星", (ZHI.index(huo_ling[1]) + time_idx) % 12),
           ("地空", dikong), ("地劫", dijie), ("天马", ZHI_INDEX[tianma]),
           ("三台", santai), ("八座", bazuo), ("恩光", enguang), ("天贵", tiangui),
           ("台辅", taifu), ("封诰", fenggao), ("天刑", tianxing), ("天姚", tianyao),
           ("红鸾", hongluan), ("天喜", (hongluan + 6) % 12),
           ("天哭", tianku), ("天虚", tianxu), ("华盖", ZHI_INDEX[huagai]),
           ("咸池", ZHI_INDEX[xianchi]), ("孤辰", ZHI_INDEX[gu_chen]),
           ("寡宿", ZHI_INDEX[gua_su]), ("破碎", ZHI_INDEX[po_sui]),
           ("截路", ZHI.index(jie_kong[0])), ("空亡", ZHI.index(jie_kong[1]))]
    for name, idx in add:
        palaces[idx].minor.append(name)
    for z in nk:
        palaces[ZHI.index(z)].liu_ji.append("旬空")

    # 生年四化
    hua = dict(zip(("化禄", "化权", "化科", "化忌"), SIHUA[year_gz[0]]))
    for star, kind in hua.items():
        for p in palaces:
            if star in p.major or star in p.minor:
                p.liu_ji.append(f"{star}{kind}")
    # 大限
    forward = (year_gz[1] in YANG_ZHI) == (SEX[gender] == "阳")
    for k in range(12):
        idx = (soul_idx + (k if forward else -k)) % 12
        start_age = bnum + 10 * k
        palaces[idx].decade = (start_age, start_age + 9)

    lu_text = f"{lu.getYearInChinese()}年{lu.getMonthInChinese()}月{lu.getDayInChinese()}"
    return ZiweiChart(when=dt, gender=gender, lunar_text=lu_text, year_gz=year_gz,
                      month=month, day=day, leap=leap, time_zhi=ZHI[time_idx],
                      soul_idx=soul_idx, body_idx=body_idx, bureau_name=bname,
                      bureau_num=bnum, ziwei_idx=zw, tianfu_idx=tf, palaces=palaces)


# --------------------------------------------------------------------------- #
# 输出
# --------------------------------------------------------------------------- #
def _stars(p: Palace) -> str:
    s = " ".join(p.major)
    if p.minor:
        s += ("　" if s else "") + " ".join(p.minor)
    return s or "（空宫）"


def render(ch: ZiweiChart, hour_label: str = "") -> str:
    soul = ch.soul_palace
    L = [f"【紫微斗数】{ch.gender}命　{hour_label or f'{ch.when:%Y-%m-%d %H:%M}'}",
         f"　　农历：{ch.lunar_text}（{ch.time_zhi}时）　　年干支：{ch.year_gz}"
         f"　　命宫：{soul.zhi}宫（{soul.gz}）　　身宫：{ch.body_palace.zhi}宫",
         f"　　五行局：{ch.bureau_name}　　命主：{ch.ming_zhu}　　身主：{ch.shen_zhu}"
         f"　　起运：{ch.bureau_num} 岁（{ch.gender}·{'顺行' if ch.forward else '逆行'}）",
         ""]
    L.append("　　" + pad("宫位", 7) + pad("宫名", 11) + pad("主星", 22)
             + pad("辅星杂曜", 40) + pad("四化", 10) + "大限")
    for k in range(12):
        p = ch.palaces[(ch.soul_idx + (k if ch.forward else -k)) % 12]
        tag = "（身）" if (p.is_body and not p.is_soul) else ""
        dec = f"{p.decade[0]}-{p.decade[1]}" if p.decade else ""
        L.append("　　" + pad(p.zhi + "宫", 7) + pad(p.name + tag, 11)
                 + pad(" ".join(p.major) or "－", 22)
                 + pad(" ".join(p.minor), 40)
                 + pad(" ".join(p.liu_ji), 10) + dec)
    L.append("")
    san = [ch.palaces[(ch.soul_idx + o) % 12] for o in (0, 4, 8, 6)]
    L.append("　【命宫三方四正】" + "　".join(
        f"{p.name}{p.zhi}：{' '.join(p.major) or '空宫'}" for p in san))
    L.append(f"　【生年四化】{ch.year_gz[0]}干："
             + "、".join(f"{s}{k}" for k, s in zip(("化禄", "化权", "化科", "化忌"), SIHUA[ch.year_gz[0]])))
    ming = soul.major or ch.palaces[(ch.soul_idx + 6) % 12].major
    if soul.major:
        L.append("　【命宫主星】" + "、".join(f"{s}（{STAR_MEANING[s]}）" for s in soul.major))
    else:
        L.append("　【命宫主星】命宫无主星，借对宫迁移："
                 + "、".join(f"{s}（{STAR_MEANING[s]}）" for s in ming))
    for star, meaning in STAR_MEANING.items():
        p = next((q for q in ch.palaces if star in q.major), None)
        if p is not None:
            L.append(f"　　· {star}在{p.name}（{p.zhi}宫）：{meaning}")
    L += ["", "　※ 紫微斗数以命宫、三方四正、四化为纲，须参大限流年方见应期。"
              "本程序依《紫微斗数全书》体例安星，未及星曜庙旺利陷与流年盘，结论仅供参考。"]
    return "\n".join(L)
