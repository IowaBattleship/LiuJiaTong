import utils
import socket 
import os
import sys
import time
import select
import psutil
import logger
import platform
from enum import Enum
from playingrules import if_input_legal

def show_playingcards(
    new_played_cards,
    cursor: int,
    err = ""
):
    # 恢复光标并清理所有的下面的屏幕数据
    print('\x1b[u\x1b[J',end='')
    # 打印信息
    print("".join(new_played_cards))
    if err != "":
        print(err)
    # 恢复光标
    print('\x1b[u', end='')
    # 再输出一遍直到cursor位置
    print("".join(new_played_cards[0:cursor]), end='')
    # 最后刷新print的缓冲区
    sys.stdout.flush()
    
class SpecialInput(Enum):
    left_arrow = 0
    right_arrow = 1
    backspace = 2

class InputException(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

g_client_socket = socket.socket()

if platform.system() == "Darwin":
    def check_tcp_connection():
        try:
            raddr = g_client_socket.getpeername()
            for conn in psutil.net_connections('tcp'):
                if conn.raddr == raddr:
                    return conn.status == 'ESTABLISHED'
            return False
        except psutil.AccessDenied:
            return True
elif platform.system() == "Linux":
    def check_tcp_connection():
        return g_client_socket.getsockopt(socket.IPPROTO_TCP, socket.TCP_INFO) == 1
elif platform.system() == "Windows":
    def check_tcp_connection():
        raddr = g_client_socket.getpeername()
        for conn in psutil.net_connections('tcp'):
            if conn.raddr == raddr:
                return conn.status == 'ESTABLISHED'
        return False
else:
    raise RuntimeError("unknown os")

# io系列函数
# now_played_cards: 用户已经输入好的字符串
# cursor: 光标位置
# user_cards: 用户已有的卡牌
# 输出新的now_played_cards, cursor二元组
if os.name == 'posix':
    # linux & mac
    def read_byte() -> str:
        TCP_COUNTER = 20
        check_tcp_counter = 0
        while select.select([sys.stdin], [], [], 0) == ([], [], []):
            if check_tcp_counter == 0:
                if check_tcp_connection() is False:
                    raise RuntimeError("Connection Failed")
                check_tcp_counter = TCP_COUNTER
            check_tcp_counter -= 1
            time.sleep(0.05)
        return sys.stdin.read(1)

    def read_direction():
        if read_byte() != '[':
            raise InputException('(非法输入)')
        else:
            dir = read_byte()
            if dir == 'D':
                return SpecialInput.left_arrow
            elif dir == 'C':
                return SpecialInput.right_arrow
            else:
                raise InputException('(非法输入)')
    
    def read_input():
        fst_byte = read_byte().upper()
        if fst_byte == '\x1b':
            # 判断是否是左右方向键
            return read_direction()
        elif fst_byte == '\x7f':
            return SpecialInput.backspace
        elif fst_byte in ['\n', '\t', 'C', 'F']:
            return fst_byte
        elif utils.str_to_int(fst_byte) != -1:
            return fst_byte
        else:
            raise InputException('(非法输入)')
    
elif os.name == 'nt':
    # windows
    from msvcrt import getch, kbhit
    def read_byte() -> str:
        TCP_COUNTER = 20
        check_tcp_counter = 0
        while not kbhit():
            if check_tcp_counter == 0:
                if check_tcp_connection() is False:
                    raise RuntimeError("Connection Failed")
                check_tcp_counter = TCP_COUNTER
            check_tcp_counter -= 1
            time.sleep(0.05)
        return chr(getch()[0])
        
    def read_direction():
        dir = read_byte()
        if dir == 'K':
            return SpecialInput.left_arrow
        elif dir == 'M':
            return SpecialInput.right_arrow
        else:
            raise InputException('(非法输入)')
    
    def read_input():
        fst_byte = read_byte()
        if fst_byte == '\xe0':
            return read_direction()
        fst_byte = fst_byte.upper()
        if fst_byte == '\x08':
            return SpecialInput.backspace
        elif fst_byte in ['\r', '\t', 'C', 'F']:
            return fst_byte
        elif utils.str_to_int(fst_byte) != -1:
            return fst_byte
        else:
            raise InputException('(非法输入)')

def read_userinput(
    new_played_cards,
    cursor: int,
    client_cards
):
    while True:
        assert(cursor <= len(new_played_cards))
        end_input = False
        try:
            input = read_input()
            if input == SpecialInput.left_arrow:
                if cursor > 0:
                    cursor -= 1
            elif input == SpecialInput.right_arrow:
                if cursor < len(new_played_cards):
                    cursor += 1
            elif input == SpecialInput.backspace:
                if cursor > 0:
                    new_played_cards = new_played_cards[:cursor - 1] + new_played_cards[cursor:]
                    cursor -= 1
            elif input in ['\n', '\r']:
                end_input = True
            elif input == '\t':
                if new_played_cards == ['F']:
                    continue
                if cursor > 0:
                    fill_char = new_played_cards[cursor - 1]
                    used_num = new_played_cards.count(fill_char)
                    total_num = client_cards.count(fill_char)
                    fill_num = total_num - used_num
                    assert (fill_num >= 0)
                    new_played_cards = new_played_cards[:cursor] + fill_num * [fill_char] + new_played_cards[cursor:]
                    cursor += fill_num
            elif input == 'F':
                new_played_cards = ['F']
                cursor = 1
            elif input == 'C':
                new_played_cards = []
                cursor = 0
            else:
                assert(new_played_cards.count(input) <= client_cards.count(input))
                if new_played_cards.count(input) == client_cards.count(input):
                    raise InputException('(你打出的牌超过上限了)')
                if new_played_cards == ['F']:
                    new_played_cards = []
                    cursor = 0
                new_played_cards = new_played_cards[:cursor] + [input] + new_played_cards[cursor:]
                cursor += 1
        except InputException as err:
            show_playingcards(new_played_cards, cursor, err.args[0])
        else:
            show_playingcards(new_played_cards, cursor)
        if end_input:
            break
        assert(new_played_cards == ['F'] or new_played_cards.count('F') == 0)
    
    return new_played_cards, cursor

# client_cards: 用户所持卡牌信息
# last_player: 最后打出牌的玩家
# client_player: 客户端正在输入的玩家
# users_played_cards: 场上所有牌信息
# client_socket: 客户端socket，用于检测远端是否关闭了
def playing(
    client_cards,
    last_player: int,
    client_player: int,
    users_played_cards,
    client_socket
):
    global g_client_socket
    g_client_socket = client_socket
    print('请输入要出的手牌(\'F\'表示跳过):')
    # 保存当前光标位置
    print('\x1b[s',end='')
    show_playingcards([], 0)

    new_played_cards = []
    new_score = 0
    cursor = 0

    if os.name == 'posix':
        #关闭核显，这里偷个懒假设大家都有stty程序
        #echo 核显，icanon 禁止缓冲
        os.system("stty -echo -icanon")
    elif os.name == 'nt':
        pass
    else:
        raise RuntimeError('unknow os!') 

    logger.info(f"last played: {users_played_cards[last_player] if last_player != client_player else None}")
    while True:
        new_played_cards, cursor = read_userinput(new_played_cards, cursor, client_cards)
        _if_input_legal, new_score = if_input_legal(
            [utils.str_to_int(c) for c in new_played_cards],
            [utils.str_to_int(c) for c in client_cards],
            [utils.str_to_int(c) for c in users_played_cards[last_player]]
                if last_player != client_player else None
        )
        if _if_input_legal:
            logger.info(f"now play: {new_played_cards}")
            break
        show_playingcards(new_played_cards, cursor, '(非法牌型)')

    if os.name == 'posix':
        #恢复核显
        os.system("stty echo icanon")
    elif os.name == 'nt':
        pass
    else:
        raise RuntimeError('unknow os!') 
    
    return new_played_cards, new_score
    
    