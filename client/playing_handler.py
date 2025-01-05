import os
import sys
import time
import logger
from logging import Logger
import utils
from enum import Enum, auto
from playingrules import validate_user_input
from terminal_printer import *
import sound
from card import Card

class SpecialInput(Enum):
    left_arrow = auto(),
    right_arrow = auto(),
    backspace = auto(),

class InputException(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class PlayingTerminalHandler(TerminalHandler):
    def __init__(self):
        super().__init__()
        # 用户打牌信息
        self.new_played_cards = []
        self.cursor = 0 # 光标位置
        self.err = ""
    
    def print(self):
        # 恢复光标并清理所有的下面的屏幕数据
        self.reset_cursor()
        self.clear_screen_after_cursor()
        # 打印信息
        self.print_string("".join(self.new_played_cards), new_line=True)
        self.print_string(self.err, new_line=False)
        # 恢复光标
        self.reset_cursor()
        # 再输出一遍直到cursor位置
        self.print_string("".join(self.new_played_cards[0:self.cursor]), new_line=False)
        # 最后刷新print的缓冲区
        self.flush()

g_terminal_handler = None
g_tcp_handler = None
HANG_OUT_COUNTER = 10
g_user_hang_out_counter = HANG_OUT_COUNTER

def check_user_hang_out():
    global g_user_hang_out_counter
    if g_user_hang_out_counter > 0:
        g_user_hang_out_counter -= 1
        if g_user_hang_out_counter == 0:
            sound.playsound("ahoo", True, None)

def reset_user_hang_out():
    global g_user_hang_out_counter
    g_user_hang_out_counter = HANG_OUT_COUNTER

def clear_user_hang_out():
    global g_user_hang_out_counter
    g_user_hang_out_counter = 0

def wait_for_input():
    TCP_COUNTER = 20
    check_tcp_counter = TCP_COUNTER
    while check_have_input() is False:
        if check_tcp_counter == 0:
            g_tcp_handler.send_playing_heartbeat(finished=False)
            check_user_hang_out()
            check_tcp_counter = TCP_COUNTER
        check_tcp_counter -= 1
        time.sleep(0.05)
    clear_user_hang_out()

if os.name == 'posix':
    # linux & mac
    import select
    def check_have_input() -> bool:
        return select.select([sys.stdin], [], [], 0) != ([], [], [])

    def read_byte(if_blocking: bool) -> str:
        if if_blocking:
            wait_for_input()
        else:
            if check_have_input() is False:
                raise InputException('(非阻塞输入)')
        return chr(sys.stdin.buffer.read1(1)[0])

    def read_direction(if_blocking: bool):
        if read_byte(if_blocking) != '[':
            raise InputException('(非法输入)')
        else:
            dir = read_byte(if_blocking)
            if dir == 'D':
                return SpecialInput.left_arrow
            elif dir == 'C':
                return SpecialInput.right_arrow
            else:
                raise InputException('(非法输入)')

    def read_input(if_blocking: bool):
        fst_byte = read_byte(if_blocking).upper()
        if fst_byte == '\x1b':
            # 判断是否是左右方向键
            return read_direction(if_blocking)
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
    def check_have_input():
        return kbhit() != 0

    def read_byte(if_blocking: bool) -> str:
        if if_blocking:
            wait_for_input()
        else:
            if check_have_input() is False:
                raise InputException('(非阻塞输入)')
        return chr(getch()[0])
        
    def read_direction(if_blocking: bool):
        dir = read_byte(if_blocking)
        if dir == 'K':
            return SpecialInput.left_arrow
        elif dir == 'M':
            return SpecialInput.right_arrow
        else:
            raise InputException('(非法输入)')

    def read_input(if_blocking: bool):
        fst_byte = read_byte(if_blocking)
        if fst_byte == '\xe0':
            return read_direction(if_blocking)
        fst_byte = fst_byte.upper()
        if fst_byte == '\x03':
            utils.fatal("Keyboard Interrupt")
        elif fst_byte == '\x08':
            return SpecialInput.backspace
        elif fst_byte in ['\r', '\t', 'C', 'F']:
            return fst_byte
        elif utils.str_to_int(fst_byte) != -1:
            return fst_byte
        else:
            raise InputException('(非法输入)')

g_input_buffer = []
def prepare_input_buffer():
    global g_input_buffer
    try:
        g_input_buffer = []
        while True:
            g_input_buffer.append(read_input(if_blocking=False))
    except InputException:
        g_input_buffer = [x for x in g_input_buffer if x not in ['\r', '\n']]
        import logger
        logger.info(f"{g_input_buffer}")

def read_input_buffer():
    global g_input_buffer
    if len(g_input_buffer) > 0:
        input = g_input_buffer[0]
        g_input_buffer = g_input_buffer[1:]
        return input
    else:
        return None

def get_input():
    input = read_input_buffer()
    if input is not None:
        return input
    return read_input(if_blocking=True)

# 读取用户输入，支持输入方向键，退格键（backspace），回车键（enter），tab键（tab）
def read_userinput(client_cards: list[Card]) -> list[str]:
    logger.info("read_userinput")
    th = g_terminal_handler
    while True:
        assert(th.cursor <= len(th.new_played_cards))
        end_input = False
        try:
            input = get_input()
            if input == SpecialInput.left_arrow: # 左移光标
                if th.cursor > 0:
                    th.cursor -= 1
            elif input == SpecialInput.right_arrow: # 右移光标
                if th.cursor < len(th.new_played_cards):
                    th.cursor += 1
            elif input == SpecialInput.backspace: # 删除光标左边的字符
                if th.cursor > 0:
                    th.new_played_cards = th.new_played_cards[:th.cursor - 1] + th.new_played_cards[th.cursor:]
                    th.cursor -= 1
            elif input in ['\n', '\r']: # 结束输入
                end_input = True
            elif input == '\t': # 自动补全
                if th.new_played_cards == ['F']:
                    continue
                if th.cursor > 0:
                    fill_char = th.new_played_cards[th.cursor - 1]
                    used_num = th.new_played_cards.count(fill_char)
                    total_num = get_card_count(client_cards, fill_char)
                    fill_num = total_num - used_num
                    assert (fill_num >= 0)
                    th.new_played_cards = th.new_played_cards[:th.cursor] + fill_num * [fill_char] + th.new_played_cards[th.cursor:]
                    th.cursor += fill_num
            elif input == 'F': # 跳过回合
                th.new_played_cards = ['F']
                th.cursor = 1
            elif input == 'C': # 清空输入
                th.new_played_cards = []
                th.cursor = 0
            else: # 输入一张牌
                user_card_count = get_card_count(client_cards, input)
                assert(th.new_played_cards.count(input) <= user_card_count)
                if th.new_played_cards.count(input) == user_card_count:
                    raise InputException('(你打出的牌超过上限了)')
                if th.new_played_cards == ['F']:
                    th.new_played_cards = []
                    th.cursor = 0
                th.new_played_cards = th.new_played_cards[:th.cursor] + [input] + th.new_played_cards[th.cursor:]
                th.cursor += 1
        except InputException as err:
            th.err = err.args[0]
        else:
            th.err = ""
        finally:
            th.print()
        if end_input:
            break
        assert(th.new_played_cards == ['F'] or th.new_played_cards.count('F') == 0) # 不允许夹杂跳过，避免误输入
    return th.new_played_cards

# 01/04/2024: 支持Card类
def get_card_count(client_cards: list[Card], card: str) -> int:
    result = 0
    for c in client_cards:
        if c.get_cli_str() == card:
            result += 1
    return result

# 从控制台获取用户输入，直到用户输入合法数据
def playing(
    client_cards      : list[Card], # 用户所持卡牌信息
    last_player       : int,        # 最后打出牌的玩家
    client_player     : int,        # 客户端正在输入的玩家
    users_played_cards: list[Card], # 场上所有牌信息
    tcp_handler,                    # 客户端句柄，用于检测远端是否关闭了
) -> tuple[list[Card], int]:
    tcp_handler.logger.info("playing")
    global g_tcp_handler
    g_tcp_handler = tcp_handler
    reset_user_hang_out()
    prepare_input_buffer()
    print('请输入要出的手牌(\'F\'表示跳过):')
    global g_terminal_handler
    g_terminal_handler = PlayingTerminalHandler()

    new_played_cards = []
    new_score = 0

    tcp_handler.logger.info(f"last played: {users_played_cards[last_player] if last_player != client_player else None}")
    while True:
        new_played_cards = read_userinput(client_cards)

        # 11/03/2024: 支持Card类
        tcp_handler.logger.info(f"new_played_cards: {new_played_cards}")
        tcp_handler.logger.info(f"client_cards: {client_cards}")
        tcp_handler.logger.info(f"users_played_cards[last_player]: {users_played_cards[last_player] if last_player != client_player else None}")
        legal_input, new_score = validate_user_input(
            [utils.str_to_int(c) for c in new_played_cards],
            [c.value for c in client_cards],
            [c.value for c in users_played_cards[last_player]]
                if last_player != client_player and users_played_cards[last_player] != None else None
        )
        if legal_input:
            tcp_handler.logger.info(f"now play: {new_played_cards}")
            tcp_handler.send_playing_heartbeat(finished=True)
            break
        g_terminal_handler.err = '(非法牌型)'
        g_terminal_handler.print()
    
    return new_played_cards, new_score