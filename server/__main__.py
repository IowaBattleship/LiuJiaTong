import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='启动六家统服务端')
    parser.add_argument('--ip', type=str, default='0.0.0.0', help='listening ip (default: %(default)s)')
    parser.add_argument('--port', type=int, default=8080, help='port (default: %(default)s)')
    args = parser.parse_args()

    try:
        server = ThreadingTCPServer((args.ip, args.port), Game_Handler)
        threading.Thread(target=manager_thread).start()
    except Exception as e:
        print("server error:", e)
        os._exit(1)
    print("Listening")
    server.serve_forever()