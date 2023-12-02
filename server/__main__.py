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

def manager_thread():
    init_logger()
    manager = Manager()
    manager.run()

ctrl_c_handler_lock = threading.Lock()
def ctrl_c_handler():
    if ctrl_c_handler_lock.locked():
        return
    with ctrl_c_handler_lock:
        while True:
            print("是否强退服务端？[y/N]: ", end='')
            while True:
                try:
                    resp = input().upper()
                except EOFError:
                    pass
                else:
                    break
            if resp in ['', 'N', 'Y']:
                if resp == 'Y':
                    print("Keyboard Interrupt")
                    os._exit(1)
                break
            else:
                print(f"非法输入，", end='')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='启动六家统服务端')
    parser.add_argument('--ip', type=str, default='0.0.0.0', help='listening ip (default: %(default)s)')
    parser.add_argument('--port', type=int, default=8080, help='port (default: %(default)s)')
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
        raise RuntimeError("unknown os")

    try:
        server = ThreadingTCPServer((args.ip, args.port), Game_Handler)
        threading.Thread(target=manager_thread).start()
    except Exception as e:
        print("server error:", e)
        os._exit(1)
    print("Listening")
    server.serve_forever()