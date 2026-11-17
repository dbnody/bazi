# -*- coding: utf-8 -*-
"""八字合婚（婚配）.

学理依据:
  《三命通会·论纳音合婚》—— 年命纳音相生相克
  《渊海子平·论婚姻》    —— 日柱、财官、夫妻宫
  《玉照定真经》          —— 生肖六合三合、刑冲害
评分权重（本程序设定，总计 100）:
  年命纳音 15 · 生肖合冲 15 · 日柱干支 25 · 五行互补 25 · 夫妻星 10 · 夫妻宫 10
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import constants as C
from .chart import Chart, SHENG, KE, shishen


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
    pts = {"相生": 15, "比和": 11, "被克": 7, "相克": 4}[rel]
    total += _add(sec, "一、年命纳音", [
        f"男命 {male.pillars[0].gz}　纳音{male.pillars[0].nayin}（{mw}）",
        f"女命 {female.pillars[0].gz}　纳音{female.pillars[0].nayin}（{fw}）",
        f"关系：{rel}　《三命通会》云：纳音相生主和睦，比和亦吉；相克则防口舌刑伤。",
        f"{'男命生女命，主男方多付出而和顺。' if rel == '相生' and SHENG[mw] == fw else ''}"
        f"{'女命生男命，主女方助夫得力。' if rel == '相生' and SHENG[fw] == mw else ''}"
        f"{'相克者，宜以婚期、居所方位调和。' if rel in ('相克', '被克') else ''}".rstrip(),
    ], pts, 15)

    # 2 生肖
    mz, fz = male.pillars[0].zhi, female.pillars[0].zhi
    zrel, zsign = _zhi_relation(mz, fz)
    pts = {"六合": 15, "三合": 13}.get(zrel, 8 if zrel == "无特殊关系" else 4)
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
    ], pts, 15)

    # 3 日柱
    mg, fg = male.pillars[2].gan, female.pillars[2].gan
    mdz, fdz = male.pillars[2].zhi, female.pillars[2].zhi
    grel, gsign = _gan_relation(mg, fg)
    drel, dsign = _zhi_relation(mdz, fdz)
    pts = 12.5
    pts += 8 if gsign == "＋" else (0 if gsign == "○" else -8)
    pts += 8 if dsign == "＋" else (0 if dsign == "○" else -8)
    pts = max(0, min(25, pts))
    total += _add(sec, "三、日柱（夫妻宫）", [
        f"男命日柱 {male.pillars[2].gz}　女命日柱 {female.pillars[2].gz}",
        f"天干：{mg}{C.GAN_WUXING[mg]} 与 {fg}{C.GAN_WUXING[fg]} —— {grel}",
        f"地支：{mdz} 与 {fdz} —— {drel}",
        "《渊海子平》：日干为夫/妻之本体，日支为夫妻宫；干合支合者，情偕意合；",
        "干支俱冲者，聚少离多；夫妻宫伏吟者，易见迟婚或再婚之象。",
    ], pts, 25)

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
    pts = max(0, min(25, 12.5 + gain))
    total += _add(sec, "四、五行互补", notes or ["双方五行分布均衡，无明显互补或冲激。"], pts, 25)

    # 5 夫妻星
    mss, fss = shishen_counts(male), shishen_counts(female)
    m_cai = mss.get("正财", 0) + mss.get("偏财", 0)
    f_guan = fss.get("正官", 0) + fss.get("七杀", 0)
    pts, notes = 5.0, []
    if m_cai:
        pts += 2.5
        notes.append(f"男命财星 {m_cai} 见（财为妻星），妻缘分明。")
    else:
        notes.append("男命财星不显，感情宜主动经营，忌过于理性。")
    if f_guan:
        pts += 2.5
        notes.append(f"女命官杀 {f_guan} 见（官为夫星），夫缘有靠。")
    else:
        notes.append("女命官星不显，宜择性格稳重之配偶。")
    if f_guan >= 5:
        pts -= 1.5
        notes.append("女命官杀过旺，易多思多虑，配偶宜温和包容。")
    if m_cai >= 5:
        pts -= 1.5
        notes.append("男命财星过旺，感情易多枝节，宜专一守分。")
    total += _add(sec, "五、夫妻星（财官）", notes, max(0, min(10, pts)), 10)

    # 6 夫妻宫生扶
    m_day_wx, f_day_wx = C.GAN_WUXING[mg], C.GAN_WUXING[fg]
    rel2 = _relation(m_day_wx, f_day_wx)
    pts = {"相生": 10, "比和": 7, "被克": 4, "相克": 2}[rel2]
    total += _add(sec, "六、日主生扶", [
        f"男日主 {mg}{m_day_wx}　女日主 {fg}{f_day_wx}　关系：{rel2}",
        {"相生": "日主相生，彼此扶持，男主外女主内皆宜。",
         "比和": "日主比和，性情相近，然须防争强好胜。",
         "相克": "日主相克，男主女从或女强男弱之象，宜以柔济刚，忌各执一词。",
         "被克": "女命克男命，宜男主内敛、女多体谅，方得长久。",
         }[rel2] + "（《滴天髓》论日主配合）",
    ], pts, 10)

    score = int(round(total))
    grade = ("上上婚（天作之合）" if score >= 85 else
             "上婚（和美之配）" if score >= 70 else
             "中婚（可成之配）" if score >= 55 else
             "下婚（须多包容）" if score >= 40 else
             "不宜（冲克较重）")

    advice = []
    if score < 70:
        advice.append("婚配之吉凶，古法重在「日柱相配」与「五行互补」，生肖属相仅为佐参，不宜独断。")
    advice.append("若欲化解冲克，传统以择吉日成婚、择合宜方位居处、双方长辈属相回避等方式调和。")
    advice.append("《三命通会》云：「男女生年纳音相生为上，比和次之」；然命理之说，仅供参考。")
    return HunResult(score=score, grade=grade, sections=sec, advice=advice)


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
