import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import utils
utils.check_packages({
    "nt": [
        ("win32api", "pypiwin32"),
        ("win32con", "pypiwin32"),
    ],
})
from socketserver import ThreadingTCPServer
from game_handler import Game_Handler
from manager import Manager
import logger
import threading
import argparse
import threading

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
        if utils.user_confirm(prompt="是否强退服务端？",default=False) is True:
            print("Keyboard Interrupt")
            os._exit(1)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='启动六家统服务端')
    parser.add_argument('--ip', type=str, default='0.0.0.0', help='listening ip (default: %(default)s)')
    parser.add_argument('--port', type=int, default=8080, help='port (default: %(default)s)')
    parser.add_argument('-s', '--static', action='store_true', default=False, help='disable reorder users')
    args = parser.parse_args()

    logger.init_logger()
    utils.register_signal_handler(ctrl_c_handler)
    threading.Thread(target=manager_thread,args=(args.static,)).start()
    try:
        server = ThreadingTCPServer((args.ip, args.port), Game_Handler)
        manager_barrier.wait()
        print("Listening")
        server.serve_forever()
    except Exception as e:
        utils.fatal(f"server error: {e}")