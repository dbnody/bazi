# -*- coding: utf-8 -*-
"""自检用例：python tests/test_core.py（无需 pytest）.

校验点均为可独立复核的天文/历法事实与经典排盘结论。
"""
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bazi import biorhythm, calendar_core as cc, chart as cht, chengku, hehun

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

print(f"全部通过：{N} 项")
