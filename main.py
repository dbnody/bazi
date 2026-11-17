# -*- coding: utf-8 -*-
"""启动入口：python main.py（打包后为同目录 exe）"""
import sys
import traceback


def _fail(msg: str) -> None:
    """打包成 exe 后没有控制台，用对话框报错；源码运行时退化到 print。"""
    try:
        from tkinter import Tk, messagebox
        root = Tk()
        root.withdraw()
        messagebox.showerror("启动失败", msg)
        root.destroy()
    except Exception:
        print(msg)
        try:
            input("按回车退出…")
        except Exception:
            pass
    sys.exit(1)


def _require_deps() -> None:
    try:
        import lunar_python  # noqa: F401
    except ImportError:
        _fail("缺少历算依赖 lunar-python。请先安装：\n"
              "    pip install lunar-python\n"
              "或（在本目录下）：\n"
              "    pip install -r requirements.txt")


if __name__ == "__main__":
    _require_deps()
    try:
        from bazi.gui import main
        main()
    except Exception:
        _fail("程序异常：\n" + traceback.format_exc(limit=8))
