import os
import sys

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _project_root)

from server.game_handler import Game_Handler
from server.manager import Manager
import core.logger as logger
import threading
import argparse
from core.network.my_network import ReusableTCPServer
from common.console import check_packages, user_confirm, fatal, register_signal_handler
check_packages({
    "nt": [
        ("win32api", "pypiwin32"),
        ("win32con", "pypiwin32"),
    ],
})

manager_barrier = threading.Barrier(2)
def manager_thread(static_user_order):
    manager = Manager(static_user_order)
    manager_barrier.wait()
    manager.run()

ctrl_c_handler_lock = threading.Lock()
def ctrl_c_handler():
    if ctrl_c_handler_lock.locked():
        return
    with ctrl_c_handler_lock:
        if user_confirm(prompt="是否强退服务端？",default=False) is True:
            fatal("Keyboard Interrupt")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='启动六家统服务端')
    parser.add_argument('--ip', type=str, default='0.0.0.0', help='listening ip (default: %(default)s)')
    parser.add_argument('--port', type=int, default=8080, help='port (default: %(default)s)')
    parser.add_argument('-s', '--static', action='store_true', default=False, help='disable reorder users')
    args = parser.parse_args()

    logger.init_logger()
    register_signal_handler(ctrl_c_handler)
    threading.Thread(target=manager_thread,args=(args.static,)).start()
    try:
        server = ReusableTCPServer((args.ip, args.port), Game_Handler)
        manager_barrier.wait()
        print("Listening")
        server.serve_forever()
    except Exception as e:
        fatal(f"server error: {e}")
