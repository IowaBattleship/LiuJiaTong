import os, sys
import threading

from card import Card

def str_to_int(c=''):
    if '3' <= c <= '9':
        return int(c)
    elif c == 'B':
        return 10
    elif c == 'J':
        return 11
    elif c == 'Q':
        return 12
    elif c == 'K':
        return 13
    elif c == 'A':
        return 14
    elif c == '2':
        return 15
    elif c == '0':  # joker
        return 16
    elif c == '1':
        return 17
    elif c == 'F':  # skip this round
        return 0
    return -1


def int_to_str(x=-1):
    if 3 <= x <= 9:
        return str(x)
    elif x == 10:
        return 'B'
    elif x == 11:
        return 'J'
    elif x == 12:
        return 'Q'
    elif x == 13:
        return 'K'
    elif x == 14:
        return 'A'
    elif x == 15:
        return '2'
    elif x == 16:  # joker
        return '0'
    elif x == 17:
        return '1'
    elif x == 0:  # skip this round
        return 'F'
    return '-'


def strs_to_ints(cards: list[str]):
    if cards is None:
        return None
    return [str_to_int(c) for c in cards]


def cards_to_ints(cards: list[Card]):
    if cards is None:
        return None
    # 检查数据类型
    for c in cards:
        if not isinstance(c, Card):
            raise TypeError('cards must be Card type')
    return [c.value for c in cards]


# 返回上一位出牌玩家下标
def last_played(played_cards, player):
    i = (player - 1 + 6) % 6
    while i != player:
        if len(played_cards[i]) != 0:
            return i
        i = (i - 1 + 6) % 6
    return player

def verbose(string: str):
    print(f"\x1b[30m\x1b[1m{string}\x1b[0m")

def success(string: str):
    print(f"\x1b[32m\x1b[1m{string}\x1b[0m")

def warn(string: str):
    print(f"\x1b[33m\x1b[1m{string}\x1b[0m")

def error(string: str):
    print(f"\x1b[31m\x1b[1m{string}\x1b[0m")

def fatal(string: str):
    error(string)
    enable_echo()
    os._exit(1)

def user_confirm(prompt: str, default: bool):
    while True:
        print(prompt, end='')
        print("[Y/n]" if default is True else "[y/N]", end='')
        print(": ", end='')
        while True:
            try:
                resp = input().upper()
            except EOFError:
                pass
            else:
                break
        if resp == '':
            return default
        elif resp == 'Y':
            return True
        elif resp == 'N':
            return False
        else:
            print(f"非法输入，", end='')

import importlib
if_need_restart = False
def __try_to_import(package_info):
    global if_need_restart
    package, install = package_info
    try:
        importlib.import_module(package)
    except ImportError:
        os.system(f"pip3 install {package if install is None else install}")
        if_need_restart = True

def check_packages(packages: dict):
    global if_need_restart
    for package_info in packages.get(os.name, []):
        __try_to_import(package_info)
    for package_info in packages.get("default", []):
        __try_to_import(package_info)
    if if_need_restart:
        success("Packages are installed, please restart program to update system enviroment")
        exit(0)

def register_signal_handler(ctrl_c_handler):
    if os.name == "posix":
        import signal
        def console_ctrl_handler(sig, frame):
            threading.Thread(target=ctrl_c_handler).start()
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

if os.name == "posix":
    import termios
    old_termios_setting = termios.tcgetattr(sys.stdin)
    def disable_echo():
        termios_setting = termios.tcgetattr(sys.stdin)
        termios_setting[3] &= ~termios.ECHO
        termios_setting[3] &= ~termios.ICANON
        termios.tcsetattr(sys.stdin, termios.TCSAFLUSH, termios_setting)
    def enable_echo():
        global old_termios_setting
        termios.tcsetattr(sys.stdin, termios.TCSAFLUSH, old_termios_setting)
elif os.name == "nt":
    def disable_echo():
        pass
    def enable_echo():
        pass
else:
    raise RuntimeError("Unknown os")