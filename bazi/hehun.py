# -*- coding: utf-8 -*-
"""八字合婚（婚配）.

学理依据:
  《三命通会·论纳音合婚》—— 年命纳音相生相克
  《渊海子平·论婚姻》    —— 日柱、财官、夫妻宫
  《玉照定真经》          —— 生肖六合三合、刑冲害
  《紫微斗数全书》        —— 双方命宫、夫妻宫星曜对照
  《增删卜易》择期之理    —— 流年合夫妻宫者利成婚
评分权重（本程序设定，总计 100）:
  年命纳音 12 · 生肖合冲 12 · 日柱干支 24 · 五行互补 22
  夫妻星 8 · 日主生扶 8 · 紫微夫妻宫 9 · 婚期机缘 5
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from . import constants as C
from .chart import Chart, KE, SHENG, liunian_of, shishen
from . import ziwei as zw


def _nayin_wx(nayin: str) -> str:
    return nayin[-1]


def _relation(a: str, b: str) -> str:
    """五行 a 对 b 的关系。"""
    if a == b:
        return "比和"
    if SHENG[a] == b:
        return "相生"
    if KE[a] == b:
        return "相克"
    if KE[b] == a:
        return "被克"
    return "相生"


def _zhi_relation(a: str, b: str) -> tuple[str, str]:
    for x, y in C.LIUHE:
        if {a, b} == {x, y}:
            return "六合", "＋"
    for trio in C.SANHE:
        if a in trio and b in trio:
            return "三合", "＋"
    for x, y in C.LIUCHONG:
        if {a, b} == {x, y}:
            return "六冲", "－"
    for x, y in C.LIUHAI:
        if {a, b} == {x, y}:
            return "六害", "－"
    for trio in C.SANXING:
        if a in trio and b in trio and a != b:
            return "相刑", "－"
    if a == b and a in C.ZIXING:
        return "自刑", "－"
    if a == b:
        return "伏吟", "○"
    return "无特殊关系", "○"


def _gan_relation(a: str, b: str) -> tuple[str, str]:
    for x, y in C.GAN_HE:
        if {a, b} == {x, y}:
            return "天干五合", "＋"
    for x, y in C.GAN_CHONG:
        if {a, b} == {x, y}:
            return "天干四冲", "－"
    ra = _relation(C.GAN_WUXING[a], C.GAN_WUXING[b])
    return {"比和": "同类", "相生": "相生", "相克": "相克", "被克": "受生"}[ra], \
        {"比和": "○", "相生": "＋", "相克": "－", "被克": "＋"}[ra]


def shishen_counts(ch: Chart) -> dict:
    out = {}
    for p in ch.pillars:
        if p.unknown:
            continue
        if p.gan_shishen != "日主":
            out[p.gan_shishen] = out.get(p.gan_shishen, 0) + 1
        for s in p.hide_shishen:
            out[s] = out.get(s, 0) + 1
    return out


@dataclass
class HunResult:
    score: int
    grade: str
    sections: list = field(default_factory=list)   # [(标题, [行], 得分, 满分)]
    advice: list = field(default_factory=list)


def _add(sections, title, lines, score, full):
    sections.append((title, lines, round(score, 1), full))
    return score


def hehun(male: Chart, female: Chart) -> HunResult:
    sec = []
    total = 0.0

    # 1 年命纳音
    mw, fw = _nayin_wx(male.pillars[0].nayin), _nayin_wx(female.pillars[0].nayin)
    rel = _relation(mw, fw)
    pts = {"相生": 12, "比和": 9, "被克": 6, "相克": 3}[rel]
    total += _add(sec, "一、年命纳音", [
        f"男命 {male.pillars[0].gz}　纳音{male.pillars[0].nayin}（{mw}）",
        f"女命 {female.pillars[0].gz}　纳音{female.pillars[0].nayin}（{fw}）",
        f"关系：{rel}　《三命通会》云：纳音相生主和睦，比和亦吉；相克则防口舌刑伤。",
        f"{'男命生女命，主男方多付出而和顺。' if rel == '相生' and SHENG[mw] == fw else ''}"
        f"{'女命生男命，主女方助夫得力。' if rel == '相生' and SHENG[fw] == mw else ''}"
        f"{'相克者，宜以婚期、居所方位调和。' if rel in ('相克', '被克') else ''}".rstrip(),
    ], pts, 12)

    # 2 生肖
    mz, fz = male.pillars[0].zhi, female.pillars[0].zhi
    zrel, zsign = _zhi_relation(mz, fz)
    pts = {"六合": 12, "三合": 10}.get(zrel, 7 if zrel == "无特殊关系" else 3)
    total += _add(sec, "二、生肖属相", [
        f"男属{C.SHENGXIAO[mz]}（{mz}）　女属{C.SHENGXIAO[fz]}（{fz}）",
        f"关系：{zrel}（{zsign}）",
        {"六合": "六合者，情投意合，白头相守，上吉。",
         "三合": "三合者，志同道合，家道兴隆，吉。",
         "六冲": "六冲者，性格易生对撞，须互相容忍，忌同日争强。",
         "六害": "六害者，易生猜疑隔阂，宜多沟通、少猜忌。",
         "相刑": "相刑者，口舌琐碎，宜以礼相待，忌翻旧账。",
         "自刑": "自刑者，多因自身执念生隙，宜各让一步。",
         "伏吟": "伏吟者，性情相近，同气相求，亦须防同过则争。",
         }.get(zrel, "属相无刑冲害合，平平，重在日柱相配。") + "（《玉照定真经》）",
    ], pts, 12)

    # 3 日柱
    mg, fg = male.pillars[2].gan, female.pillars[2].gan
    mdz, fdz = male.pillars[2].zhi, female.pillars[2].zhi
    grel, gsign = _gan_relation(mg, fg)
    drel, dsign = _zhi_relation(mdz, fdz)
    pts = 12.0
    pts += 8 if gsign == "＋" else (0 if gsign == "○" else -8)
    pts += 8 if dsign == "＋" else (0 if dsign == "○" else -8)
    pts = max(0, min(24, pts))
    total += _add(sec, "三、日柱（夫妻宫）", [
        f"男命日柱 {male.pillars[2].gz}　女命日柱 {female.pillars[2].gz}",
        f"天干：{mg}{C.GAN_WUXING[mg]} 与 {fg}{C.GAN_WUXING[fg]} —— {grel}",
        f"地支：{mdz} 与 {fdz} —— {drel}",
        "《渊海子平》：日干为夫/妻之本体，日支为夫妻宫；干合支合者，情偕意合；",
        "干支俱冲者，聚少离多；夫妻宫伏吟者，易见迟婚或再婚之象。",
        f"日支（夫妻宫）{mdz}为男命{'财星' if C.ZHI_WUXING[mdz] in male.yongshen else '比印'}之地，"
        f"{fdz}为女命{'官星' if C.ZHI_WUXING[fdz] in female.yongshen else '比印'}之地；"
        "夫妻宫得用神者，婚后得力。",
    ], pts, 24)

    # 4 五行互补
    mw_map, fw_map = male.wuxing_hide, female.wuxing_hide
    gain = 0.0
    notes = []
    for w in ("木", "火", "土", "金", "水"):
        if mw_map[w] < 1.2 and fw_map[w] >= 2.2:
            gain += 3.0
            notes.append(f"男命缺{w}，女命{w}旺（{fw_map[w]}），女能补男之不足。")
        if fw_map[w] < 1.2 and mw_map[w] >= 2.2:
            gain += 3.0
            notes.append(f"女命缺{w}，男命{w}旺（{mw_map[w]}），男能助女之所乏。")
    for w in ("木", "火", "土", "金", "水"):
        if mw_map[w] >= 3.5 and fw_map[w] >= 3.5:
            gain -= 2.5
            notes.append(f"双方{w}俱旺（{mw_map[w]}/{fw_map[w]}），同气过盛，宜互让锋芒。")
    pts = max(0, min(22, 11.0 + gain))
    total += _add(sec, "四、五行互补", notes or ["双方五行分布均衡，无明显互补或冲激。"], pts, 22)

    # 5 夫妻星
    mss, fss = shishen_counts(male), shishen_counts(female)
    m_cai = mss.get("正财", 0) + mss.get("偏财", 0)
    f_guan = fss.get("正官", 0) + fss.get("七杀", 0)
    pts, notes = 4.0, []
    if m_cai:
        pts += 2.0
        notes.append(f"男命财星 {m_cai} 见（财为妻星），妻缘分明。")
    else:
        notes.append("男命财星不显，感情宜主动经营，忌过于理性。")
    if f_guan:
        pts += 2.0
        notes.append(f"女命官杀 {f_guan} 见（官为夫星），夫缘有靠。")
    else:
        notes.append("女命官星不显，宜择性格稳重之配偶。")
    if f_guan >= 5:
        pts -= 1.5
        notes.append("女命官杀过旺，易多思多虑，配偶宜温和包容。")
    if m_cai >= 5:
        pts -= 1.5
        notes.append("男命财星过旺，感情易多枝节，宜专一守分。")
    total += _add(sec, "五、夫妻星（财官）", notes, max(0, min(8, pts)), 8)

    # 6 夫妻宫生扶
    m_day_wx, f_day_wx = C.GAN_WUXING[mg], C.GAN_WUXING[fg]
    rel2 = _relation(m_day_wx, f_day_wx)
    pts = {"相生": 8, "比和": 6, "被克": 3, "相克": 2}[rel2]
    total += _add(sec, "六、日主生扶", [
        f"男日主 {mg}{m_day_wx}　女日主 {fg}{f_day_wx}　关系：{rel2}",
        {"相生": "日主相生，彼此扶持，男主外女主内皆宜。",
         "比和": "日主比和，性情相近，然须防争强好胜。",
         "相克": "日主相克，男主女从或女强男弱之象，宜以柔济刚，忌各执一词。",
         "被克": "女命克男命，宜男主内敛、女多体谅，方得长久。",
         }[rel2] + "（《滴天髓》论日主配合）",
    ], pts, 8)

    # 7 紫微夫妻宫对照
    pts, notes = _ziwei_pair(male, female)
    total += _add(sec, "七、紫微夫妻宫", notes, pts, 9)

    # 8 婚期机缘
    pts, notes = _wedding_years(male, female)
    total += _add(sec, "八、婚期机缘", notes, pts, 5)

    score = int(round(total))
    grade = ("上上婚（天作之合）" if score >= 85 else
             "上婚（和美之配）" if score >= 70 else
             "中婚（可成之配）" if score >= 55 else
             "下婚（须多包容）" if score >= 40 else
             "不宜（冲克较重）")

    advice = []
    worst = min(sec, key=lambda s: s[2] / s[3])
    if worst[2] / worst[3] < 0.6:
        advice.append(f"八项之中「{worst[0].split('、')[-1]}」一项偏弱（{worst[2]}/{worst[3]}），"
                      "为本次合婚主要着力处。")
    if score < 70:
        advice.append("婚配之吉凶，古法重在「日柱相配」与「五行互补」，生肖属相仅为佐参，不宜独断。")
    advice.append("若欲化解冲克，传统以择吉日成婚、择合宜方位居处、双方长辈属相回避等方式调和。")
    advice.append("《三命通会》云：「男女生年纳音相生为上，比和次之」；然命理之说，仅供参考。")
    return HunResult(score=score, grade=grade, sections=sec, advice=advice)


def _ziwei_pair(male: Chart, female: Chart) -> tuple[float, list[str]]:
    """双方紫微命宫、夫妻宫星曜对照。"""
    notes: list[str] = []
    try:
        mz = zw.build(male.used, "男")
        fz = zw.build(female.used, "女")
    except Exception as exc:                      # 安星失败时退化为中性分
        return 4.5, [f"紫微安星未能完成（{exc}），此节按中性计。"]
    mp, fp = mz.soul_palace, fz.soul_palace
    mc = next(p for p in mz.palaces if p.name == "夫妻")
    fc = next(p for p in fz.palaces if p.name == "夫妻")
    mstar = mp.major[0] if mp.major else ""
    fstar = fp.major[0] if fp.major else ""
    pts = 4.5
    if mstar and fstar:
        r = _relation(C.STAR_WX.get(mstar, "土"), C.STAR_WX.get(fstar, "土"))
        pts += {"相生": 1.5, "比和": 1.0, "被克": 0.0, "相克": -1.0}[r]
        notes.append(f"男命宫{mstar}（{zw.bright_of(mstar, mp.zhi)}）　女命宫{fstar}"
                     f"（{zw.bright_of(fstar, fp.zhi)}）　星性关系：{r}")
    else:
        notes.append("一方命宫无主星（空宫），以对宫借星参看，力量减半。")
    ms = [s for s in mc.major if s in zw.STAR_MEANING]
    fs = [s for s in fc.major if s in zw.STAR_MEANING]
    if ms and fs:
        r2 = _relation(C.STAR_WX.get(ms[0], "土"), C.STAR_WX.get(fs[0], "土"))
        pts += {"相生": 1.5, "比和": 1.0, "被克": 0.0, "相克": -1.0}[r2]
        notes.append(f"男夫妻宫{ms[0]}（{zw.bright_of(ms[0], mc.zhi)}）　女夫妻宫{fs[0]}"
                     f"（{zw.bright_of(fs[0], fc.zhi)}）　关系：{r2}——"
                     + {"相生": "彼此体谅，婚后渐入佳境。", "比和": "性格相近，宜各留空间。",
                        "被克": "相处需多迁就，忌冷处理。", "相克": "意见易相左，宜约法三章。"}[r2])
    elif not ms or not fs:
        notes.append("夫妻宫见空宫，主配偶缘分须经人事方定，忌早婚急就。")
    lucky = [x for x in (mc.minor + fc.minor) if x in zw.LUCKY]
    evil = [x for x in (mc.minor + fc.minor) if x in zw.EVIL]
    if lucky:
        pts += min(1.5, 0.5 * len(lucky))
        notes.append("夫妻宫吉曜（两方合计）：" + "、".join(dict.fromkeys(lucky)) + "，主配偶得助、家道和顺。")
    if evil:
        pts -= min(1.5, 0.5 * len(evil))
        notes.append("夫妻宫煞曜（两方合计）：" + "、".join(dict.fromkeys(evil)) + "，宜迟婚、宜多沟通化解。")
    return max(0.0, min(9.0, pts)), notes


def _wedding_years(male: Chart, female: Chart) -> tuple[float, list[str]]:
    """未来六年中，流年支与双方日支六合者利成婚，逢冲者不利。"""
    now = datetime.now().year
    mdz, fdz = male.pillars[2].zhi, female.pillars[2].zhi
    he_pairs = {frozenset(p) for p in C.LIUHE}
    chong_pairs = {frozenset(p) for p in C.LIUCHONG}
    good, bad = [], []
    for y in range(now, now + 6):
        gz = liunian_of(male, None, y)
        z = gz[1]
        he, chong = [], []
        for dz, who in ((mdz, "男方"), (fdz, "女方")):
            if frozenset((z, dz)) in he_pairs:
                he.append(f"{z}与{who}日支{dz}六合")
            elif frozenset((z, dz)) in chong_pairs:
                chong.append(f"{z}冲{who}日支{dz}")
        if he and chong:
            bad.append(f"{y} {gz}：" + "、".join(he) + "，然" + "、".join(chong)
                       + "，吉凶相参，宜择月避冲。")
        elif he:
            good.append(f"{y} {gz}：" + "、".join(he) + "，宜议婚成礼。")
        elif chong:
            bad.append(f"{y} {gz}：" + "、".join(chong) + "，此年宜缓议、忌仓促。")
    pts = 3.0 + min(1.5, 0.5 * len(good))
    if bad:
        pts -= 0.5
    notes = good[:3] or ["近六年未见流年合夫妻宫之期，可待流年财官得力之年再议。"]
    if bad:
        notes += bad[:2]
    notes.append("择期尚须避双方本命年及父母忌月，并合通书吉日；"
                 "《增删卜易》以「用神得地、世应相生」为成事之期。")
    return max(0.0, min(5.0, pts)), notes


def render(result: HunResult, male: Chart, female: Chart) -> str:
    mb = male.hour_label or f"{male.birth:%Y-%m-%d %H:%M}"
    fb = female.hour_label or f"{female.birth:%Y-%m-%d %H:%M}"
    L = [f"【八字合婚】{male.name or '男方'}（{male.gender}）　与　{female.name or '女方'}（{female.gender}）",
         f"　　男：{mb}　{''.join(p.gz for p in male.pillars)}",
         f"　　女：{fb}　{''.join(p.gz for p in female.pillars)}",
         "", f"　　【合婚得分】{result.score} 分　—— {result.grade}", ""]
    for title, lines, pts, full in result.sections:
        L.append(f"　{title}（{pts}/{full}）")
        for ln in lines:
            if ln:
                L.append(f"　　{ln}")
        L.append("")
    L.append("　【合婚要义】")
    for a in result.advice:
        L.append(f"　　· {a}")
    return "\n".join(L)
