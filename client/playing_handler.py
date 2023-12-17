import utils
import os
import sys
import time
import select
import logger
from enum import Enum
import utils
from playingrules import if_input_legal

class TerminalHandler:
    def __init__(self):
        # 终端信息
        self.column_max = os.get_terminal_size().columns - 1
        assert self.column_max >= 2, self.column_max
        self.row = self.column = 0
        self.row_buffer = ""
        # 用户打牌信息
        self.new_played_cards = []
        self.cursor = 0
        self.err = ""
    
    def __reset_cursor(self):
        if self.row > 0:
            print(f"\x1b[{self.row}A", end='')
            self.row = 0
        if self.column > 0:
            print(f"\x1b[{self.column}D", end='')
            self.column = 0

    def __flush_buffer(self, end):
        assert end in ['\n', ''], end
        print(self.row_buffer, end=end)
        if end == '\n':
            self.row += 1
            self.column = 0
        self.row_buffer = ""

    def __print_string(self, string:str, end='\n'):
        assert self.row_buffer == "", self.row_buffer
        assert end in ['\n', ''], end
        for ch in string:
            ch_columns = utils.columns(ch)
            if self.column + ch_columns > self.column_max:
                self.__flush_buffer(end='\n')
            self.row_buffer += ch
            self.column += ch_columns
        if end == '\n':
            if self.row_buffer != "":
                self.__flush_buffer(end='\n')
        elif end == '':
            if self.column == self.column_max:
                self.__flush_buffer(end='\n')
            else:
                self.__flush_buffer(end='')
        else:
            raise RuntimeError("")

    def print(self):
        # 恢复光标并清理所有的下面的屏幕数据
        self.__reset_cursor()
        print("\x1b[J", end='')
        sys.stdout.flush()
        # 打印信息
        self.__print_string("".join(self.new_played_cards))
        self.__print_string(self.err, end='')
        # 恢复光标
        self.__reset_cursor()
        # 再输出一遍直到cursor位置
        self.__print_string("".join(self.new_played_cards[0:self.cursor]), end='')
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

g_terminal_handler = TerminalHandler()
g_tcp_handler = None

def check_tcp_connection():
    g_tcp_handler.send_playing_heartbeat(finished=False)

# io系列函数
# now_played_cards: 用户已经输入好的字符串
# cursor: 光标位置
# user_cards: 用户已有的卡牌
# 输出新的now_played_cards, cursor二元组
if os.name == 'posix':
    # linux & mac
    def read_byte(if_remaining: bool) -> str:
        if if_remaining:
            return sys.stdin.read(1)
        TCP_COUNTER = 20
        check_tcp_counter = 0
        while select.select([sys.stdin], [], [], 0) == ([], [], []):
            if check_tcp_counter == 0:
                check_tcp_connection()
                check_tcp_counter = TCP_COUNTER
            check_tcp_counter -= 1
            time.sleep(0.05)
        return sys.stdin.read(1)

    def read_direction():
        if read_byte(True) != '[':
            raise InputException('(非法输入)')
        else:
            dir = read_byte(True)
            if dir == 'D':
                return SpecialInput.left_arrow
            elif dir == 'C':
                return SpecialInput.right_arrow
            else:
                raise InputException('(非法输入)')
    
    def read_input():
        fst_byte = read_byte(False).upper()
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
                check_tcp_connection()
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

def read_userinput(client_cards):
    th = g_terminal_handler
    while True:
        assert(th.cursor <= len(th.new_played_cards))
        end_input = False
        try:
            input = read_input()
            if input == SpecialInput.left_arrow:
                if th.cursor > 0:
                    th.cursor -= 1
            elif input == SpecialInput.right_arrow:
                if th.cursor < len(th.new_played_cards):
                    th.cursor += 1
            elif input == SpecialInput.backspace:
                if th.cursor > 0:
                    th.new_played_cards = th.new_played_cards[:th.cursor - 1] + th.new_played_cards[th.cursor:]
                    th.cursor -= 1
            elif input in ['\n', '\r']:
                end_input = True
            elif input == '\t':
                if th.new_played_cards == ['F']:
                    continue
                if th.cursor > 0:
                    fill_char = th.new_played_cards[th.cursor - 1]
                    used_num = th.new_played_cards.count(fill_char)
                    total_num = client_cards.count(fill_char)
                    fill_num = total_num - used_num
                    assert (fill_num >= 0)
                    th.new_played_cards = th.new_played_cards[:th.cursor] + fill_num * [fill_char] + th.new_played_cards[th.cursor:]
                    th.cursor += fill_num
            elif input == 'F':
                th.new_played_cards = ['F']
                th.cursor = 1
            elif input == 'C':
                th.new_played_cards = []
                th.cursor = 0
            else:
                assert(th.new_played_cards.count(input) <= client_cards.count(input))
                if th.new_played_cards.count(input) == client_cards.count(input):
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
        assert(th.new_played_cards == ['F'] or th.new_played_cards.count('F') == 0)
    return th.new_played_cards

# client_cards: 用户所持卡牌信息
# last_player: 最后打出牌的玩家
# client_player: 客户端正在输入的玩家
# users_played_cards: 场上所有牌信息
# tcp_handler: 客户端句柄，用于检测远端是否关闭了
def playing(
    client_cards,
    last_player: int,
    client_player: int,
    users_played_cards,
    tcp_handler
):
    global g_tcp_handler
    g_tcp_handler = tcp_handler
    print('请输入要出的手牌(\'F\'表示跳过):')
    global g_terminal_handler
    g_terminal_handler = TerminalHandler()

    new_played_cards = []
    new_score = 0

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
        new_played_cards = read_userinput(client_cards)
        _if_input_legal, new_score = if_input_legal(
            [utils.str_to_int(c) for c in new_played_cards],
            [utils.str_to_int(c) for c in client_cards],
            [utils.str_to_int(c) for c in users_played_cards[last_player]]
                if last_player != client_player else None
        )
        if _if_input_legal:
            logger.info(f"now play: {new_played_cards}")
            tcp_handler.send_playing_heartbeat(finished=True)
            break
        g_terminal_handler.err = '(非法牌型)'
        g_terminal_handler.print()

    if os.name == 'posix':
        #恢复核显
        os.system("stty echo icanon")
    elif os.name == 'nt':
        pass
    else:
        raise RuntimeError('unknow os!') 
    
    return new_played_cards, new_score
    
    