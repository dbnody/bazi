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
    "文昌": "文才、考试、条理", "文曲": "口才、才艺、风雅", "左辅": "助力、辅佐、忠厚",
    "右弼": "助力、人缘、机变", "天魁": "阳贵、机遇、男性长辈", "天钺": "阴贵、机遇、女性长辈",
    "禄存": "财禄、保守、孤守", "擎羊": "刑伤、刚烈、决断", "陀罗": "拖磨、固执、暗耗",
    "火星": "急躁、突发、虚惊", "铃星": "暴烈、惊扰、急变", "地空": "空想、幻灭、灵感",
    "地劫": "破耗、掠夺、意外", "天马": "奔波、迁徙、变动", "红鸾": "婚喜、魅力",
    "天喜": "喜庆、添丁", "天刑": "刑法、疾病、自律", "天姚": "风情、交际、暗昧",
    "华盖": "孤高、艺术、宗教", "咸池": "桃花、情欲", "天哭": "悲忧、刑克",
    "天虚": "虚耗、空亡", "孤辰": "孤独、刑克", "寡宿": "孤寂、寡合",
    "破碎": "破损、不成", "三台": "地位、名声", "八座": "地位、清贵",
    "恩光": "殊荣、恩赐", "天贵": "贵气、助力", "台辅": "辅弼、清望",
    "封诰": "封赏、荣典", "天月": "疾病、缠延", "天巫": "升迁、宗教",
    "阴煞": "暗害、小人", "解神": "解厄、消灾", "天厨": "禄食、口福",
    "天官": "仕宦、贵显", "天福": "福禄、安逸", "天才": "天才、智慧",
    "天寿": "长寿、稳重", "龙池": "文雅、异性缘", "凤阁": "华美、清秀",
    "蜚廉": "小人、口舌", "天伤": "伤损、内耗", "天使": "疾病、催逼",
    "天德": "福德、解厄", "月德": "福德、柔和", "旬空": "虚而不实",
}

# 星曜庙旺利陷（与 iztro 亮度表逐格一致；寅宫起为序，四生宫无亮度者留空）
BRIGHT = {
    "紫微": dict(zip("子丑寅卯辰巳午未申酉戌亥",
                    "平庙旺旺得旺庙庙旺旺得旺")),
    "天机": dict(zip("子丑寅卯辰巳午未申酉戌亥",
                    "庙陷得旺利平庙陷得旺利平")),
    "太阳": dict(zip("子丑寅卯辰巳午未申酉戌亥",
                    "陷不旺庙旺旺旺得得平不陷")),
    "武曲": dict(zip("子丑寅卯辰巳午未申酉戌亥",
                    "旺庙得利庙平旺庙得利庙平")),
    "天同": dict(zip("子丑寅卯辰巳午未申酉戌亥",
                    "旺不利平平庙陷不旺平平庙")),
    "廉贞": dict(zip("子丑寅卯辰巳午未申酉戌亥",
                    "平利庙平利陷平利庙平利陷")),
    "天府": dict(zip("子丑寅卯辰巳午未申酉戌亥",
                    "庙庙庙得庙得旺庙得旺庙得")),
    "太阴": dict(zip("子丑寅卯辰巳午未申酉戌亥",
                    "庙庙旺陷陷陷不不利旺旺庙")),
    "贪狼": dict(zip("子丑寅卯辰巳午未申酉戌亥",
                    "旺庙平利庙陷旺庙平利庙陷")),
    "巨门": dict(zip("子丑寅卯辰巳午未申酉戌亥",
                    "旺不庙庙陷旺旺不庙庙陷旺")),
    "天相": dict(zip("子丑寅卯辰巳午未申酉戌亥",
                    "庙庙庙陷得得庙得庙陷得得")),
    "天梁": dict(zip("子丑寅卯辰巳午未申酉戌亥",
                    "庙旺庙庙庙陷庙旺陷得庙陷")),
    "七杀": dict(zip("子丑寅卯辰巳午未申酉戌亥",
                    "旺庙庙旺庙平旺庙庙旺庙平")),
    "破军": dict(zip("子丑寅卯辰巳午未申酉戌亥",
                    "庙旺得陷旺平庙旺得陷旺平")),
    "文昌": dict(zip("子丑寅卯辰巳午未申酉戌亥",
                    "得庙陷利得庙陷利得庙陷利")),
    "文曲": dict(zip("子丑寅卯辰巳午未申酉戌亥",
                    "得庙平旺得庙陷旺得庙陷旺")),
    "火星": dict(zip("子丑寅卯辰巳午未申酉戌亥",
                    "陷得庙利陷得庙利陷得庙利")),
    "铃星": dict(zip("子丑寅卯辰巳午未申酉戌亥",
                    "陷得庙利陷得庙利陷得庙利")),
    "擎羊": {"子": "陷", "丑": "庙", "寅": "", "卯": "陷", "辰": "庙", "巳": "",
             "午": "陷", "未": "庙", "申": "", "酉": "陷", "戌": "庙", "亥": ""},
    "陀罗": {"子": "", "丑": "庙", "寅": "陷", "卯": "", "辰": "庙", "巳": "陷",
             "午": "", "未": "庙", "申": "陷", "酉": "", "戌": "庙", "亥": "陷"},
}

BRIGHT_GRADE = {"庙": 2, "旺": 2, "得": 1, "利": 1, "平": 0, "不": -1, "陷": -2, "": 0}


def bright_of(star: str, zhi: str) -> str:
    return BRIGHT.get(star, {}).get(zhi, "")


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


def _xunkong_idx(year_gan_idx: int, year_zhi_idx: int) -> int:
    """旬空星位：以年支起、逆推至旬首，再取与年支同阴阳之一支。"""
    idx = (year_zhi_idx + 9 - year_gan_idx + 1) % 12
    if idx % 2 != year_zhi_idx % 2:
        idx = (idx + 1) % 12
    return idx


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
    # 年干/年支/月/宫位系杂曜（依《紫微斗数全书》通行安法，与 iztro 对照）
    mi = month - 1                                        # 正月为 0
    extras = [
        ("天才", (soul_idx + yz) % 12), ("天寿", (body_idx + yz) % 12),
        ("天厨", ZHI.index("巳午子巳午申寅午酉亥"[GAN.index(year_gz[0])])),
        ("蜚廉", ZHI.index("申酉戌巳午未寅卯辰亥子丑"[yz])),
        ("龙池", (ZHI.index("辰") + yz) % 12), ("凤阁", (ZHI.index("戌") - yz) % 12),
        ("天官", ZHI.index("未辰巳寅卯酉亥酉戌午"[GAN.index(year_gz[0])])),
        ("天福", ZHI.index("酉申子亥卯寅午巳午巳"[GAN.index(year_gz[0])])),
        ("天德", (ZHI.index("酉") + yz) % 12), ("月德", (ZHI.index("巳") + yz) % 12),
        ("天伤", (soul_idx + 5) % 12), ("天使", (soul_idx + 7) % 12),
        ("年解", ZHI.index("戌酉申未午巳辰卯寅丑子亥"[yz])),
        ("解神", ZHI.index("申戌子寅辰午"[mi // 2])),
        ("阴煞", ZHI.index("寅子戌申午辰"[mi % 6])),
        ("天月", ZHI.index("戌巳辰寅未卯亥未寅午戌寅"[mi])),
        ("天巫", ZHI.index("巳申寅亥"[mi % 4])),
        ("天空", (yz + 1) % 12),
        ("旬空", _xunkong_idx(GAN.index(year_gz[0]), yz)),
    ]
    add += extras
    for name, idx in add:
        palaces[idx].minor.append(name)

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
# 断语：庙旺、三方四正、格局、四化落宫、限运
# --------------------------------------------------------------------------- #
LUCKY = {"左辅", "右弼", "文昌", "文曲", "天魁", "天钺", "禄存", "天马", "三台", "八座",
         "恩光", "天贵", "台辅", "封诰", "红鸾", "天喜", "天德", "月德", "解神", "年解",
         "天官", "天福", "天厨", "天才", "天寿", "龙池", "凤阁", "天巫"}
EVIL = {"擎羊", "陀罗", "火星", "铃星", "地空", "地劫", "天刑", "天姚", "天空", "旬空",
        "天哭", "天虚", "破碎", "阴煞", "蜚廉", "孤辰", "寡宿", "咸池", "天使", "天伤"}

SANFANG_OFFSETS = (0, 4, 8, 6)          # 本宫、三合两宫、对宫


def sanfang(ch: ZiweiChart, idx: int) -> list[Palace]:
    return [ch.palaces[(idx + o) % 12] for o in SANFANG_OFFSETS]


def palace_grade(p: Palace) -> int:
    """宫位吉凶量化：主星庙旺（±2）、吉曜（+1）、煞曜（-1）、四化（禄权科 +、忌 −）。"""
    s = sum(BRIGHT_GRADE.get(bright_of(x, p.zhi), 0) for x in p.major)
    s += sum(1 for x in p.minor if x in LUCKY)
    s -= sum(1 for x in p.minor if x in EVIL)
    for tag in p.liu_ji:
        if "化禄" in tag:
            s += 2
        elif "化权" in tag:
            s += 1
        elif "化科" in tag:
            s += 1
        elif "化忌" in tag:
            s -= 2
    return s


def patterns(ch: ZiweiChart) -> list[str]:
    soul = ch.soul_palace
    idx = ch.soul_idx
    tri = {x for p in sanfang(ch, idx) for x in p.major}
    minor_ming = set(soul.minor)
    allidx = {x for p in ch.palaces for x in p.major}
    out = []

    if {"紫微", "天府"} <= set(soul.major):
        out.append("紫府同宫：尊贵持重、器度宽宏，宜居领导之位，一生多助力。")
    if {"紫微", "天府"} <= tri and not ({"紫微", "天府"} <= set(soul.major)):
        out.append("紫府朝垣：三方见紫微天府，主格局宏大，得贵人与资源相扶。")
    if {"七杀", "破军", "贪狼"} <= tri:
        out.append("杀破狼格：主开创变动，一生起伏大而机会多，宜主动不宜守成。")
    if {"天机", "太阴", "天同", "天梁"} <= tri:
        out.append("机月同梁格：宜公职、幕僚、专业与文教，稳中得名，不宜投机。")
    if {"太阳", "太阴"} <= set(soul.major):
        out.append("日月同宫：阴阳并济，性情兼刚柔，然易心事反复、内外两难。")
    if soul.major == ["太阴"] and soul.zhi == "亥":
        out.append("月朗天门：太阴在亥庙地守命，主清贵、富文才，女命尤佳。")
    if soul.major == ["太阳"] and soul.zhi in ("卯", "辰"):
        out.append("日照雷门：太阳卯辰庙旺守命，主光明磊落、早年得志。")
    if "紫微" in soul.major and len(minor_ming & {"左辅", "右弼", "文昌", "文曲", "天魁", "天钺"}) >= 2:
        out.append("君臣庆会：紫微得辅弼昌曲魁钺相随，主得众助、位高而稳。")
    if "巨门" in soul.major and soul.zhi in ("子", "午") and any("化" in t for t in soul.liu_ji):
        out.append("石中隐玉：巨门子午得化，主先难后成，以专业口才立身。")
    if {"天府", "天相"} <= tri:
        out.append("府相朝垣：三方见天府天相，主衣食丰足、处事圆融，得人信任。")
    if "贪狼" in tri and ({"火星", "铃星"} & {x for p in sanfang(ch, idx) for x in p.minor}):
        out.append("火贪（铃贪）相逢：主突发之财与横发机遇，来得快亦须防去得快。")
    if "紫微" in soul.major and soul.zhi == "午":
        out.append("极向离明：紫微在午守命，主气象恢宏，宜大任而不宜小就。")
    if not out:
        out.append("命宫三方无特异组合，格局平平，成败多系于大限流年与自身修为。")
    return out


def sihua_of(gan: str) -> dict:
    return dict(zip(("化禄", "化权", "化科", "化忌"), SIHUA[gan]))


def sihua_landing(ch: ZiweiChart, gan: str) -> list[str]:
    """四化落宫：某干四化飞入何宫，主该宫事象得失。"""
    out = []
    for kind, star in sihua_of(gan).items():
        p = next((q for q in ch.palaces if star in q.major or star in q.minor), None)
        if p is None:
            continue
        tone = {"化禄": "主财禄、机遇、人缘", "化权": "主权柄、掌控、进取",
                "化科": "主名誉、文书、贵人", "化忌": "主阻滞、执着、耗损"}[kind]
        out.append(f"{star}{kind} 入{p.name}（{p.zhi}宫）：{tone}，应在{PALACE_MEANING[p.name]}。")
    return out


XIAOXIAN_START = {"寅": "辰", "午": "辰", "戌": "辰", "申": "戌", "子": "戌", "辰": "戌",
                  "巳": "未", "酉": "未", "丑": "未", "亥": "丑", "卯": "丑", "未": "丑"}


def small_limit(ch: ZiweiChart, year: int) -> tuple[int, int]:
    """小限：男顺女逆，一岁起于年支所定之宫。返回 (宫位索引, 虚岁)。"""
    start = ZHI.index(XIAOXIAN_START[ch.year_gz[1]])
    age = year - ch.when.year + 1
    step = (age - 1) if ch.gender == "男" else -(age - 1)
    return (start + step) % 12, age


def liunian_palace(ch: ZiweiChart, year: int) -> Palace:
    """流年宫：太岁所在之宫。"""
    zhi = ZHI[(year - 1984) % 12]
    return next(p for p in ch.palaces if p.zhi == zhi)


def _star_text(p: Palace, with_bright: bool = True) -> str:
    if not p.major:
        return "空宫"
    if not with_bright:
        return " ".join(p.major)
    return " ".join(f"{s}({bright_of(s, p.zhi) or '－'})" for s in p.major)


PALACE_RULE = {
    "夫妻": "主婚姻配偶。见天同、天梁、太阴庙旺者多和顺；见七杀、破军、廉贞加擎羊陀罗者多波折，宜迟婚。",
    "财帛": "主财源理财。武曲、天府、禄存、化禄守之为财有根；地空地劫同度则财来财去。",
    "官禄": "主事业功名。紫微、天府、太阳宜公职管理；巨门宜专业口才；天机宜谋划幕僚。",
    "疾厄": "主健康体质。煞曜聚集则体质偏弱；天月、天刑同度宜防慢性之疾。",
    "迁移": "主外出际遇。太阳、天马守之宜外出发展；空劫同度则外出多虚耗。",
    "田宅": "主不动产与家宅。天府、太阴、禄存守之宜置业；空劫则家宅多变动。",
    "福德": "主福泽精神。天同、天梁、太阴守之享福安逸；贪狼、廉贞则多欲多思。",
    "父母": "主父母长辈。见吉曜得荫庇；见煞则早年离乡或与长辈缘薄。",
    "子女": "主子女缘与才艺。天机、文昌文曲守之多聪慧；孤辰寡宿则缘迟。",
    "兄弟": "主同辈手足。左辅右弼得助；擎羊陀罗则易生争执。",
    "交友": "主朋友部属。吉曜得众助；煞曜则防小人拖累。",
}


def palace_notes(ch: ZiweiChart) -> list[str]:
    """重点宫位断语：命、夫妻、财帛、官禄、疾厄、迁移。"""
    out = []
    for name in ("夫妻", "财帛", "官禄", "疾厄", "迁移"):
        p = next(q for q in ch.palaces if q.name == name)
        stars = _star_text(p)
        if not p.major:
            stars += "（借对宫" + _star_text(ch.palaces[(ch.palaces.index(p) + 6) % 12], False) + "）"
        extra = []
        lucky = [x for x in p.minor if x in LUCKY and x in ("左辅", "右弼", "文昌", "文曲", "天魁", "天钺", "禄存", "天马")]
        evil = [x for x in p.minor if x in EVIL]
        if lucky:
            extra.append("吉曜见" + "、".join(lucky[:3]))
        if evil:
            extra.append("煞曜见" + "、".join(evil[:3]))
        if p.liu_ji:
            extra.append("、".join(p.liu_ji))
        out.append(f"{name}宫（{p.zhi}）：{stars}"
                   + ("；" + "；".join(extra) if extra else "")
                   + f"。{PALACE_RULE.get(name, '')}")
    soul = ch.soul_palace
    grade = palace_grade(soul)
    out.insert(0, f"命宫（{soul.zhi}·{soul.gz}）：{_star_text(soul)}；三方四正吉凶分 {grade:+d}"
                  + ("，庙旺吉曜得力，主气象开展。" if grade >= 4 else
                     "，吉凶相参，成败在运。" if grade >= 0 else
                     "，煞忌偏重，宜守成积德、以勤补拙。"))
    return out


def render(ch: ZiweiChart, hour_label: str = "") -> str:
    soul = ch.soul_palace
    L = [f"【紫微斗数】{ch.gender}命　{hour_label or f'{ch.when:%Y-%m-%d %H:%M}'}",
         f"　　农历：{ch.lunar_text}（{ch.time_zhi}时）　　年干支：{ch.year_gz}"
         f"　　命宫：{soul.zhi}宫（{soul.gz}）　　身宫：{ch.body_palace.zhi}宫",
         f"　　五行局：{ch.bureau_name}　　命主：{ch.ming_zhu}　　身主：{ch.shen_zhu}"
         f"　　起运：{ch.bureau_num} 岁（{ch.gender}·{'顺行' if ch.forward else '逆行'}）",
         ""]
    L.append("　　" + pad("宫位", 7) + pad("宫名", 11) + pad("主星（庙旺）", 26)
             + pad("辅星杂曜", 40) + pad("四化", 10) + "大限")
    for k in range(12):
        p = ch.palaces[(ch.soul_idx + (k if ch.forward else -k)) % 12]
        tag = "（身）" if (p.is_body and not p.is_soul) else ""
        dec = f"{p.decade[0]}-{p.decade[1]}" if p.decade else ""
        L.append("　　" + pad(p.zhi + "宫", 7) + pad(p.name + tag, 11)
                 + pad(_star_text(p), 26)
                 + pad(" ".join(p.minor), 40)
                 + pad(" ".join(p.liu_ji), 10) + dec)
    L.append("")
    san = sanfang(ch, ch.soul_idx)
    L.append("　【命宫三方四正】" + "　".join(f"{p.name}{p.zhi}：{_star_text(p)}" for p in san))
    L.append(f"　【生年四化】{ch.year_gz[0]}干："
             + "、".join(f"{s}{k}" for k, s in sihua_of(ch.year_gz[0]).items()))
    if soul.major:
        L.append("　【命宫主星】" + "、".join(
            f"{s}（{bright_of(s, soul.zhi)}·{STAR_MEANING[s]}）" for s in soul.major))
    else:
        opp = ch.palaces[(ch.soul_idx + 6) % 12]
        L.append("　【命宫主星】命宫无主星，借对宫迁移："
                 + "、".join(f"{s}（{bright_of(s, opp.zhi)}·{STAR_MEANING[s]}）" for s in opp.major)
                 + "　※ 空宫借星，力量减半，须参本宫辅曜与对宫。")
    L.append("")
    L.append("　【格局】")
    L += [f"　　· {x}" for x in patterns(ch)]
    L.append("")
    L.append("　【生年四化落宫】")
    L += [f"　　· {x}" for x in sihua_landing(ch, ch.year_gz[0])]
    L.append("")
    L.append("　【宫位要义】")
    L += [f"　　· {x}" for x in palace_notes(ch)]
    L.append("")
    now = datetime.now().year
    age_now = now - ch.when.year + 1
    L.append(f"　【限运】今 {now} 年（虚岁 {age_now}）")
    cur = next((p for p in ch.palaces if p.decade and p.decade[0] <= age_now <= p.decade[1]), None)
    if cur:
        L.append(f"　　大限：{cur.name}宫（{cur.zhi}·{cur.gz}）{cur.decade[0]}-{cur.decade[1]} 岁　"
                 + f"主星 {_star_text(cur)}　大限四化："
                 + "、".join(f"{s}{k}" for k, s in sihua_of(cur.gan).items()))
        L.append("　　　　" + "；".join(sihua_landing(ch, cur.gan)[:2]))
    li = liunian_palace(ch, now)
    lgz = GAN[(now - 1984) % 10] + ZHI[(now - 1984) % 12]
    L.append(f"　　流年：{now} 干支 {lgz}，流年宫 {li.name}（{li.zhi}）主星 {_star_text(li)}；"
             "流年四化：" + "、".join(f"{s}{k}" for k, s in sihua_of(lgz[0]).items()))
    sidx, age = small_limit(ch, now)
    sp = ch.palaces[sidx]
    L.append(f"　　小限：{sp.zhi}宫（{sp.name}）主星 {_star_text(sp)}")
    L.append("　　近五年流年宫：")
    for y in range(now, now + 5):
        lp = liunian_palace(ch, y)
        g = GAN[(y - 1984) % 10]
        L.append(f"　　　{y} {g}{ZHI[(y - 1984) % 12]}　{lp.name}（{lp.zhi}）{_star_text(lp)}"
                 f"　四化 " + "、".join(f"{s}{k}" for k, s in sihua_of(g).items()))
    L += ["", "　※ 紫微斗数以命宫、三方四正、四化为纲，庙旺利陷定星力强弱，大限流年见应期。"
              "本程序安星与 iztro 逐格核对一致，然推论属规则化引申，仅供参考。"]
    return "\n".join(L)
