import os
import sys
import argparse

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import utils
utils.check_packages({
    "nt": [
        ("win32api", "pypiwin32"),
        ("win32con", "pypiwin32"),
    ],
})
import sound
sound.check_sound_player()

from interface import set_interface_type
import logger
from gui import init_gui
from myclient import Client
from config import Config

def ctrl_c_handler():
    utils.fatal("Keyboard Interrupt")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='启动六家统客户端')
    parser.add_argument('--ip', type=str, help='ip address')
    parser.add_argument('--port', type=int, help='port')
    parser.add_argument('--user-name', type=str, help='user name')
    parser.add_argument('--mode', type=str, default="CLI", help='mode')
    parser.add_argument('-n', '--no-cookie', action='store_true', default=False, help='disable cookies')
    args = parser.parse_args()

    logger.init_logger()

    utils.register_signal_handler(ctrl_c_handler)
    client = Client(args.no_cookie)

    # 11/02/2024: 增加GUI模式
    if args.mode == "GUI":
        logger.info("启动GUI模式")
        set_interface_type("GUI")
        init_gui()
    else:
        logger.info("启动命令行模式")

    if args.ip == None or args.port == None or args.user_name == None:
        client.load_config()
    else:
        client.config = Config(args.ip, args.port, args.user_name)
        client.init_logger()

    client.connect(client.config.ip, client.config.port)
    utils.disable_echo()
    client.run()
    utils.enable_echo()
    client.close()
