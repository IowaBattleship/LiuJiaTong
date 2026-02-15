"""
Flet 构建入口：供 flet build apk / flet run 使用。

flet build 期望在 app 目录根下找到 main.py，此处将调用转发到 gui_flet.main.run()。
"""
from gui_flet.main import run

if __name__ == "__main__":
    run()
