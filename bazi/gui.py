# -*- coding: utf-8 -*-
"""图形界面（tkinter/ttk）：万年历 · 八字排盘 · 称骨算命 · 八字合婚 · 生物钟."""
from __future__ import annotations

import tkinter as tk
from datetime import datetime, timedelta
from tkinter import filedialog, messagebox, ttk

from lunar_python import Lunar

from . import biorhythm, calendar_core as cc, chart as cht, chengku, hehun

FONT = "Microsoft YaHei UI"
MONO = "NSimSun"
SHICHEN_UNSET = "不详"
SHICHEN_ALL = [f"{z}时" for z in cc.SHICHEN]

CITIES = [
    ("北京", 116.41), ("上海", 121.47), ("天津", 117.20), ("重庆", 106.55),
    ("广州", 113.26), ("深圳", 114.06), ("杭州", 120.15), ("南京", 118.78),
    ("武汉", 114.30), ("成都", 104.07), ("西安", 108.95), ("沈阳", 123.43),
    ("哈尔滨", 126.53), ("长春", 125.32), ("济南", 117.00), ("郑州", 113.62),
    ("长沙", 112.94), ("南昌", 115.89), ("合肥", 117.28), ("福州", 119.30),
    ("厦门", 118.09), ("昆明", 102.71), ("贵阳", 106.63), ("南宁", 108.37),
    ("海口", 110.20), ("兰州", 103.83), ("西宁", 101.78), ("银川", 106.23),
    ("乌鲁木齐", 87.62), ("拉萨", 91.14), ("呼和浩特", 111.75), ("太原", 112.55),
    ("石家庄", 114.51), ("青岛", 120.38), ("大连", 121.62), ("苏州", 120.62),
    ("宁波", 121.55), ("无锡", 120.30), ("温州", 120.70), ("东莞", 113.75),
    ("佛山", 113.12), ("珠海", 113.58), ("三亚", 109.51), ("丽江", 100.23),
    ("喀什", 75.99), ("香港", 114.17), ("澳门", 113.54), ("台北", 121.52),
]
CITY_MAP = dict(CITIES)


class DateInput(ttk.Frame):
    """公历/农历日期时间输入。"""

    def __init__(self, master, default: datetime | None = None, allow_lunar: bool = True,
                 allow_unknown_hour: bool = False):
        super().__init__(master)
        d = default or datetime.now().replace(second=0, microsecond=0)
        self.allow_lunar = allow_lunar
        self.allow_unknown_hour = allow_unknown_hour
        self.v_year = tk.StringVar(value=str(d.year))
        self.v_month = tk.StringVar(value=str(d.month))
        self.v_day = tk.StringVar(value=str(d.day))
        self.v_hour = tk.StringVar(value=str(d.hour))
        self.v_min = tk.StringVar(value=str(d.minute))
        self.v_lunar = tk.BooleanVar(value=False)
        self.v_leap = tk.BooleanVar(value=False)
        self.v_nohour = tk.BooleanVar(value=False)

        ttk.Spinbox(self, from_=1901, to=2100, width=6, textvariable=self.v_year).grid(row=0, column=0)
        ttk.Label(self, text="年").grid(row=0, column=1, padx=(1, 6))
        ttk.Spinbox(self, from_=1, to=12, width=3, textvariable=self.v_month).grid(row=0, column=2)
        ttk.Label(self, text="月").grid(row=0, column=3, padx=(1, 6))
        ttk.Spinbox(self, from_=1, to=31, width=3, textvariable=self.v_day).grid(row=0, column=4)
        ttk.Label(self, text="日").grid(row=0, column=5, padx=(1, 8))
        self.sp_hour = ttk.Spinbox(self, from_=0, to=23, width=3, textvariable=self.v_hour)
        self.sp_hour.grid(row=1, column=0, sticky="w")
        ttk.Label(self, text="时").grid(row=1, column=1, padx=(1, 6), sticky="w")
        self.sp_min = ttk.Spinbox(self, from_=0, to=59, width=3, textvariable=self.v_min)
        self.sp_min.grid(row=1, column=2, sticky="w")
        ttk.Label(self, text="分").grid(row=1, column=3, padx=(1, 8), sticky="w")

        cbs = ttk.Frame(self)
        cbs.grid(row=2, column=0, columnspan=6, sticky="w", pady=(3, 0))
        if allow_lunar:
            ttk.Checkbutton(cbs, text="农历输入", variable=self.v_lunar,
                            command=self._toggle).pack(side="left")
            self.chk_leap = ttk.Checkbutton(cbs, text="闰月", variable=self.v_leap)
            self.chk_leap.pack(side="left", padx=(8, 0))
            self.chk_leap.state(["disabled"])
        if allow_unknown_hour:
            self.chk_nohour = ttk.Checkbutton(cbs, text="时辰不详", variable=self.v_nohour,
                                             command=self._toggle_hour)
            self.chk_nohour.pack(side="left", padx=(12, 0))
            self.v_shichen = tk.StringVar(value=SHICHEN_UNSET)
            self.cb_shichen = ttk.Combobox(cbs, textvariable=self.v_shichen, width=6,
                                           state="readonly", values=[SHICHEN_UNSET] + SHICHEN_ALL)

    def _toggle_hour(self):
        st = ["disabled"] if self.v_nohour.get() else ["!disabled"]
        self.sp_hour.state(st)
        self.sp_min.state(st)
        if not self.allow_unknown_hour:
            return
        if self.v_nohour.get():
            self.cb_shichen.pack(side="left", padx=(6, 0))
        else:
            self.v_shichen.set(SHICHEN_UNSET)
            self.cb_shichen.pack_forget()

    @property
    def mode(self) -> str:
        """exact=精确到分；shichen=只知时辰；unknown=时辰完全不详。"""
        if not (self.allow_unknown_hour and self.v_nohour.get()):
            return "exact"
        return "unknown" if self.v_shichen.get() == SHICHEN_UNSET else "shichen"

    @property
    def hour_known(self) -> bool:
        return self.mode != "unknown"

    @property
    def shichen_text(self) -> str:
        if self.mode != "shichen":
            return ""
        i = cc.SHICHEN.index(self.v_shichen.get()[0])
        return f"{cc.SHICHEN[i]}时（{cc.SHICHEN_RANGE[i]}）"

    def _pick_shichen_hour(self, dt: datetime) -> datetime:
        i = cc.SHICHEN.index(self.v_shichen.get()[0])
        return dt.replace(hour=cc.SHICHEN_MID_HOUR[i], minute=0)

    def _toggle(self):
        if self.v_lunar.get():
            self.chk_leap.state(["!disabled"])
        else:
            self.v_leap.set(False)
            self.chk_leap.state(["disabled"])

    def set(self, dt: datetime):
        self.v_year.set(str(dt.year))
        self.v_month.set(str(dt.month))
        self.v_day.set(str(dt.day))
        self.v_hour.set(str(dt.hour))
        self.v_min.set(str(dt.minute))
        self.v_lunar.set(False)
        self._toggle()

    def get(self) -> datetime:
        dt = self._raw_dt()
        if self.mode == "shichen":
            return self._pick_shichen_hour(dt)
        return dt

    def _raw_dt(self) -> datetime:
        try:
            y, m, d = int(self.v_year.get()), int(self.v_month.get()), int(self.v_day.get())
            h, mi = int(self.v_hour.get()), int(self.v_min.get())
        except ValueError:
            raise ValueError("日期时间须为整数")
        if not (0 <= h <= 23 and 0 <= mi <= 59):
            raise ValueError("时/分超出范围")
        if self.allow_lunar and self.v_lunar.get():
            lm = -m if self.v_leap.get() else m
            try:
                s = Lunar.fromYmdHms(y, lm, d, h, mi, 0).getSolar()
            except Exception:
                raise ValueError("农历日期无效：请检查闰月与日期")
            return datetime(s.getYear(), s.getMonth(), s.getDay(), h, mi)
        try:
            return datetime(y, m, d, h, mi)
        except ValueError:
            raise ValueError("公历日期无效")


def scrolled_text(parent, font=(MONO, 11), **kw) -> tk.Text:
    kw.setdefault("wrap", "none")
    frame = ttk.Frame(parent)
    frame.pack(fill="both", expand=True)
    txt = tk.Text(frame, font=font, undo=True, **kw)
    ys = ttk.Scrollbar(frame, orient="vertical", command=txt.yview)
    xs = ttk.Scrollbar(frame, orient="horizontal", command=txt.xview)
    txt.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
    txt.grid(row=0, column=0, sticky="nsew")
    ys.grid(row=0, column=1, sticky="ns")
    xs.grid(row=1, column=0, sticky="ew")
    frame.rowconfigure(0, weight=1)
    frame.columnconfigure(0, weight=1)
    return txt


def copy_text(root, text: str):
    root.clipboard_clear()
    root.clipboard_append(text)


# --------------------------------------------------------------------------- #
# 万年历
# --------------------------------------------------------------------------- #
class CalendarFrame(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master, padding=8)
        self.app = app
        today = datetime.now()
        self.year, self.month = today.year, today.month
        self.selected = today.date()
        self.cells = []

        bar = ttk.Frame(self)
        bar.pack(fill="x", pady=(0, 6))
        ttk.Button(bar, text="◀ 上月", command=lambda: self.shift(-1)).pack(side="left")
        self.v_year = tk.StringVar(value=str(self.year))
        ttk.Spinbox(bar, from_=1901, to=2100, width=6, textvariable=self.v_year,
                    command=self.jump).pack(side="left", padx=(8, 2))
        ttk.Label(bar, text="年").pack(side="left")
        self.v_month = tk.StringVar(value=str(self.month))
        ttk.Spinbox(bar, from_=1, to=12, width=3, textvariable=self.v_month,
                    command=self.jump).pack(side="left", padx=(6, 2))
        ttk.Label(bar, text="月").pack(side="left")
        ttk.Button(bar, text="下月 ▶", command=lambda: self.shift(1)).pack(side="left", padx=8)
        ttk.Button(bar, text="今天", command=self.today).pack(side="left")
        self.title_var = tk.StringVar()
        ttk.Label(bar, textvariable=self.title_var, font=(FONT, 11, "bold")).pack(side="left", padx=16)
        ttk.Label(bar, text="（点击日期查看通书详情）", foreground="#888").pack(side="right")

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)
        left = ttk.Frame(body)
        left.pack(side="left", fill="both", expand=True)
        right = ttk.Frame(body, width=370)
        right.pack(side="right", fill="y", padx=(8, 0))
        right.pack_propagate(False)

        head = ttk.Frame(left)
        head.pack(fill="x")
        for i, w in enumerate(["一", "二", "三", "四", "五", "六", "日"]):
            ttk.Label(head, text=w, anchor="center", font=(FONT, 10, "bold"),
                      foreground="#c0392b" if i >= 5 else "#000").grid(row=0, column=i, sticky="ew")
            head.columnconfigure(i, weight=1)

        self.grid_frame = ttk.Frame(left)
        self.grid_frame.pack(fill="both", expand=True)
        for i in range(7):
            self.grid_frame.columnconfigure(i, weight=1, uniform="day")
        for i in range(6):
            self.grid_frame.rowconfigure(i, weight=1, uniform="day")

        self.detail = scrolled_text(right, font=(FONT, 9), wrap="char", state="disabled", spacing1=1)

        self.refresh()

    def shift(self, delta: int):
        m = self.month + delta
        y = self.year + (m - 1) // 12
        m = (m - 1) % 12 + 1
        self.year, self.month = y, m
        self.v_year.set(str(y))
        self.v_month.set(str(m))
        self.refresh()

    def jump(self):
        try:
            self.year = int(self.v_year.get())
            self.month = int(self.v_month.get())
            self.refresh()
        except ValueError:
            pass

    def today(self):
        now = datetime.now()
        self.year, self.month = now.year, now.month
        self.v_year.set(str(self.year))
        self.v_month.set(str(self.month))
        self.selected = now.date()
        self.refresh()

    def refresh(self):
        for w in self.grid_frame.winfo_children():
            w.destroy()
        weeks = cc.month_grid(self.year, self.month)
        jq = cc.jieqi_of_month(self.year, self.month)
        mid = weeks[2][3]
        self.title_var.set(
            f"{self.year}年{self.month}月　{mid.gz_year}年 {mid.gz_month}月　" +
            "　".join(f"{k} {v[5:]}" for k, v in jq.items()))
        today = datetime.now().date()
        self.cells = []
        for r, row in enumerate(weeks):
            for c, info in enumerate(row):
                cell = self._make_cell(info, info.year == self.year and info.month == self.month,
                                       datetime(info.year, info.month, info.day).date() == today)
                cell.grid(row=r, column=c, sticky="nsew", padx=1, pady=1)
                self.cells.append(cell)
        self.show_detail(self.selected)

    def _make_cell(self, info, in_month: bool, is_today: bool):
        d = datetime(info.year, info.month, info.day).date()
        bg = "#fff8e1" if is_today else ("#ffffff" if in_month else "#f4f4f4")
        if d == self.selected:
            bg = "#d6e4ff"
        f = tk.Frame(self.grid_frame, bg=bg, highlightthickness=1,
                     highlightbackground="#c8c8c8", cursor="hand2")
        f.pack_propagate(True)
        fg = "#000000" if in_month else "#9a9a9a"
        top = tk.Frame(f, bg=bg)
        top.pack(fill="x", padx=4, pady=(3, 0))
        num_fg = "#c0392b" if info.weekday in (5, 6) else fg
        tk.Label(top, text=str(info.day), bg=bg, fg=num_fg,
                 font=(FONT, 11, "bold")).pack(side="left")
        tk.Label(top, text=info.gz_day, bg=bg, fg="#999999",
                 font=(FONT, 8)).pack(side="right")

        if info.jieqi:
            mid_txt, mid_fg = info.jieqi, "#c0392b"
        elif info.lunar_day_cn == "初一":
            mid_txt, mid_fg = info.lunar_month_cn + "月", "#b9770e"
        else:
            mid_txt, mid_fg = info.lunar_day_cn, fg
        tk.Label(f, text=mid_txt, bg=bg, fg=mid_fg, font=(FONT, 9),
                 anchor="w").pack(fill="x", padx=4)
        tk.Label(f, text=f"{info.zhixing} {info.xiu}宿", bg=bg, fg="#a0a0a0",
                 font=(FONT, 8), anchor="w").pack(fill="x", padx=4, pady=(0, 2))

        for w in (f, top, *f.winfo_children(), *top.winfo_children()):
            w.bind("<Button-1>", lambda e, dd=d: self.pick(dd))
        return f

    def pick(self, d):
        self.selected = d
        self.refresh()

    def show_detail(self, d):
        info = cc.day_info(d.year, d.month, d.day)
        wk = "一二三四五六日"[info.weekday]
        L = [f"{info.year}年{info.month}月{info.day}日　星期{wk}",
             f"农历 {info.lunar_date_cn}",
             f"{info.gz_year}年　{info.gz_month}月　{info.gz_day}日",
             f"节气 {info.jieqi or '—'}　值神 {info.tianshen}（{info.tianshen_luck}）",
             f"建除 {info.zhixing}　二十八宿 {info.xiu}（{info.xiu_luck}）",
             f"日纳音 {info.nayin}　九星 {info.jiuxing}",
             f"冲煞 {info.chong}　煞{info.sha}",
             f"胎神 {info.taishen}",
             f"彭祖 {info.pengzu_gan}；{info.pengzu_zhi}",
             "", "【宜】", "　" + "　".join(info.yi),
             "", "【忌】", "　" + "　".join(info.ji),
             "", "【吉神宜趋】", "　" + "　".join(info.jishen),
             "", "【凶煞宜忌】", "　" + "　".join(info.xiongsha)]
        if info.festivals or info.other_festivals:
            L += ["", "【节日】", "　" + "　".join(info.festivals + info.other_festivals)]
        if info.shujiu or info.fushu:
            L += ["", "【时令】", "　" + " ".join(x for x in (info.shujiu, info.fushu) if x)]
        L += ["", f"月相 {info.yuexiang}　星座 {info.xingzuo}",
              "", "出处：《协纪辨方书》《象吉通书》通书体系（lunar-python 历算）"]
        self.detail.configure(state="normal")
        self.detail.delete("1.0", "end")
        self.detail.insert("end", "\n".join(L))
        self.detail.configure(state="disabled")


# --------------------------------------------------------------------------- #
# 八字排盘
# --------------------------------------------------------------------------- #
class BaziFrame(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master, padding=8)
        self.app = app
        left = ttk.Frame(self, width=430)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        box = ttk.LabelFrame(left, text="出生信息", padding=8)
        box.pack(fill="x")
        ttk.Label(box, text="姓名").grid(row=0, column=0, sticky="w")
        self.name = tk.StringVar()
        ttk.Entry(box, textvariable=self.name, width=18).grid(row=0, column=1, columnspan=3, sticky="w")
        ttk.Label(box, text="性别").grid(row=1, column=0, sticky="w", pady=4)
        self.gender = tk.StringVar(value="男")
        ttk.Combobox(box, textvariable=self.gender, values=["男", "女"], width=6,
                     state="readonly").grid(row=1, column=1, sticky="w", pady=4)
        ttk.Label(box, text="出生").grid(row=2, column=0, sticky="w")
        self.date = DateInput(box, allow_lunar=True, allow_unknown_hour=True)
        self.date.grid(row=2, column=1, columnspan=3, sticky="w", pady=2)

        opt = ttk.LabelFrame(left, text="时柱校正", padding=8)
        opt.pack(fill="x", pady=8)
        self.use_tst = tk.BooleanVar(value=False)
        ttk.Checkbutton(opt, text="按真太阳时定时柱", variable=self.use_tst,
                        command=self._toggle_tst).grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(opt, text="城市").grid(row=1, column=0, sticky="w", pady=3)
        self.city = tk.StringVar(value="北京")
        cb = ttk.Combobox(opt, textvariable=self.city, values=[c for c, _ in CITIES],
                          width=10, state="readonly")
        cb.grid(row=1, column=1, sticky="w")
        cb.bind("<<ComboboxSelected>>", lambda e: self.lon.set(str(CITY_MAP[self.city.get()])))
        ttk.Label(opt, text="经度").grid(row=2, column=0, sticky="w", pady=3)
        self.lon = tk.StringVar(value="116.41")
        self.lon_entry = ttk.Entry(opt, textvariable=self.lon, width=10)
        self.lon_entry.grid(row=2, column=1, sticky="w")
        self.zi = tk.BooleanVar(value=False)
        ttk.Checkbutton(opt, text="23点后日柱算次日（晚子时换日）",
                        variable=self.zi).grid(row=3, column=0, columnspan=3, sticky="w", pady=(6, 0))
        ttk.Label(opt, text="注：日期默认公历，\n"
                            "勾「农历输入」即按农历排盘。\n"
                            "只记到时辰：勾「时辰不详」，\n"
                            "右侧下拉选辰时等，时柱精确排定。\n"
                            "全不知时辰：留「不详」，排三柱。\n"
                            "节气、农历由寿星历计算，误差<1分。",
                  foreground="#888", justify="left").grid(
            row=4, column=0, columnspan=3, sticky="w", pady=(6, 0))
        self._toggle_tst()

        btns = ttk.Frame(left)
        btns.pack(fill="x")
        ttk.Button(btns, text="排 盘", command=self.compute).pack(fill="x", pady=2)
        ttk.Button(btns, text="复制全文", command=self.copy).pack(fill="x", pady=2)
        ttk.Button(btns, text="保存为文本", command=self.save).pack(fill="x", pady=2)
        ttk.Button(btns, text="填入当前时间", command=lambda: self.date.set(datetime.now())).pack(fill="x", pady=2)
        ttk.Button(btns, text="查看称骨", command=lambda: self.app.goto_chengku(self.date.get(),
                                                                           self.gender.get())).pack(fill="x", pady=2)
        ttk.Button(btns, text="查看生物钟", command=lambda: self.app.goto_biorhythm(self.date.get())).pack(fill="x", pady=2)

        right = ttk.LabelFrame(self, text="排盘结果", padding=4)
        right.pack(side="left", fill="both", expand=True, padx=(8, 0))
        self.text = scrolled_text(right)
        self.text.configure(state="disabled")

    def _toggle_tst(self):
        if self.use_tst.get():
            self.lon_entry.state(["!disabled"])
        else:
            self.lon_entry.state(["disabled"])

    def compute(self):
        try:
            dt = self.date.get()
            lon = float(self.lon.get() or 120)
        except ValueError as e:
            messagebox.showerror("输入有误", str(e))
            return
        shichen = self.date.mode == "shichen"
        ch = cht.build_chart(self.name.get().strip(), self.gender.get(), dt,
                             use_true_solar=self.use_tst.get() and not shichen, longitude=lon,
                             sect=1 if self.zi.get() else 2,
                             hour_known=self.date.hour_known,
                             hour_label=f"{dt:%Y-%m-%d} {self.date.shichen_text}" if shichen else "")
        s = cht.render_chart(ch)
        if shichen:
            s += ("\n\n※ 出生时辰只记到「" + self.date.shichen_text + "」：古法一日十二时，"
                  "时柱只由时辰决定、与刻分无关，故四柱与逐运推断完整可用；\n"
                  "　　本盘未作真太阳时校正（时辰既已选定，再随时差挪动反失本意）。")
        self._set(s)

    def _set(self, s):
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("end", s)
        self.text.configure(state="disabled")

    def copy(self):
        copy_text(self, self.text.get("1.0", "end-1c"))

    def save(self):
        p = filedialog.asksaveasfilename(defaultextension=".txt",
                                         filetypes=[("文本", "*.txt")], initialfile="八字排盘.txt")
        if p:
            with open(p, "w", encoding="utf-8") as f:
                f.write(self.text.get("1.0", "end-1c"))
            messagebox.showinfo("已保存", p)


# --------------------------------------------------------------------------- #
# 称骨
# --------------------------------------------------------------------------- #
class ChengkuFrame(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master, padding=8)
        self.app = app
        left = ttk.Frame(self, width=430)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        box = ttk.LabelFrame(left, text="出生信息", padding=8)
        box.pack(fill="x")
        ttk.Label(box, text="性别").grid(row=0, column=0, sticky="w")
        self.gender = tk.StringVar(value="男")
        ttk.Combobox(box, textvariable=self.gender, values=["男", "女"], width=6,
                     state="readonly").grid(row=0, column=1, sticky="w")
        ttk.Label(box, text="出生").grid(row=1, column=0, sticky="w", pady=6)
        self.date = DateInput(box, allow_lunar=True, allow_unknown_hour=True)
        self.date.grid(row=1, column=1, sticky="w")
        ttk.Button(left, text="称 骨", command=self.compute).pack(fill="x", pady=8)
        ttk.Label(left, text="《袁天罡称骨》\n年干支 + 农历月 + 农历日 + 时辰，\n四柱权重相加得骨重。",
                  foreground="#666", justify="left").pack(anchor="w", pady=(0, 6))
        ttk.Label(left, text="只记到时辰：勾「时辰不详」再选时辰，\n"
                             "骨重与歌诀即可完全确定；\n"
                             "时辰全不详：留「不详」，\n"
                             "出三柱骨重与区间。",
                  foreground="#888", justify="left").pack(anchor="w")
        right = ttk.LabelFrame(self, text="结果", padding=4)
        right.pack(side="left", fill="both", expand=True, padx=(8, 0))
        self.text = scrolled_text(right)
        self.text.configure(state="disabled")
        self.compute()

    def compute(self):
        try:
            dt = self.date.get()
        except ValueError as e:
            messagebox.showerror("输入有误", str(e))
            return
        res = chengku.calc(dt, self.gender.get(), self.date.hour_known,
                           hour_label=f"{dt:%Y-%m-%d} {self.date.shichen_text}"
                           if self.date.mode == "shichen" else "")
        s = chengku.render(res)
        if self.date.mode == "shichen":
            s += ("\n　　注：时辰只记到「" + self.date.shichen_text + "」，称骨只按时辰（时支）取重，"
                  "不涉刻分，故骨重与歌诀均确定。")
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("end", s)
        self.text.configure(state="disabled")


# --------------------------------------------------------------------------- #
# 合婚
# --------------------------------------------------------------------------- #
class HehunFrame(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master, padding=8)
        self.app = app
        top = ttk.Frame(self)
        top.pack(fill="x")
        m = ttk.LabelFrame(top, text="男方", padding=8)
        m.pack(side="left", fill="x", expand=True)
        ttk.Label(m, text="姓名").grid(row=0, column=0, sticky="w")
        self.m_name = tk.StringVar()
        ttk.Entry(m, textvariable=self.m_name, width=10).grid(row=0, column=1, sticky="w")
        ttk.Label(m, text="出生").grid(row=1, column=0, sticky="w", pady=4)
        self.m_date = DateInput(m, allow_lunar=True, allow_unknown_hour=True)
        self.m_date.grid(row=1, column=1, sticky="w")

        f = ttk.LabelFrame(top, text="女方", padding=8)
        f.pack(side="left", fill="x", expand=True, padx=8)
        ttk.Label(f, text="姓名").grid(row=0, column=0, sticky="w")
        self.f_name = tk.StringVar()
        ttk.Entry(f, textvariable=self.f_name, width=10).grid(row=0, column=1, sticky="w")
        ttk.Label(f, text="出生").grid(row=1, column=0, sticky="w", pady=4)
        self.f_date = DateInput(f, allow_lunar=True, allow_unknown_hour=True)
        self.f_date.grid(row=1, column=1, sticky="w")

        ttk.Button(self, text="合 婚 测 算", command=self.compute).pack(pady=8)
        box = ttk.LabelFrame(self, text="合婚结果", padding=4)
        box.pack(fill="both", expand=True)
        self.text = scrolled_text(box)
        self.text.configure(state="disabled")

    def compute(self):
        try:
            md, fd = self.m_date.get(), self.f_date.get()
        except ValueError as e:
            messagebox.showerror("输入有误", str(e))
            return
        male = cht.build_chart(self.m_name.get().strip(), "男", md,
                                hour_known=self.m_date.hour_known,
                                hour_label=f"{md:%Y-%m-%d} {self.m_date.shichen_text}"
                                if self.m_date.mode == "shichen" else "")
        female = cht.build_chart(self.f_name.get().strip(), "女", fd,
                                  hour_known=self.f_date.hour_known,
                                  hour_label=f"{fd:%Y-%m-%d} {self.f_date.shichen_text}"
                                  if self.f_date.mode == "shichen" else "")
        res = hehun.hehun(male, female)
        s = hehun.render(res, male, female)
        for lab, d in (("男方", self.m_date), ("女方", self.f_date)):
            if d.mode == "shichen":
                s += f"\n　※ {lab}时辰按「{d.shichen_text}」推定，时柱确定，合婚各项均按此断。"
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("end", s)
        self.text.configure(state="disabled")


# --------------------------------------------------------------------------- #
# 生物钟
# --------------------------------------------------------------------------- #
COLORS = ["#e74c3c", "#2980b9", "#27ae60", "#e67e22", "#8e44ad", "#16a085", "#8d6e63"]


class BiorhythmFrame(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master, padding=8)
        self.app = app
        bar = ttk.Frame(self)
        bar.pack(fill="x")
        ttk.Label(bar, text="出生：").grid(row=0, column=0, sticky="nw", pady=(4, 0))
        self.birth = DateInput(bar, allow_lunar=True, allow_unknown_hour=True)
        self.birth.grid(row=0, column=1, sticky="w")
        ttk.Label(bar, text="　测算日：").grid(row=0, column=2, sticky="nw", pady=(4, 0))
        self.target = DateInput(bar)
        self.target.grid(row=0, column=3, sticky="w")
        ttk.Label(bar, text="　版本　").grid(row=1, column=0, sticky="w", pady=6)
        self.profile = tk.StringVar(value="七节律（完整七种）")
        ttk.Combobox(bar, textvariable=self.profile, values=list(biorhythm.PROFILES),
                     width=26, state="readonly").grid(row=1, column=1, sticky="w", pady=6)
        ttk.Label(bar, text="天数").grid(row=1, column=2, sticky="e", padx=(0, 4))
        self.days = tk.StringVar(value="30")
        ttk.Spinbox(bar, from_=7, to=90, width=5, textvariable=self.days).grid(row=1, column=3, sticky="w")
        ttk.Button(bar, text="计 算", command=self.compute).grid(row=1, column=4, padx=8)
        ttk.Button(bar, text="今天", command=self.set_today).grid(row=1, column=5)
        ttk.Button(bar, text="导出文本", command=self.export).grid(row=1, column=6, padx=8)

        self.canvas = tk.Canvas(self, bg="white", height=240, highlightthickness=1,
                                highlightbackground="#cccccc")
        self.canvas.pack(fill="both", expand=True, pady=8)
        self.canvas.bind("<Configure>", lambda e: self.draw())

        bottom = ttk.Frame(self)
        bottom.pack(fill="x")
        self.text = scrolled_text(bottom, font=(MONO, 10), height=11)
        self.text.configure(state="disabled")
        self._series = None
        self.after(200, self.compute)

    def set_today(self):
        self.target.set(datetime.now())
        self.compute()

    def compute(self):
        try:
            birth, target = self.birth.get(), self.target.get()
            days = max(7, min(90, int(self.days.get())))
        except ValueError as e:
            messagebox.showerror("输入有误", str(e))
            return
        mode = self.birth.mode
        if mode == "unknown":           # 时辰完全不详：按当日 12:00 起算
            birth = birth.replace(hour=12, minute=0)
        if target < birth:
            messagebox.showerror("输入有误", "测算日不能早于出生日")
            return
        count = biorhythm.PROFILES[self.profile.get()]
        self._birth, self._target, self._days, self._count = birth, target, days, count
        start = target - timedelta(days=days // 2)
        self._series = biorhythm.series(birth, start.replace(hour=birth.hour, minute=birth.minute),
                                        days, count)
        self._start = start.replace(hour=birth.hour, minute=birth.minute)
        self.draw()

        pts = biorhythm.at(birth, target, count)
        tail = {"unknown": "　（时辰不详，按 12:00 起算）",
                "shichen": f"　（取中 {birth:%H:%M} 起算）"}.get(mode, "")
        blabel = (f"{birth:%Y-%m-%d %H:%M}" if mode == "exact"
                  else f"{birth:%Y-%m-%d} {self.birth.shichen_text or '时辰不详'}")
        L = [f"出生 {blabel}　测算 {target:%Y-%m-%d %H:%M}　"
             f"已历 {(target - birth).days} 天" + tail]
        L.append(f"综合指数（体力30%·情绪40%·智力30%）：{biorhythm.composite(birth, target):+.1f}%")
        L.append("")
        L.append("周期　　名称　　今日数值　　状态　　　相位说明")
        phase_desc = {biorhythm.HIGH: "上升或高峰", biorhythm.LOW: "回落或低谷", biorhythm.CRIT: "过零点，宜慎"}
        for p in pts:
            L.append(f"{p.period:>3}天　　{p.name}　　{p.value:+7.1f}%　　{p.phase}　　{phase_desc[p.phase]}")
        L.append("")
        for t in biorhythm.advice(pts):
            L.append("· " + t)
        crit = biorhythm.critical_days(birth, self._start, days, count)
        if crit:
            L.append("")
            L.append("近期临界日（|值|≤6%）：")
            for d, n, v in crit[:24]:
                L.append(f"　{d}　{n}　{v:+.1f}%")
        L.append("")
        L.append("理论渊源：Fleiss 体力23天／Swoboda 情绪28天／Teltscher 智力33天，"
                 "后扩为 38·43·48·53 天（直觉·审美·心灵·灵性）。属经验模型，仅供自我观察，非医学依据。")
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("end", "\n".join(L))
        self.text.configure(state="disabled")

    def export(self):
        p = filedialog.asksaveasfilename(defaultextension=".txt",
                                         filetypes=[("文本", "*.txt")], initialfile="生物钟.txt")
        if p:
            with open(p, "w", encoding="utf-8") as f:
                f.write(self.text.get("1.0", "end-1c"))
            messagebox.showinfo("已保存", p)

    def draw(self):
        c = self.canvas
        c.delete("all")
        if not self._series:
            return
        W, H = c.winfo_width(), c.winfo_height()
        if W < 100 or H < 100:
            return
        L, R, T, B = 58, 20, 34, 46
        pw, ph = W - L - R, H - T - B
        series = self._series
        dates = series["__dates__"]
        names = [n for n, *_ in biorhythm.CYCLES[:self._count]]

        def x(i):
            return L + (pw * i / (len(dates) - 1) if len(dates) > 1 else 0)

        def y(v):
            return T + ph / 2 - v / 100 * ph / 2

        for v in (-100, -50, 0, 50, 100):
            col = "#555555" if v == 0 else "#e5e5e5"
            dash = () if v == 0 else (3, 3)
            c.create_line(L, y(v), L + pw, y(v), fill=col, dash=dash)
            c.create_text(L - 10, y(v), text=f"{v:+d}%", anchor="e", font=(FONT, 8), fill="#666")
        step = max(1, len(dates) // 8)
        for i, d in enumerate(dates):
            if i % step == 0 or i == len(dates) - 1:
                c.create_line(x(i), T + ph, x(i), T + ph + 4, fill="#999")
                c.create_text(x(i), T + ph + 14, text=f"{d:%m-%d}", font=(FONT, 8), fill="#666")
        for idx, name in enumerate(names):
            vals = series[name]
            pts = []
            for i, v in enumerate(vals):
                pts.extend([x(i), y(v)])
            c.create_line(*pts, fill=COLORS[idx % len(COLORS)], width=2)
            c.create_text(L + 8 + idx * 82, T - 18, text=f"{name} {dict((n, p) for n, p, *_ in biorhythm.CYCLES)[name]}天",
                          anchor="w", font=(FONT, 9, "bold"), fill=COLORS[idx % len(COLORS)])
        ix = dates.index(min(dates, key=lambda d: abs(d - self._target))) if dates else 0
        c.create_line(x(ix), T, x(ix), T + ph, fill="#e67e22", dash=(4, 2))
        c.create_text(x(ix), T + 8, text="测算日", font=(FONT, 8), fill="#e67e22")


# --------------------------------------------------------------------------- #
# 主窗口
# --------------------------------------------------------------------------- #
def setup_dpi() -> float:
    """开启 DPI 感知，返回系统缩放比（1.0 / 1.25 / 1.5 …）。"""
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
        return ctypes.windll.shcore.GetScaleFactorForDevice(0) / 100.0
    except Exception:
        return 1.0


class App(tk.Tk):
    def __init__(self):
        self.scale = setup_dpi()
        super().__init__()
        self.tk.call("tk", "scaling", 1.3333 * self.scale)
        self.title("八字命理通鉴 · 万年历 / 八字 / 称骨 / 合婚 / 生物钟")
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = min(int(1180 * self.scale), sw - 40), min(int(700 * self.scale), sh - 90)
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{max(0, (sh - h) // 2 - 20)}")
        self.minsize(int(980 * self.scale), int(620 * self.scale))
        style = ttk.Style(self)
        try:
            style.theme_use("vista")
        except tk.TclError:
            pass
        style.configure(".", font=(FONT, 10))
        style.configure("TNotebook.Tab", font=(FONT, 11), padding=(14, 6))

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=6, pady=6)
        self.frames = {}
        for name, cls in [("万年历", CalendarFrame), ("八字排盘", BaziFrame),
                          ("称骨算命", ChengkuFrame), ("八字合婚", HehunFrame),
                          ("生物钟", BiorhythmFrame)]:
            f = cls(nb, self)
            nb.add(f, text=name)
            self.frames[name] = f
        self.nb = nb
        nb.bind("<<NotebookTabChanged>>", self._on_tab)
        self.status = tk.StringVar(value="就绪　|　传统文化研究工具，结论仅供参考")
        ttk.Label(self, textvariable=self.status, anchor="w",
                  foreground="#666").pack(fill="x", padx=10, pady=(0, 4))

    def _on_tab(self, _event=None):
        f = self.nb.nametowidget(self.nb.select()) if self.nb.select() else None
        if f is self.frames.get("生物钟"):
            self.after(60, f.draw)

    def goto_chengku(self, dt, gender):
        f = self.frames["称骨算命"]
        f.date.set(dt)
        f.gender.set(gender)
        f.compute()
        self.nb.select(f)

    def goto_biorhythm(self, dt):
        f = self.frames["生物钟"]
        f.birth.set(dt)
        f.compute()
        self.nb.select(f)


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
