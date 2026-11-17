# -*- coding: utf-8 -*-
"""八字排盘：四柱、十神、藏干、旺衰、格局、用神、神煞、大运流年.

学理依据:
  《渊海子平》—— 十神、六亲、格局总纲
  《子平真诠》—— 月令取格、成败救应
  《滴天髓》  —— 旺衰气势、寒暖燥湿
  《穷通宝典》—— 调候用神
  《三命通会》—— 神煞、纳音
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from lunar_python import Solar

from . import constants as C
from .calendar_core import true_solar_time

WUXING = ["木", "火", "土", "金", "水"]
SHENG = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}   # 我生
KE = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}       # 我克


def _w(s: str) -> int:
    """显示宽度：中日韩全角字符按 2 计。"""
    return sum(2 if ord(c) > 0x2E7F else 1 for c in s)


def _pad(s: str, width: int) -> str:
    return s + " " * max(0, width - _w(s))


def _rel(me: str, other: str) -> str:
    if me == other:
        return "同"
    if SHENG[me] == other:
        return "生"
    if KE[me] == other:
        return "克"
    if KE[other] == me:
        return "攻"
    return "养"


def shishen(day_gan: str, gan: str) -> str:
    me = C.GAN_WUXING[day_gan]
    other = C.GAN_WUXING[gan]
    same = (C.GAN.index(day_gan) % 2) == (C.GAN.index(gan) % 2)
    return C.SHISHEN[(_rel(me, other), same)]


def dishi(day_gan: str, zhi: str) -> str:
    start = C.CHANGSHENG_START[day_gan]
    forward = C.GAN.index(day_gan) % 2 == 0      # 阳干顺行
    step = (C.ZHI.index(zhi) - C.ZHI.index(start)) % 12
    if not forward:
        step = (-step) % 12
    return C.CHANGSHENG[step]


@dataclass
class Pillar:
    name: str
    gan: str
    zhi: str
    gan_shishen: str
    hide: list
    hide_shishen: list
    nayin: str
    dishi: str
    xunkong: str
    is_day: bool = False
    unknown: bool = False

    @property
    def gz(self) -> str:
        return self.gan + self.zhi


@dataclass
class DaYun:
    index: int
    gan_zhi: str
    start_age: int
    end_age: int
    start_year: int
    end_year: int
    shishen: str = ""
    liunian: list = field(default_factory=list)


@dataclass
class Chart:
    name: str
    gender: str
    birth: datetime
    used: datetime
    is_true_solar: bool
    hour_known: bool
    longitude: float
    tst_offset: float
    lunar_text: str
    shengxiao: str
    jieqi_info: str
    pillars: list
    day_master: str
    day_master_wx: str
    taiyuan: str
    minggong: str
    shengong: str
    wuxing_count: dict
    wuxing_hide: dict
    missing: list
    strength: float
    strength_text: str
    geju: str
    geju_note: str
    yongshen: str
    jishen: str
    tiaohou: str
    shensha: dict
    dayun: list
    start_text: str
    forward: bool
    hour_label: str = ''
    notes: list = field(default_factory=list)


def _pillar(name, gan, zhi, day_gan, is_day=False) -> Pillar:
    hide = list(C.ZHI_CANG[zhi])
    return Pillar(
        name=name, gan=gan, zhi=zhi,
        gan_shishen=("日主" if is_day else shishen(day_gan, gan)),
        hide=hide,
        hide_shishen=[shishen(day_gan, h) for h in hide],
        nayin=_nayin(gan, zhi),
        dishi=dishi(day_gan, zhi),
        xunkong="",
        is_day=is_day,
    )


def _nayin(gan: str, zhi: str) -> str:
    for i in range(60):
        if i % 10 == C.GAN.index(gan) and i % 12 == C.ZHI.index(zhi):
            return C.NAYIN[i // 2]
    return ""


def _shensha(year_gz: str, month_zhi: str, day_gan: str, pillars: list) -> dict:
    """按日干、年干、月支、日支、年支查神煞，返回 {柱名: [神煞...]}。"""
    out = {p.name: [] for p in pillars if not p.unknown}
    zhis = [(p.name, p.zhi) for p in pillars if not p.unknown]

    def add(where, name):
        if name not in out[where]:
            out[where].append(name)

    for pname, z in zhis:
        for g in (day_gan, year_gz[0]):
            if z in C.TIANYI.get(g, ""):
                add(pname, "天乙贵人")
            if z in C.TAIJI.get(g, ""):
                add(pname, "太极贵人")
            if z == C.WENCHANG.get(g):
                add(pname, "文昌贵人")
            if z == C.LUSHEN.get(g):
                add(pname, "禄神")
            if z == C.YANGREN.get(g):
                add(pname, "羊刃")
            if z == C.JINYU.get(g):
                add(pname, "金舆")
            if z == C.HONGYAN.get(g):
                add(pname, "红艳")
        if z == C.TIANDE.get(month_zhi):
            add(pname, "天德贵人")
        if z == C.YUEDE.get(month_zhi):
            add(pname, "月德贵人")
        for key in (month_zhi, pillars[2].zhi, year_gz[1]):
            if z == C.TAOHUA.get(key):
                add(pname, "桃花")
            if z == C.YIMA.get(key):
                add(pname, "驿马")
            if z == C.HUAGAI.get(key):
                add(pname, "华盖")
            if z == C.JIANGXING.get(key):
                add(pname, "将星")
            if z == C.JIESHA.get(key):
                add(pname, "劫煞")
            if z == C.ZAISHA.get(key):
                add(pname, "灾煞")
        if z == C.GUSHEN.get(year_gz[1]):
            add(pname, "孤辰")
        if z == C.GUASU.get(year_gz[1]):
            add(pname, "寡宿")
        if pillars[2].xunkong and z in pillars[2].xunkong:
            add(pname, "空亡")
    return out


def _wuxing_stats(pillars: list) -> tuple[dict, dict]:
    """天干地支计数 + 含藏干加权统计。"""
    plain = {w: 0 for w in WUXING}
    weighted = {w: 0.0 for w in WUXING}
    for p in pillars:
        if p.unknown:
            continue
        w = C.GAN_WUXING[p.gan]
        plain[w] += 1
        weighted[w] += 1.0 if p.is_day else 1.2
        z = C.ZHI_WUXING[p.zhi]
        plain[z] += 1
        weighted[z] += 1.0
        for i, h in enumerate(p.hide):
            weighted[C.GAN_WUXING[h]] += (0.6, 0.3, 0.15)[min(i, 2)]
    return plain, {k: round(v, 2) for k, v in weighted.items()}


def _strength(day_gan: str, pillars: list, month_zhi: str) -> tuple[float, str]:
    """日主旺衰：得令、得地、得势三才计分（《滴天髓》气势论 / 《子平真诠》）。

    以 50 分为中和基准：月令定格局之势（±38），地支通根（得地）、天干比印官财（得势）加减，
    回归《渊海子平》「月令为提纲，得令者旺」之旨。
    """
    me = C.GAN_WUXING[day_gan]
    score = 50.0

    # 一、得令：月支本气与日主之生克
    mb = C.ZHI_CANG[month_zhi][0]
    score += {"同": 38.0, "养": 28.0, "生": -12.0, "克": -26.0, "攻": -38.0}[_rel(me, C.GAN_WUXING[mb])]

    # 二、得地：地支藏干通根（本气/中气/余气，月支加倍）
    for p in pillars:
        if p.unknown:
            continue
        for i, h in enumerate(p.hide):
            v = (8.0, 4.0, 2.0)[min(i, 2)] * (1.5 if p.name == "月" else 1.0)
            rel = _rel(me, C.GAN_WUXING[h])
            if rel == "同":
                score += v
            elif rel == "养":
                score += v * 0.7
            elif rel == "攻":
                score -= v * 0.7
            else:
                score -= v * 0.5

    # 三、得势：天干比劫印星帮身，官杀财食伤耗身
    for p in pillars:
        if p.is_day or not p.gan:
            continue
        rel = _rel(me, C.GAN_WUXING[p.gan])
        score += {"同": 7.0, "养": 5.0, "生": -5.0, "克": -4.0, "攻": -7.0}[rel]

    score = max(0.0, min(100.0, score))
    if score >= 68:
        txt = "身强（旺）"
    elif score >= 58:
        txt = "偏强"
    elif score >= 44:
        txt = "中和"
    elif score >= 34:
        txt = "偏弱"
    else:
        txt = "身弱"
    return round(score, 1), txt


def _geju(day_gan: str, pillars: list, month_zhi: str, ratio: float) -> tuple[str, str]:
    """月令取格（《子平真诠》：用神专寻月令，透干者优先）。"""
    benqi = C.ZHI_CANG[month_zhi][0]
    ss = shishen(day_gan, benqi)
    tou = [(p.name, p.gan) for p in pillars if p.gan and not p.is_day]
    tou_ss = {shishen(day_gan, g) for _, g in tou}

    if ss in ("比肩", "劫财"):
        base = "建禄格" if ss == "比肩" else "月劫格"
        hit = [o for o in ("正官", "七杀", "正财", "偏财", "食神", "伤官") if o in tou_ss]
        if hit:
            return f"{base}（透{hit[0]}）", "月令为日主禄刃，透官杀则贵、透财食则富；忌比劫重逢争财夺禄。"
        return base, "月令为比劫，喜官杀制刃、食伤泄秀，不宜再见比劫帮身。"

    # 中气/余气透干者，取透出者为格
    for h in C.ZHI_CANG[month_zhi][1:]:
        h_ss = shishen(day_gan, h)
        if h_ss in tou_ss:
            return (f"{h_ss}格（月令{ss}不透，{h_ss}透干）",
                    "月令中藏之气透出天干，取透者为格，此《子平真诠》「月令用神」之法。")

    note = {
        "正官": "官星清纯，喜财生、印护，忌伤官克官、刑冲提纲。",
        "七杀": "杀须有制或有化，食制杀、印化杀皆为贵格，最忌身弱杀重。",
        "正财": "财旺身弱则富屋贫人，须比劫帮身或印星生扶，喜官星护财。",
        "偏财": "偏财喜身旺、喜官星，为流动之财，忌比劫分夺。",
        "食神": "食神吐秀，喜身旺、财星承接，最忌枭印夺食。",
        "伤官": "伤官喜佩印或生财，忌见官星（伤官见官为祸百端）。",
        "正印": "印星护身，喜官杀生印，忌财星破印。",
        "偏印": "枭神喜制，宜见财星，忌与食神同透。",
    }.get(ss, "")
    return f"{ss}格", note


def _yongshen(day_gan: str, month_zhi: str, ratio: float, pillars: list) -> tuple[str, str, str]:
    me = C.GAN_WUXING[day_gan]
    sheng_me = next(C.GAN_WUXING[g] for g in C.GAN if SHENG[C.GAN_WUXING[g]] == me)  # 生我
    wo_sheng = SHENG[me]                                                             # 我生
    wo_ke = KE[me]                                                                   # 我克
    ke_me = next(C.GAN_WUXING[g] for g in C.GAN if KE[C.GAN_WUXING[g]] == me)        # 克我
    if ratio >= 58:
        yong = f"{wo_ke}（财）、{wo_sheng}（食伤）"
        ji = f"{ke_me}（官杀过重则克身）"
        ytext = f"身旺宜泄宜克：以{wo_ke}耗其势、{wo_sheng}泄其秀，忌比劫再来助身。"
    elif ratio <= 44:
        yong = f"{sheng_me}（印）、比劫"
        ji = f"{wo_ke}（财耗身）、{ke_me}（官杀克身）"
        ytext = f"身弱宜生宜扶：以{sheng_me}生身、比劫帮身，忌财多坏印、杀重攻身。"
    else:
        yong = f"{wo_sheng}（食伤）、{wo_ke}（财）"
        ji = "偏枯之运"
        ytext = "日主中和，宜顺其气势：食伤生财、官印相生各得其宜，忌偏枯偏旺。"
    th = C.TIAOHOU.get(day_gan, {}).get(month_zhi, "")
    return yong, ji, f"{ytext}《穷通宝典》调候取{th}。"


def build_chart(name: str, gender: str, dt: datetime, use_true_solar: bool = False,
                longitude: float = 120.0, sect: int = 2, hour_known: bool = True,
                hour_label: str = '') -> Chart:
    """排盘。gender: 男/女；sect: 1=晚子时算次日，2=晚子时算当日。

    hour_known=False 表示时辰不详：时柱不排，旺衰/神煞/五行统计均不计时柱。
    hour_label 用于只记到时辰（如「辰时」）时替代精确时刻显示。
    """
    used = dt
    offset = 0.0
    if use_true_solar:
        used, offset = true_solar_time(dt, longitude)
    solar = Solar.fromYmdHms(used.year, used.month, used.day, used.hour, used.minute, 0)
    lunar = solar.getLunar()
    ec = lunar.getEightChar()
    ec.setSect(sect)

    day_gan = ec.getDayGan()
    day_master_wx = C.GAN_WUXING[day_gan]
    pillars = [
        _pillar("年", ec.getYearGan(), ec.getYearZhi(), day_gan),
        _pillar("月", ec.getMonthGan(), ec.getMonthZhi(), day_gan),
        _pillar("日", ec.getDayGan(), ec.getDayZhi(), day_gan, is_day=True),
        _pillar("时", ec.getTimeGan(), ec.getTimeZhi(), day_gan),
    ]
    xunkongs = [ec.getYearXunKong(), ec.getMonthXunKong(), ec.getDayXunKong(), ec.getTimeXunKong()]
    for p, xk in zip(pillars, xunkongs):
        p.xunkong = xk
    if not hour_known:
        pillars[3] = Pillar("时", "", "", "", [], [], "", "", "", False, True)

    plain, weighted = _wuxing_stats(pillars)
    missing = [w for w in WUXING if plain[w] == 0]
    ratio, stext = _strength(day_gan, pillars, ec.getMonthZhi())
    geju, gnote = _geju(day_gan, pillars, ec.getMonthZhi(), ratio)
    yong, ji, yn = _yongshen(day_gan, ec.getMonthZhi(), ratio, pillars)
    shensha = _shensha(ec.getYear(), ec.getMonthZhi(), day_gan, pillars)

    yun = ec.getYun(1 if gender == "男" else 0)
    dayun = []
    for d in yun.getDaYun():
        if d.getIndex() == 0:
            continue
        item = DaYun(index=d.getIndex(), gan_zhi=d.getGanZhi(),
                     start_age=d.getStartAge(), end_age=d.getEndAge(),
                     start_year=d.getStartYear(), end_year=d.getEndYear())
        item.shishen = shishen(day_gan, d.getGanZhi()[0])
        dayun.append(item)
    start_text = f"{yun.getStartYear()}年{yun.getStartMonth()}个月{yun.getStartDay()}天后起运（{yun.getStartSolar().toYmd()}）"

    jq = lunar.getPrevJieQi(True)
    jieqi_info = f"{jq.getName()} {jq.getSolar().toYmdHms()} 后生"

    return Chart(
        name=name, gender=gender, birth=dt, used=used, is_true_solar=use_true_solar,
        hour_known=hour_known,
        hour_label=hour_label,
        longitude=longitude, tst_offset=offset,
        lunar_text=lunar.toString(), shengxiao=lunar.getYearShengXiaoByLiChun(),
        jieqi_info=jieqi_info, pillars=pillars, day_master=day_gan,
        day_master_wx=day_master_wx, taiyuan=ec.getTaiYuan(),
        minggong=ec.getMingGong(), shengong=ec.getShenGong(),
        wuxing_count=plain, wuxing_hide=weighted, missing=missing,
        strength=ratio, strength_text=stext, geju=geju, geju_note=gnote,
        yongshen=yong, jishen=ji, tiaohou=yn, shensha=shensha, dayun=dayun,
        start_text=start_text, forward=yun.isForward(),
    )


def render_chart(ch: Chart) -> str:
    L = []
    t = ch.pillars
    L.append(f"【命主】{ch.name or '未名'}　{ch.gender}命　生于 {ch.hour_label or format(ch.birth, '%Y-%m-%d %H:%M')}")
    if ch.is_true_solar:
        L.append(f"　　　　真太阳时 {ch.used:%Y-%m-%d %H:%M}（经度 {ch.longitude:.2f}°，校正 {ch.tst_offset:+.1f} 分）")
    L.append(f"　　　　农历 {ch.lunar_text}　生肖{ch.shengxiao}　{ch.jieqi_info}")
    L.append("")
    def uc(p, s):
        return "—" if p.unknown else s

    rows = [
        ("", ["年柱", "月柱", "日柱", "时柱"]),
        ("天干", [uc(p, f"{p.gan}·{p.gan_shishen}") for p in t]),
        ("地支", [uc(p, p.zhi) for p in t]),
        ("藏干", [uc(p, "".join(p.hide)) for p in t]),
        ("藏神", [uc(p, "·".join(p.hide_shishen)) for p in t]),
        ("纳音", [uc(p, p.nayin) for p in t]),
        ("星运", [uc(p, p.dishi) for p in t]),
        ("空亡", [uc(p, p.xunkong) for p in t]),
    ]
    widths = [max(_w(row[i]) for _, row in rows) for i in range(4)]
    for label, cells in rows:
        prefix = "　　" + _pad(label, 4) + "  "
        line = "".join(_pad(c, widths[i]) + "  " for i, c in enumerate(cells)).rstrip()
        L.append(prefix + line)
    if not ch.hour_known:
        L.append("　　※ 时辰不详：时柱未排，旺衰、神煞、五行统计均不计时柱；"
                 "日柱、大运、流年不受影响。")
    L.append("")
    L.append(f"【命宫】{ch.minggong}　【身宫】{ch.shengong}　【胎元】{ch.taiyuan}")
    L.append(f"【五行】" + "　".join(f"{w}{ch.wuxing_count[w]}" for w in WUXING) +
             f"　　（含藏干加权：" + " ".join(f"{w}{ch.wuxing_hide[w]}" for w in WUXING) + "）")
    L.append(f"　　　　五行{'齐全' if not ch.missing else '缺' + '、'.join(ch.missing)}")
    L.append("")
    L.append(f"【日主】{ch.day_master}{ch.day_master_wx}　{ch.strength_text}　得分 {ch.strength}（50 为中和）")
    L.append(f"【格局】{ch.geju}　{ch.geju_note}")
    L.append(f"【用神】{ch.yongshen}　【忌神】{ch.jishen}")
    L.append(f"　　　　{ch.tiaohou}")
    L.append("")
    L.append("【神煞】（《三命通会》）")
    for p in t:
        ss = ch.shensha.get(p.name) or []
        L.append(f"　　{p.name}柱：" + ("、".join(ss) if ss else "—"))
    for name in sorted({s for v in ch.shensha.values() for s in v}):
        L.append(f"　　· {name}：{C.SHENSHA_DESC.get(name, '')}")
    L.append("")
    L.append(f"【大运】{ch.start_text}　{'顺行' if ch.forward else '逆行'}")
    L.append("　　序号　干支　十神　吉忌　起始年龄　起止年份")
    for d in ch.dayun:
        L.append(f"　　{d.index:>2}　　{d.gan_zhi}　{d.shishen}　{_yun_luck(ch, d.gan_zhi)}　"
                 f"{d.start_age:>2}-{d.end_age:<2}岁　{d.start_year}-{d.end_year}")
    now = datetime.now().year
    ln = liunian_of(ch, None, now)
    cur = current_dayun(ch, now)
    if cur:
        L.append(f"【今年】{now}年 流年 {ln}（{shishen(ch.day_master, ln[0])}·{_yun_luck(ch, ln)}）"
                 f"　行 {cur.gan_zhi} 大运（{cur.shishen}）")
    else:
        L.append(f"【今年】{now}年 流年 {ln}（{shishen(ch.day_master, ln[0])}·{_yun_luck(ch, ln)}）")
    L.append("")
    L.append("【说明】本程序依《渊海子平》《子平真诠》《滴天髓》《穷通宝典》《三命通会》之理排演，")
    L.append("　　　　命理属传统文化，结论仅供参考，不作人生决策之唯一依据。")
    return "\n".join(L)


def _yun_luck(ch: Chart, gz: str) -> str:
    """大运/流年干支五行与用神喜忌的粗判。"""
    gan_w = C.GAN_WUXING[gz[0]]
    zhi_w = C.ZHI_WUXING[gz[1]]
    if gan_w in ch.yongshen or zhi_w in ch.yongshen:
        return "吉"
    if gan_w in ch.jishen or zhi_w in ch.jishen:
        return "忌"
    return "平"


def current_dayun(ch: Chart, year: int):
    for d in ch.dayun:
        if d.start_year <= year <= d.end_year:
            return d
    return None


def liunian_of(ch: Chart, dayun: DaYun, year: int) -> str:
    """某年流年干支。"""
    idx = (year - 1984) % 60
    return C.GAN[idx % 10] + C.ZHI[idx % 12]
