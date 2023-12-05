import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import importlib
if_need_restart = False
def check_package(package, install=None):
    try:
        importlib.import_module(package)
    except ImportError:
        os.system(f"pip3 install {package if install is None else install}")
        global if_need_restart; if_need_restart = True
if os.name == 'nt':
    check_package("win32api", "pypiwin32")
    check_package("win32con", "pypiwin32")
if if_need_restart:
    print("\x1b[32m\x1b[1mPackages are installed, please restart program to update system enviroment\x1b[0m")
    os._exit(0)

from socketserver import ThreadingTCPServer
from game_handler import Game_Handler
from manager import Manager
from logger import init_logger
import threading
import argparse
import utils

def manager_thread(static_user_order):
    init_logger()
    manager = Manager(static_user_order)
    manager.run()

ctrl_c_handler_lock = threading.Lock()
def ctrl_c_handler():
    if ctrl_c_handler_lock.locked():
        return
    with ctrl_c_handler_lock:
        if utils.user_confirm(prompt="是否强退服务端？",default=False) is True:
            print("Keyboard Interrupt")
            os._exit(1)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='启动六家统服务端')
    parser.add_argument('--ip', type=str, default='0.0.0.0', help='listening ip (default: %(default)s)')
    parser.add_argument('--port', type=int, default=8080, help='port (default: %(default)s)')
    parser.add_argument('-s', '--static', action='store_true', default=False, help='disable reorder users')
    args = parser.parse_args()

    if os.name == "posix":
        import signal
        def console_ctrl_handler(sig, frame):
            ctrl_c_handler()
        signal.signal(signal.SIGINT, console_ctrl_handler)
    elif os.name == "nt":
        import win32api
        import win32con
        def console_ctrl_handler(ctrl_type):
            if ctrl_type == win32con.CTRL_C_EVENT:
                threading.Thread(target=ctrl_c_handler).start()
                return True
        # 注册控制台事件处理程序
        win32api.SetConsoleCtrlHandler(console_ctrl_handler, True)
    else:
        raise RuntimeError("Unknown os")

    try:
        server = ThreadingTCPServer((args.ip, args.port), Game_Handler)
        threading.Thread(target=manager_thread,args=(args.static,)).start()
    except Exception as e:
        print(f"\x1b[31m\x1b[1mserver error: {e}\x1b[0m")
        os._exit(1)
    print("Listening")
    server.serve_forever()