"""
六家统客户端 Flet 入口点。

用于 flet run / flet build 的入口，符合 Flet 标准项目结构。
运行方式：在项目根目录执行 `flet run gui_flet/main.py` 或 `python -m gui_flet`。
"""
import os
import sys
import logging
import threading

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_client_dir = os.path.join(_project_root, "client")
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
if _client_dir not in sys.path:
    sys.path.insert(0, _client_dir)  # interface、gui 等模块在 client 下

from cli.terminal_utils import check_packages, fatal, register_signal_handler

check_packages({
    "nt": [
        ("win32api", "pypiwin32"),
        ("win32con", "pypiwin32"),
    ],
})

from core import sound
sound.check_sound_player()

from interface import set_interface_type
import core.logger as logger
from cli.__main__ import Client
from core.config import Config


def run():
    """
    Flet 应用启动入口。
    尝试加载本地配置；若存在则开始界面显示「加入房间」「退出登录」，
    否则显示输入表单。用户点击连接后进入等待大厅。
    """
    os.chdir(_project_root)  # 确保配置文件 LiuJiaTong.json 等从项目根目录加载
    logger.init_logger()
    register_signal_handler(lambda: fatal("Keyboard Interrupt"))

    client = Client(no_cookie=False)
    client.load_config_silent()  # 静默加载，若存在则使用；否则开始界面显示输入表单

    set_interface_type("GUI")
    if client.config:
        client.logger.info("启动 GUI 模式 (Flet)，已加载本地配置")
    else:
        # 无配置时 init_logger 尚未调用，使用默认 logger
        _log = logging.getLogger("gui_flet")
        _log.info("启动 GUI 模式 (Flet)，无本地配置，显示输入界面")

    from gui_flet.gui_flet import init_gui_flet
    client_log = client.logger if client.config else logging.getLogger("gui_flet")
    init_gui_flet(client_log, client)


if __name__ == "__main__":
    run()
