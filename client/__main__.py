import os
import sys
import argparse

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_client_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _project_root)
if _client_dir not in sys.path:
    sys.path.insert(0, _client_dir)

from cli.terminal_utils import check_packages, fatal, register_signal_handler
check_packages({
    "nt": [
        ("win32api", "pypiwin32"),
        ("win32con", "pypiwin32"),
    ],
})
from core import sound
sound.check_sound_player()

import core.logger as logger
from cli.__main__ import Client
from core.config import Config
from client.interface import run_client


def ctrl_c_handler():
    fatal("Keyboard Interrupt")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="启动六家统客户端")
    parser.add_argument("--ip", type=str, help="ip address")
    parser.add_argument("--port", type=int, help="port")
    parser.add_argument("--user-name", type=str, help="user name")
    parser.add_argument("--mode", type=str, default="CLI", help="mode: CLI, GUI, or GUI_FLET")
    parser.add_argument("-n", "--no-cookie", action="store_true", default=False, help="disable cookies")
    args = parser.parse_args()

    logger.init_logger()
    register_signal_handler(ctrl_c_handler)

    client = Client(args.no_cookie)
    if args.ip is None or args.port is None or args.user_name is None:
        client.load_config()
    else:
        client.config = Config(args.ip, args.port, args.user_name)
        client.init_logger()

    run_client(client, args.mode)
