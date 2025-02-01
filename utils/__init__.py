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

def cards_to_strs(cards: list[Card]):
    if cards is None:
        return None
    # 检查数据类型
    for c in cards:
        if not isinstance(c, Card):
            raise TypeError('cards must be Card type')
    return [str(c) for c in cards]

def draw_cards(cards: list[Card], targets: list[str]) -> list[Card]:
    # 双指针遍历cards和targets，找到value与targets中int值相同的card
    result = []
    i, j = 0, 0
    while i < len(cards) and j < len(targets):
        if cards[i].value == str_to_int(targets[j]):
            result.append(cards[i])
            i += 1
            j += 1
        else:
            i += 1
    return result

def calculate_score(cards: list[Card]):
    score = 0
    for c in cards:
        if c.value == 5:
            score += 5
        elif c.value == 10 or c.value == 13:
            score += 10
    return score

# 01/04/2024: 支持Card类
def get_card_count(client_cards: list[Card], card: str) -> int:
    result = 0
    for c in client_cards:
        if c.get_cli_str() == card:
            result += 1
    return result

def head_master_in_team(head_master: int, client_id: int) -> bool:
    return head_master in [client_id, (client_id + 2) % 6, (client_id + 4) % 6]

def calculate_team_scores(head_master: int, client_id: int, users_cards_num: list[int], users_scores: list[int]) -> tuple[int, int]:
    if head_master_in_team(head_master, client_id):
        my_team_score = calculate_head_master_team_score(client_id, users_scores)
        opposing_team_score = calculate_normal_team_score((client_id + 1) % 6, users_cards_num, users_scores)
    elif head_master_in_team(head_master, (client_id + 1) % 6):
        opposing_team_score = calculate_head_master_team_score((client_id + 1) % 6, users_scores)
        my_team_score = calculate_normal_team_score(client_id, users_cards_num, users_scores)
    else:
        my_team_score = calculate_normal_team_score(client_id, users_cards_num, users_scores)
        opposing_team_score = calculate_normal_team_score((client_id + 1) % 6, users_cards_num, users_scores)
    return my_team_score, opposing_team_score

def calculate_head_master_team_score(client_id: int, users_scores: list[int]):
    return users_scores[client_id] + users_scores[(client_id + 2) % 6] + users_scores[(client_id + 4) % 6]

def calculate_normal_team_score(client_id: int, users_cards_num: list[int], users_scores: list[int]):
    team_score = 0
    team_score += users_scores[client_id] if users_cards_num[client_id] == 0 else 0
    team_score += users_scores[(client_id + 2) % 6] if users_cards_num[(client_id + 2) % 6] == 0 else 0
    team_score += users_scores[(client_id + 4) % 6] if users_cards_num[(client_id + 4) % 6] == 0 else 0
    return team_score

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