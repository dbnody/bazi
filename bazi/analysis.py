# -*- coding: utf-8 -*-
"""八字断语：在排盘之上作规则化引申，使结论更细、更可读。

学理依据:
  《渊海子平》—— 十神性情、六亲宫位
  《子平真诠》—— 月令格局、成败救应
  《滴天髓》  —— 旺衰气势、寒暖燥湿
  《穷通宝典》—— 调候喜用
  《三命通会》—— 神煞、刑冲合害

说明：本模块只做「由盘推象」的规则化引申，不作吉凶铁断。
"""
from __future__ import annotations

from datetime import datetime

from . import constants as C
from .chart import KE, SHENG, WUXING, _rel, shishen

GROUP = {"比肩": "比劫", "劫财": "比劫", "食神": "食伤", "伤官": "食伤",
         "正财": "财", "偏财": "财", "正官": "官杀", "七杀": "官杀",
         "正印": "印", "偏印": "印"}
GROUPS = ["比劫", "食伤", "财", "官杀", "印"]

GROUP_DESC = {
    "比劫": "自我意识强，重朋友义气、好竞争，宜合作而忌争利。",
    "食伤": "才思外露，善表达与创作，喜自由，易恃才傲物。",
    "财": "务实重利，善经营理财，重现实，易为物所役。",
    "官杀": "重规矩责任，自我要求高，宜体制与管理，易拘谨多压。",
    "印": "好学善思，重名声与安全感，受长辈荫，行动稍缓而依赖。",
}
GROUP_LACK = {
    "比劫": "缺比劫：独立少助，凡事亲力，宜广结善缘、借力而行。",
    "食伤": "缺食伤：表达内敛、秀气不吐，宜习一技一艺以泄其秀。",
    "财": "缺财：理财观念较淡，宜稳健积累，不宜投机。",
    "官杀": "缺官杀：不喜约束、自律稍弱，宜以规矩自绳方能成事。",
    "印": "缺印：少依仗、多亲为，宜持续进修以补学养。",
}

GAN_XING = {
    "甲": "甲木参天，正直仁厚，有担当，失之固执。",
    "乙": "乙木藤萝，柔韧善变，能屈能伸，重情多虑。",
    "丙": "丙火太阳，热情豪爽，光明磊落，性急少耐。",
    "丁": "丁火灯烛，温和细腻，心思缜密，多思善感。",
    "戊": "戊土城墙，厚重守信，稳健持重，近于固执。",
    "己": "己土田园，宽厚包容，随和务实，易随波逐流。",
    "庚": "庚金斧钺，刚毅果决，重义气，失之刚愎。",
    "辛": "辛金珠玉，细腻敏锐，重品味体面，易挑剔。",
    "壬": "壬水江河，聪明多智，胸襟开阔，流于浮动。",
    "癸": "癸水雨露，内秀敏感，善体人意，易多愁善感。",
}

ZHI_HUA = {("子", "丑"): "土", ("寅", "亥"): "木", ("卯", "戌"): "火",
           ("辰", "酉"): "金", ("巳", "申"): "水", ("午", "未"): "土"}
LIUPO = [("子", "酉"), ("午", "卯"), ("巳", "申"), ("寅", "亥"), ("辰", "丑"), ("戌", "未")]
SANHUI = [("寅", "卯", "辰", "木"), ("巳", "午", "未", "火"),
          ("申", "酉", "戌", "金"), ("亥", "子", "丑", "水")]
SANXING_YIN = [("寅", "巳", "申")]

WUXING_ORDER = ["木", "火", "土", "金", "水"]


# --------------------------------------------------------------------------- #
# 十神权重
# --------------------------------------------------------------------------- #
def shishen_weights(ch) -> dict:
    """十神加权：天干各 1.0（月干 1.3），藏干本气 1.0、中气 0.5、余气 0.25（月支 ×1.5）。"""
    w = {s: 0.0 for s in C.SHISHEN.values()}
    for p in ch.pillars:
        if p.unknown:
            continue
        mult = 1.3 if p.name == "月" else 1.0
        if not p.is_day:
            w[p.gan_shishen] += 1.0 * mult
        for i, s in enumerate(p.hide_shishen):
            w[s] += (1.0, 0.5, 0.25)[min(i, 2)] * (1.5 if p.name == "月" else 1.0)
    return {k: round(v, 2) for k, v in w.items()}


def group_weights(ch) -> dict:
    w = shishen_weights(ch)
    out = {g: 0.0 for g in GROUPS}
    for s, v in w.items():
        out[GROUP[s]] += v
    return {k: round(v, 2) for k, v in out.items()}


def tou_gan(ch) -> tuple[list, list]:
    """透干十神、仅藏不透十神。"""
    tou = [p.gan_shishen for p in ch.pillars if p.gan and not p.is_day]
    cang = {s for p in ch.pillars if not p.unknown for s in p.hide_shishen}
    return tou, sorted(cang - set(tou))


# --------------------------------------------------------------------------- #
# 刑冲合害
# --------------------------------------------------------------------------- #
def zhi_relations(ch) -> list[str]:
    """四柱地支之间的刑冲合害破，附宫位义。"""
    ps = [p for p in ch.pillars if not p.unknown]
    tag = {"年": "祖基", "月": "提纲", "日": "夫妻宫", "时": "子女宫"}
    lines = []
    for i in range(len(ps)):
        for j in range(i + 1, len(ps)):
            a, b = ps[i].zhi, ps[j].zhi
            where = f"{ps[i].name}支{a}·{ps[j].name}支{b}"
            for x, y in C.LIUHE:
                if {a, b} == {x, y}:
                    hua = ZHI_HUA.get((x, y), "")
                    lines.append(f"{where} 六合{'化' + hua if hua else ''}"
                                 + ("（合夫妻宫，主亲和）" if "日" in (ps[i].name, ps[j].name) else ""))
            for x, y in C.LIUCHONG:
                if {a, b} == {x, y}:
                    extra = []
                    for p in (ps[i], ps[j]):
                        if p.name in tag:
                            extra.append(tag[p.name])
                    lines.append(f"{where} 六冲" + (f"（冲{'、'.join(extra)}）" if extra else ""))
            for x, y in C.LIUHAI:
                if {a, b} == {x, y}:
                    lines.append(f"{where} 六害")
            for x, y in LIUPO:
                if {a, b} == {x, y}:
                    lines.append(f"{where} 相破")
            if a == b:
                if a in C.ZIXING:
                    lines.append(f"{where} 伏吟自刑（同气重叠，事多反复）")
                else:
                    lines.append(f"{where} 伏吟")
            elif frozenset((a, b)) in {frozenset(("子", "卯"))}:
                lines.append(f"{where} 相刑（无礼之刑）")
            else:
                for trio in SANXING_YIN:
                    if a in trio and b in trio:
                        lines.append(f"{where} 相刑（恃势之刑）")
                        break
                for trio in C.SANXING[1:]:
                    if a in trio and b in trio:
                        lines.append(f"{where} 相刑（无恩之刑）")
                        break
    # 三合 / 三会 / 半合
    zhis = [p.zhi for p in ps]
    for x, y, z in C.SANHE:
        hit = [t for t in (x, y, z) if t in zhis]
        if len(hit) == 3:
            lines.append(f"地支见{x}{y}{z}三合局（合化{('水','木','火','金')[C.SANHE.index((x, y, z))]}）")
        elif len(hit) == 2:
            lines.append(f"地支见{hit[0]}{hit[1]}半合（三合缺一，力减）")
    for x, y, z, wx in SANHUI:
        if all(t in zhis for t in (x, y, z)):
            lines.append(f"地支见{x}{y}{z}三会{wx}局（方局成势，力大于三合）")
    return lines


def gan_relations(ch) -> list[str]:
    ps = [p for p in ch.pillars if p.gan]
    lines = []
    for i in range(len(ps)):
        for j in range(i + 1, len(ps)):
            a, b = ps[i].gan, ps[j].gan
            where = f"{ps[i].name}干{a}·{ps[j].name}干{b}"
            for x, y in C.GAN_HE:
                if {a, b} == {x, y}:
                    lines.append(f"{where} 五合（主亲近、有牵绊）")
            for x, y in C.GAN_CHONG:
                if {a, b} == {x, y}:
                    lines.append(f"{where} 相冲（主变动、分离）")
    return lines


# --------------------------------------------------------------------------- #
# 寒暖燥湿、调候
# --------------------------------------------------------------------------- #
def han_nuan(ch) -> dict:
    mz = ch.pillars[1].zhi if not ch.pillars[1].unknown else ""
    season = {"亥": "冬", "子": "冬", "丑": "冬", "寅": "春", "卯": "春", "辰": "春",
              "巳": "夏", "午": "夏", "未": "夏", "申": "秋", "酉": "秋", "戌": "秋"}.get(mz, "")
    fire = ch.wuxing_hide.get("火", 0)
    water = ch.wuxing_hide.get("水", 0)
    if season == "冬":
        judge = "天寒地冻，最喜火来暖局" if fire < 2 else "虽生冬月，局中已有火气，寒暖尚调"
        need = "火"
    elif season == "夏":
        judge = "火炎土燥，最喜水来润泽" if water < 2 else "虽生夏月，局中水气可济，燥湿得中"
        need = "水"
    elif season == "春":
        judge = "木旺土虚，喜丙火温暖、庚金修剪" if fire < 1.5 else "春木得火而秀，气势流通"
        need = "火" if fire < 1.5 else "金"
    elif season == "秋":
        judge = "金旺气肃，喜丁火炼金、壬水淘洗" if fire < 1.5 else "秋金得火而锐，成器可期"
        need = "火" if fire < 1.5 else "水"
    else:
        judge, need = "月令无考，寒暖从局中五行求之", "火" if fire < water else "水"
    return {"season": season, "fire": fire, "water": water, "judge": judge, "need": need}


def tiaohou_advice(ch) -> list[str]:
    mz = ch.pillars[1].zhi
    want = C.TIAOHOU.get(ch.day_master, {}).get(mz, "")
    if not want:
        return []
    have = {p.gan for p in ch.pillars if p.gan}
    for p in ch.pillars:
        if not p.unknown:
            have.update(p.hide)
    got = [g for g in want if g in have]
    lack = [g for g in want if g not in have]
    lines = [f"《穷通宝典》{ch.day_master}日生{mz}月，调候喜用「{want}」；"
             f"局中已见 {len(got)}/{len(want)}（{'、'.join(got) or '无'}）。"]
    if lack:
        wxs = sorted({C.GAN_WUXING[g] for g in lack})
        dirs = "、".join(C.WUXING_DIR[x] for x in wxs)
        cols = "、".join(C.WUXING_COLOR[x] for x in wxs)
        lines.append(f"　未透之调候神属{'、'.join(wxs)}：宜以居处{dirs}方位、{cols}色系、相应行业补其气。")
    return lines


# --------------------------------------------------------------------------- #
# 分项断语
# --------------------------------------------------------------------------- #
def personality(ch) -> list[str]:
    gw = group_weights(ch)
    total = sum(gw.values()) or 1
    top = sorted(gw, key=lambda k: -gw[k])
    lines = [GAN_XING.get(ch.day_master, "") + f"（{ch.day_master_wx}日主，{ch.strength_text}）"]
    lines.append(f"十神以{'、'.join(top[:2])}为重（占 {sum(gw[k] for k in top[:2]) / total:.0%}）："
                 + GROUP_DESC[top[0]])
    if gw[top[1]] / total >= 0.15 and top[1] != top[0]:
        lines.append(f"　兼{top[1]}之气：{GROUP_DESC[top[1]]}")
    weak = [g for g in GROUPS if gw[g] / total < 0.05]
    if weak:
        lines.append("　" + "、".join(weak) + "偏弱：" + "".join(GROUP_LACK[g].split("：")[-1] for g in weak))
    if "身弱" in ch.strength_text or ch.strength <= 34:
        lines.append("　身弱之人：外缘影响大，宜借势借力、择友择业，忌独木撑天。")
    elif ch.strength >= 68:
        lines.append("　身旺之人：主观刚强、能任事，宜适度泄耗（食伤财官），忌一味逞强。")
    return lines


def career(ch) -> list[str]:
    gw = group_weights(ch)
    lines = []
    if gw["官杀"] >= 2.0 and gw["印"] >= 1.2:
        lines.append("官印相生：宜公职、教育、医疗、管理及专业技术，凭资历声誉渐进。")
    elif gw["食伤"] >= 2.0 and gw["财"] >= 1.2:
        lines.append("食伤生财：宜经营、创意、技术变现、自由职业，以己之长易得财。")
    elif gw["财"] >= 2.0 and gw["官杀"] >= 1.2:
        lines.append("财官相生：宜商而兼管，或企业内掌实权，重信誉则财官两得。")
    elif gw["比劫"] >= 2.5:
        lines.append("比劫为重：宜合伙、团队、销售，须先明权责分配，忌独断争利。")
    elif gw["印"] >= 2.0:
        lines.append("印星为重：宜文教、研究、行政、后台策划，稳中求进。")
    else:
        lines.append("十神分布均匀：宜一专多能，随运而调，不宜早定终身一行。")
    yong = ch.yongshen
    ws = [w for w in WUXING_ORDER if w in yong]
    if ws:
        lines.append("用神属" + "、".join(ws) + "：行业宜 "
                     + "；".join(f"{w}—{C.WUXING_JOB[w]}" for w in ws) + "。")
    lines.append(f"格局：{ch.geju}。{ch.geju_note}")
    return lines


def wealth(ch) -> list[str]:
    gw = group_weights(ch)
    cai = gw["财"]
    strong = ch.strength >= 58
    lines = [f"财星权重 {cai:.1f}（财为养命之源，身旺任财、身弱财多反为累）。"]
    if cai < 0.8:
        lines.append("财星微弱：以薪俸、技艺稳定取财为佳，忌高杠杆与投机。")
    elif cai >= 3.0 and not strong:
        lines.append("财多身弱：古谓「富屋贫人」，宜合作、宜守成，忌独揽大项目。")
    elif cai >= 1.5 and strong:
        lines.append("身旺财旺：能任财，善经营，宜主动开拓，财来有根。")
    if gw["比劫"] >= 2.5 and cai >= 1.5:
        lines.append("比劫夺财：合伙须立字据、分清账目，忌与友朋共财不清。")
    if ch.wuxing_hide.get("金", 0) >= 3:
        lines.append("金气偏重：理财宜制度化、忌逞快钱；金为义，重信则财聚。")
    ss = ch.shensha
    for pos, names in ss.items():
        if "驿马" in names and "偏财" in (ch.pillars[["年", "月", "日", "时"].index(pos)].gan_shishen,):
            lines.append("驿马带偏财：动中求财，宜异地、外贸、物流之属。")
    return lines


def marriage(ch) -> list[str]:
    gw = group_weights(ch)
    male = ch.gender == "男"
    star = "财" if male else "官杀"
    cnt = gw[star]
    lines = [f"{'妻星（财）' if male else '夫星（官杀）'}权重 {cnt:.1f}："
             + ("星显有根，婚姻议题在其一生中分量较重。" if cnt >= 1.5 else
                "星气偏弱，感情多需主动经营，不宜坐等。" if cnt < 0.8 else
                "星气中和，婚缘随运而至，不必强求。")]
    if male and gw["比劫"] >= 2.5:
        lines.append("男命比劫重：易有竞争者或友人干预感情，宜专一守分。")
    if not male and gw["食伤"] >= 2.5:
        lines.append("女命食伤重：才情外露、要求较高，宜择包容之配，忌以言语伤人。")
    day_zhi = ch.pillars[2].zhi
    pair = ch.pillars[2].hide_shishen[0]
    lines.append(f"夫妻宫（日支{day_zhi}）本气为{pair}：配偶多呈"
                 + C.SHISHEN_DESC.get(pair, "").split("：")[-1])
    rel = [r for r in zhi_relations(ch) if "日" in r and any(k in r for k in ("冲", "刑", "害", "伏吟"))]
    if rel:
        lines.append("夫妻宫受" + "、".join(f"{r.split(' ')[1]}" for r in rel)
                     + "：宜迟婚、宜多沟通体谅，忌意气用事。")
    bad = [s for s in ("孤鸾煞", "阴差阳错", "孤辰", "寡宿") if any(s in v for v in ch.shensha.values())]
    if bad:
        lines.append("命带" + "、".join(bad) + "：传统主婚缘稍迟或聚少离多，宜晚婚、宜异地之配。")
    good = [s for s in ("天乙贵人", "金舆", "天德贵人", "月德贵人") if any(s in v for v in ch.shensha.values())]
    if good:
        lines.append("命带" + "、".join(good) + "：婚缘多得贵人成全，择偶宜听长辈之荐。")
    if any("桃花" in v for v in ch.shensha.values()):
        lines.append("命带桃花：异性缘佳、魅力足，落吉位为风雅，逢刑冲则须防情困。")
    return lines


def health(ch) -> list[str]:
    wx = ch.wuxing_hide
    low = min(WUXING_ORDER, key=lambda w: wx[w])
    high = max(WUXING_ORDER, key=lambda w: wx[w])
    lines = [f"五行以{low}最弱（{wx[low]}）、{high}最旺（{wx[high]}）。"
             f"弱则{C.WUXING_ORGAN[low]}易虚，旺则{C.WUXING_ORGAN[high]}易亢。"]
    if ch.missing:
        lines.append("命局缺" + "、".join(ch.missing) + "："
                     "相关脏腑功能宜以作息、饮食调养，不必过虑。")
    hn = han_nuan(ch)
    lines.append(f"寒暖：{hn['judge']}（火 {hn['fire']} / 水 {hn['water']}）。")
    if ch.pillars[2].dishi in ("死", "绝", "病", "墓"):
        lines.append(f"日主坐{ch.pillars[2].dishi}地：元气偏弱，宜规律作息、忌熬夜劳损。")
    lines.append("以上为五行偏枯之倾向，非疾病论断；有不适请就医。")
    return lines


def study(ch) -> list[str]:
    gw = group_weights(ch)
    marks = [s for s in ("文昌贵人", "华盖", "太极贵人", "天乙贵人")
             if any(s in v for v in ch.shensha.values())]
    lines = [f"印星权重 {gw['印']:.1f}（主学习吸收）、食伤 {gw['食伤']:.1f}（主表达输出）。"]
    if gw["印"] >= 1.5:
        lines.append("印旺：宜系统深造、考取证照，理论功底胜于临场应变。")
    elif gw["印"] < 0.6:
        lines.append("印弱：自学力强而不耐系统课程，宜以实践带动学习。")
    if gw["食伤"] >= 1.5:
        lines.append("食伤旺：口头与文字表达佳，宜演讲、写作、设计、教研。")
    if marks:
        lines.append("命带" + "、".join(marks) + "：利读书考试、宜文史哲与专业钻研。")
    if "华盖" in marks:
        lines.append("华盖入命：性喜玄思，于哲学、宗教、术数、艺术别有会心。")
    return lines


# --------------------------------------------------------------------------- #
# 流年
# --------------------------------------------------------------------------- #
LN_HINT = {
    "比肩": "同辈助力、亦主竞争分利", "劫财": "合作与破财并存，宜守",
    "食神": "安逸口福、利才艺表达", "伤官": "变动求新，忌口舌犯上",
    "正财": "正业得财、婚恋可期", "偏财": "意外之财与应酬，宜节制",
    "正官": "职位、责任、考试文书", "七杀": "压力与挑战，宜稳中求进",
    "正印": "贵人、学业、文书庇荫", "偏印": "偏门学问、孤独多思",
}


def _liunian_score(ch, gz: str) -> tuple[int, list[str]]:
    score, tags = 0, []
    for i, w in enumerate((C.GAN_WUXING[gz[0]], C.ZHI_WUXING[gz[1]])):
        s = 2 if i == 0 else 1
        tag = f"{w}为用" if w in ch.yongshen else (f"{w}为忌" if w in ch.jishen else "")
        if w in ch.yongshen:
            score += s
        elif w in ch.jishen:
            score -= s
        if tag and tag not in tags:
            tags.append(tag)
    day_zhi = ch.pillars[2].zhi
    mon_zhi = ch.pillars[1].zhi
    for x, y in C.LIUCHONG:
        if {gz[1], day_zhi} == {x, y}:
            score -= 1
            tags.append("冲夫妻宫")
        if {gz[1], mon_zhi} == {x, y}:
            score -= 1
            tags.append("冲提纲")
    for x, y in C.LIUHE:
        if {gz[1], day_zhi} == {x, y}:
            score += 1
            tags.append("合夫妻宫")
    if gz[1] == ch.pillars[0].zhi and not ch.pillars[0].unknown:
        tags.append("本命年")
        score -= 1
    return score, tags


def liunian_forecast(ch, years: int = 10, start: int | None = None) -> list[tuple]:
    from .chart import current_dayun, liunian_of
    start = start or datetime.now().year
    out = []
    for y in range(start, start + years):
        gz = liunian_of(ch, None, y)
        dy = current_dayun(ch, y)
        sc, tags = _liunian_score(ch, gz)
        out.append((y, gz, shishen(ch.day_master, gz[0]), dy.gan_zhi if dy else "—",
                    "吉" if sc > 0 else ("忌" if sc < 0 else "平"), sc, tags))
    return out


# --------------------------------------------------------------------------- #
# 汇总裁剪
# --------------------------------------------------------------------------- #
def liuqin_palaces(ch) -> list[str]:
    """四柱宫位与六亲：年祖上、月父母兄弟、日自身配偶、时子女晚辈。"""
    where = {"年": "祖上、长辈", "月": "父母、兄弟", "日": "自身与配偶", "时": "子女、晚辈"}
    lines = []
    for p in ch.pillars:
        if p.unknown:
            lines.append("时柱：时辰不详，子女宫与晚运参看大运流年。")
            continue
        star = "日主" if p.is_day else p.gan_shishen
        desc = "自身本体，亦为配偶之镜" if p.is_day else C.SHISHEN_DESC.get(star, "")
        lines.append(f"{p.name}柱 {p.gz}（{where[p.name]}）：{star} —— {desc}")
    return lines


def gong_detail(ch) -> str:
    """命宫、身宫、胎元之纳音与十神。"""
    from .chart import _nayin
    out = []
    for label, gz in (("命宫", ch.minggong), ("身宫", ch.shengong), ("胎元", ch.taiyuan)):
        if not gz or len(gz) < 2:
            continue
        ss = shishen(ch.day_master, gz[0]) if gz[0] in C.GAN else ""
        out.append(f"{label}{gz}（{_nayin(gz[0], gz[1])}·{ss}）")
    return "　".join(out)


def render_extra(ch) -> list[str]:
    L: list[str] = []
    w = shishen_weights(ch)
    tou, cang = tou_gan(ch)
    gw = group_weights(ch)
    L.append("【十神】" + "　".join(f"{k}{v}" for k, v in w.items() if v))
    L.append("　　透干：" + ("、".join(tou) or "—") + "　　藏而不透：" + ("、".join(cang) or "—"))
    L.append("　　五类：" + "　".join(f"{g}{gw[g]}" for g in GROUPS))
    L.append("")
    L.append("【宫位六亲】（年祖上、月父母兄弟、日自身配偶、时子女晚辈）")
    L += [f"　　{x}" for x in liuqin_palaces(ch)]
    L.append("")
    L.append("【命身胎元】" + gong_detail(ch))
    L.append("")
    L.append("【性情】")
    L += [f"　　{x}" for x in personality(ch)]
    L.append("")
    rel = gan_relations(ch) + zhi_relations(ch)
    L.append("【刑冲合害】（《三命通会》）")
    if rel:
        L += [f"　　· {x}" for x in rel]
    else:
        L.append("　　四柱之间无刑冲合害，气势平稳。")
    L.append("")
    hn = han_nuan(ch)
    L.append(f"【寒暖燥湿】生{hn['season']}月　{hn['judge']}；喜{hn['need']}。")
    L += [f"　　{x}" for x in tiaohou_advice(ch)]
    L.append("")
    L.append("【事业】")
    L += [f"　　· {x}" for x in career(ch)]
    L.append("【财运】")
    L += [f"　　· {x}" for x in wealth(ch)]
    L.append("【婚恋】")
    L += [f"　　· {x}" for x in marriage(ch)]
    L.append("【健康】")
    L += [f"　　· {x}" for x in health(ch)]
    L.append("【学业】")
    L += [f"　　· {x}" for x in study(ch)]
    L.append("")
    yong = ch.yongshen
    ws = [x for x in WUXING_ORDER if x in yong]
    if ws:
        L.append("【趋避】用神属" + "、".join(ws) + "："
                 + "；".join(f"{x}—方位{C.WUXING_DIR[x]}、色{C.WUXING_COLOR[x]}" for x in ws))
    L.append("")
    L.append("【流年】未来十年（流年吉忌据用神喜忌、刑冲本命判，须与大运合参）")
    L.append("　　年份　流年　十神　　大运　判　　备注")
    for y, gz, ss, dy, luck, sc, tags in liunian_forecast(ch):
        L.append(f"　　{y}　{gz}　{ss}　{dy}　{luck}({sc:+d})　{'、'.join(tags[:3])}")
    return L
