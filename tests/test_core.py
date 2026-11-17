# -*- coding: utf-8 -*-
"""自检用例：python tests/test_core.py（无需 pytest）.

校验点均为可独立复核的天文/历法事实与经典排盘结论。
"""
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bazi import (biorhythm, calendar_core as cc, chart as cht, chengku, hehun,
                  liuyao, ziwei)

N = 0


def check(name, got, want):
    global N
    N += 1
    assert got == want, f"{name}: 期望 {want!r}，实得 {got!r}"


def gz(dt, gender="男", **kw):
    ch = cht.build_chart("", gender, dt, **kw)
    return "".join(p.gz for p in ch.pillars)


# ---- 历法：农历、干支、节气 -------------------------------------------------
check("1990-05-12 农历", cc.day_info(1990, 5, 12).lunar_date_cn, "一九九〇年四月十八")
check("2026-11-16 农历", cc.day_info(2026, 11, 16).lunar_date_cn, "二〇二六年十月初八")
check("2026-11-16 日柱", cc.day_info(2026, 11, 16).gz_day, "甲午")
check("2026-11-16 月柱", cc.day_info(2026, 11, 16).gz_month, "己亥")
check("2026 立春时刻", f"{cc.lichun_time(2026):%Y-%m-%d %H:%M}", "2026-02-04 04:02")
check("2026-11 节气数", len(cc.jieqi_of_month(2026, 11)), 2)
check("月历网格", (len(cc.month_grid(2026, 11)), len(cc.month_grid(2026, 11)[0])), (6, 7))
check("闰月转换", __import__("lunar_python").Lunar.fromYmd(2020, -4, 1).getSolar().toYmd(), "2020-05-23")

# ---- 四柱：节气分界（立春换年、交节换月） -----------------------------------
check("立春前", gz(datetime(1985, 2, 3, 12, 0))[:2], "甲子")
check("立春后", gz(datetime(1985, 2, 10, 12, 0))[:2], "乙丑")
check("立冬前一时辰(戌月)", gz(datetime(2026, 11, 7, 17, 0))[2:4], "戊戌")
check("立冬后一时辰(亥月)", gz(datetime(2026, 11, 7, 18, 0))[2:4], "己亥")
check("示例四柱", gz(datetime(1990, 5, 12, 14, 30)), "庚午辛巳丁丑丁未")
check("晚子时日柱算当日", gz(datetime(1990, 5, 12, 23, 30))[4:6], "丁丑")
check("次日凌晨即换日", gz(datetime(1990, 5, 13, 0, 30))[4:6], "戊寅")

# ---- 时辰不详：三柱排盘 -----------------------------------------------------
ch_nh = cht.build_chart("", "男", datetime(1990, 5, 12, 14, 30), hour_known=False)
check("时辰不详时柱留空", [p.gz for p in ch_nh.pillars], ["庚午", "辛巳", "丁丑", ""])
check("时辰不详标记", ch_nh.pillars[3].unknown, True)
check("时辰不详五行不含时柱", ch_nh.wuxing_count["土"], 1)
check("时辰不详神煞不含时柱", "时" in ch_nh.shensha, False)
check("时辰不详表内显示—", "—" in cht.render_chart(ch_nh).split("时辰不详：")[0], True)
check("时辰不详仍排大运", ch_nh.dayun[0].gan_zhi, "壬午")
r_nh = chengku.calc(datetime(1990, 5, 12, 14, 30), "男", hour_known=False)
check("三柱骨重", (r_nh["total"], r_nh["weight_text"]), (36, "三两六钱"))
check("三柱区间上限", r_nh["total"] + max(chengku.HOUR_WEIGHT.values()), 52)

# ---- 只知时辰：取中点，时辰序号可复原 --------------------------------------
check("时辰中点", cc.SHICHEN_MID_HOUR[:3] + [cc.SHICHEN_MID_HOUR[11]], [0, 2, 4, 22])
check("中点回推时辰", [cc.shichen_index(datetime(2000, 1, 1, h)) for h in cc.SHICHEN_MID_HOUR],
      list(range(12)))
ch_sc = cht.build_chart("", "男", datetime(1990, 5, 12, 8, 0), hour_label="1990-05-12 辰时")
check("时辰推定四柱", [p.gz for p in ch_sc.pillars], ["庚午", "辛巳", "丁丑", "甲辰"])
r_sc = chengku.calc(datetime(1990, 5, 12, 8, 0), "男", hour_label="1990-05-12 辰时")
check("时辰推定骨重", (r_sc["total"], r_sc["weight_text"]), (45, "四两五钱"))
check("时辰推定标题", "辰时" in chengku.render(r_sc).splitlines()[0], True)

# ---- 真太阳时 ---------------------------------------------------------------
tst, off = cc.true_solar_time(datetime(1990, 5, 12, 14, 30), 116.41)
check("真太阳时", f"{tst:%H:%M}", "14:19")
check("校正分钟(约)", round(off, 0), -10.0)

# ---- 旺衰 / 格局 / 大运 -----------------------------------------------------
ch = cht.build_chart("张三", "男", datetime(1990, 5, 12, 14, 30))
check("旺衰", ch.strength_text, "身强（旺）")
check("生肖", ch.shengxiao, "马")
check("大运顺逆(阳年男)", ch.forward, True)
check("首运干支", ch.dayun[0].gan_zhi, "壬午")
ch_f = cht.build_chart("", "女", datetime(1990, 5, 12, 14, 30))
check("大运顺逆(阳年女)", ch_f.forward, False)
check("神煞含桃花", "桃花" in ch.shensha["年"], True)

# ---- 称骨 -------------------------------------------------------------------
r = chengku.calc(datetime(1990, 5, 12, 14, 30), "男")
check("骨重(钱)", r["total"], 44)
check("骨重文", r["weight_text"], "四两四钱")
check("歌诀首句", r["poem"].split("，")[0], "万事由天莫苦求")
check("骨重范围", all(21 <= chengku.calc(datetime(y, 6, 15, 10, 0))["total"] <= 71
                      for y in range(1950, 2001, 5)), True)
check("骨重分布总数", sum(chengku.distribution().values()), chengku.TOTAL_COMBOS)
check("同骨重占比", round(r["pct"], 2), 3.52)

# ---- 合婚 -------------------------------------------------------------------
male = cht.build_chart("男", "男", datetime(1990, 5, 12, 14, 30))
female = cht.build_chart("女", "女", datetime(1992, 8, 3, 9, 15))
res = hehun.hehun(male, female)
check("合婚分数区间", 0 <= res.score <= 100, True)
check("合婚分项数", len(res.sections), 6)
check("合婚满分", sum(s[3] for s in res.sections), 100)

# ---- 生物钟 -----------------------------------------------------------------
b = datetime(1990, 5, 12, 14, 30)
check("出生日全为临界", {p.phase for p in biorhythm.at(b, b)}, {biorhythm.CRIT})
check("四分之一周期=+100%",
      round(biorhythm.value(b, b + timedelta(days=23 / 4), 23), 6), 100.0)
vals = biorhythm.series(b, b, 30)
check("序列周期数(默认7)", len([k for k in vals if k != "__dates__"]), 7)
check("序列天数", len(vals["__dates__"]), 30)
check("经典三节律", [p.period for p in biorhythm.at(b, b, 3)], [23, 28, 33])
check("七节律周期", [p for _, p, *_ in biorhythm.CYCLES], [23, 28, 33, 38, 43, 48, 53])

# ---- 紫微斗数 ---------------------------------------------------------------
# 定紫微星诀：六五四三二，酉午亥辰丑（初一之紫微）
check("紫微 水二局初一", ziwei.ZHI[ziwei.ziwei_index(1, 2)], "丑")
check("紫微 木三局初一", ziwei.ZHI[ziwei.ziwei_index(1, 3)], "辰")
check("紫微 金四局初一", ziwei.ZHI[ziwei.ziwei_index(1, 4)], "亥")
check("紫微 土五局初一", ziwei.ZHI[ziwei.ziwei_index(1, 5)], "午")
check("紫微 火六局初一", ziwei.ZHI[ziwei.ziwei_index(1, 6)], "酉")
# 全书三例：27日木三局→戌；13日火六局→亥；6日土五局→未
check("紫微 27日木三局", ziwei.ZHI[ziwei.ziwei_index(27, 3)], "戌")
check("紫微 13日火六局", ziwei.ZHI[ziwei.ziwei_index(13, 6)], "亥")
check("紫微 6日土五局", ziwei.ZHI[ziwei.ziwei_index(6, 5)], "未")

zw1 = ziwei.build(datetime(1990, 5, 12, 14, 30), "男")
check("紫微 年干支", zw1.year_gz, "庚午")
check("紫微 农历时支", zw1.time_zhi, "未")
check("紫微 命宫", zw1.palaces[zw1.soul_idx].zhi, "戌")
check("紫微 命宫干支", zw1.palaces[zw1.soul_idx].gz, "丙戌")
check("紫微 身宫", zw1.palaces[zw1.body_idx].zhi, "子")
check("紫微 五行局", zw1.bureau_name, "土五局")
check("紫微 紫微所在", ziwei.ZHI[zw1.ziwei_idx], "未")
check("紫微 天府所在", ziwei.ZHI[zw1.tianfu_idx], "酉")
check("紫微 命主", zw1.ming_zhu, "禄存")
check("紫微 身主", zw1.shen_zhu, "火星")
check("紫微 大限顺逆", zw1.forward, True)
check("紫微 起运岁", zw1.palaces[zw1.soul_idx].decade, (5, 14))
check("紫微 十二宫次宫", zw1.palaces[(zw1.soul_idx + 1) % 12].name, "父母")
check("紫微 十二宫末宫", zw1.palaces[(zw1.soul_idx - 1) % 12].name, "兄弟")
check("紫微 命宫主星", zw1.palaces[zw1.soul_idx].major, ["太阴"])
_ziwei_group = {"紫微", "天机", "太阳", "武曲", "天同", "廉贞"}
_tianfu_group = {"天府", "太阴", "贪狼", "巨门", "天相", "天梁", "七杀", "破军"}
check("紫微 十四主星齐备", {s for p in zw1.palaces for s in p.major}, _ziwei_group | _tianfu_group)
check("紫微 主星不重", sum(len(p.major) for p in zw1.palaces), 14)
check("紫微 生年四化", ziwei.SIHUA["庚"], ("太阳", "武曲", "太阴", "天同"))
check("紫微 阴女逆行", ziwei.build(datetime(1990, 5, 12, 14, 30), "女").forward, False)
check("紫微 纳音五行", ziwei.nayin_wuxing("丙戌"), "土")


def star_branch(ch, name):
    return [p.zhi for p in ch.palaces if name in p.minor]


check("紫微 孤辰在申", star_branch(zw1, "孤辰"), ["申"])
check("紫微 寡宿在辰", star_branch(zw1, "寡宿"), ["辰"])
check("紫微 截路在午", star_branch(zw1, "截路"), ["午"])
check("紫微 空亡在未", star_branch(zw1, "空亡"), ["未"])
check("紫微 命宫无禄存(庚年禄存在申)", star_branch(zw1, "禄存"), ["申"])

# 与 npm iztro（官方 JS 实现）逐项比对后固化的向量：(日期, 性别, 命宫支, 身宫支, 五行局)
for dt_s, g, soul, body, bureau in [
    ("1976-09-09 23:30", "男", "酉", "酉", "火六局"),   # 晚子时作次日子时
    ("2020-05-23 10:15", "男", "子", "戌", "火六局"),   # 闰四月
    ("2000-01-01 00:30", "女", "子", "子", "水二局"),
    ("1999-12-31 03:10", "女", "戌", "寅", "火六局"),
    ("1955-04-20 16:20", "女", "申", "子", "水二局"),
    ("2012-06-15 08:40", "男", "寅", "戌", "金四局"),
    ("2004-02-29 06:30", "女", "子", "午", "水二局"),
]:
    c = ziwei.build(datetime.strptime(dt_s, "%Y-%m-%d %H:%M"), g)
    check(f"紫微 iztro 向量 {dt_s}", (ziwei.ZHI[c.soul_idx], ziwei.ZHI[c.body_idx], c.bureau_name),
          (soul, body, bureau))

# ---- 六爻 -------------------------------------------------------------------
QIAN = liuyao.GUAS[(1,) * 6]
check("六爻 乾为天宫位", (QIAN.name, QIAN.palace, QIAN.shi, QIAN.ying), ("乾为天", "乾", 6, 3))
check("六爻 乾纳甲", QIAN.na, ("甲子", "甲寅", "甲辰", "壬午", "壬申", "壬戌"))
check("六爻 乾初爻六亲", liuyao.liuqin("金", "水"), "子孙")
check("六爻 乾二爻六亲", liuyao.liuqin("金", "木"), "妻财")
check("六爻 乾三爻六亲", liuyao.liuqin("金", "土"), "父母")
check("六爻 乾四爻六亲", liuyao.liuqin("金", "火"), "官鬼")
check("六爻 乾五爻六亲", liuyao.liuqin("金", "金"), "兄弟")
check("六爻 八宫卦数", len(liuyao.GUAS), 64)
check("六爻 乾为天六冲", liuyao._is_liuchong(QIAN), True)
check("六爻 天地否六合", liuyao._is_liuhe(liuyao.GUAS[(0, 0, 0, 1, 1, 1)]), True)
jin = liuyao.GUAS[(0, 0, 0, 1, 0, 1)]
check("六爻 火地晋", (jin.name, jin.palace, jin.kind, jin.shi, jin.ying),
      ("火地晋", "乾", "游魂", 4, 1))
shi_gua = liuyao.GUAS[(0, 1, 0, 0, 0, 0)]
check("六爻 地水师", (shi_gua.name, shi_gua.palace, shi_gua.kind, shi_gua.shi),
      ("地水师", "坎", "归魂", 3))
check("六爻 六神甲日起青龙", liuyao.liushen_of_day("甲")[0], "青龙")
check("六爻 六神庚日起白虎", liuyao.liushen_of_day("庚")[0], "白虎")
check("六爻 旬空甲子日", liuyao.kong_wang("甲子"), "戌亥")
check("六爻 旺相休囚死", [liuyao.wangshuai(x, "木") for x in "木火水金土"],
      ["旺", "相", "休", "囚", "死"])
c1 = liuyao.build("手动", [9, 7, 7, 7, 7, 7], datetime(2026, 11, 17, 10, 30), "财运",
                  day_gz="乙未", month_gz="己亥", year_gz="丙午")
check("六爻 手动本卦", c1.ben.name, "乾为天")
check("六爻 手动变卦", c1.bian.name, "天风姤")
check("六爻 动爻数", sum(1 for r in c1.lines if r.dong), 1)
check("六爻 用神取财", c1.yongshen.startswith("妻财"), True)
check("六爻 六阳静卦", liuyao.build("手动", [7] * 6, datetime(2026, 11, 17, 10, 30),
                                "事业", day_gz="乙未", month_gz="己亥",
                                year_gz="丙午").bian, None)
check("六爻 摇钱取值", set(liuyao.cast_coins()) <= {6, 7, 8, 9}, True)
check("六爻 输入解析", liuyao.from_coins_text("789789"), [7, 8, 9, 7, 8, 9])
try:
    liuyao.from_coins_text("123456")
    bad = False
except ValueError:
    bad = True
check("六爻 非法输入报错", bad, True)

print(f"全部通过：{N} 项")
