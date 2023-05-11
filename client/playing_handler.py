import utils
import os
import sys
from enum import Enum
from playingrules import if_input_legal
from userinfo import UserInfo

def show_playingcards(
    now_played_cards,
    cursor: int,
    err = ""
):
    # 恢复光标并清理所有的下面的屏幕数据
    print('\x1b[u\x1b[J',end='')
    # 打印信息
    print("".join(now_played_cards))
    if err != "":
        print(err)
    # 恢复光标
    print('\x1b[u', end='')
    # 再输出一遍直到cursor位置
    print("".join(now_played_cards[0:cursor]), end='')
    # 最后刷新print的缓冲区
    sys.stdout.flush()
    
class Special_Input(Enum):
    left_arrow = 0
    right_arrow = 1
    backspace = 2

class InputException(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

# io系列函数
# now_played_cards: 用户已经输入好的字符串
# cursor: 光标位置
# user_cards: 用户已有的卡牌
# 输出新的now_played_cards, cursor二元组
if os.name == 'posix':
    # linux & mac
    def read_byte() -> str:
        return sys.stdin.read(1)

    def read_direction():
        if read_byte() != '[':
            raise InputException('(非法输入)')
        else:
            dir = read_byte()
            if dir == 'D':
                return Special_Input.left_arrow
            elif dir == 'C':
                return Special_Input.right_arrow
            else:
                raise InputException('(非法输入)')
    
    def read_input():
        fst_byte = read_byte().upper()
        if fst_byte == '\x1b':
            # 判断是否是左右方向键
            return read_direction()
        elif fst_byte == '\x7f':
            return Special_Input.backspace
        elif fst_byte in ['\n', '\t', 'C', 'F']:
            return fst_byte
        elif utils.str_to_int(fst_byte) != -1:
            return fst_byte
        else:
            raise InputException('(非法输入)')
    
elif os.name == 'nt':
    # windows
    from msvcrt import getch
    def read_byte() -> str:
        char = chr(getch()[0])
        if char == '\x03': # ctrl + C
            raise KeyboardInterrupt()
        return char
        
    def read_direction():
        dir = read_byte()
        if dir == 'K':
            return Special_Input.left_arrow
        elif dir == 'M':
            return Special_Input.right_arrow
        else:
            raise InputException('(非法输入)')
    
    def read_input():
        fst_byte = read_byte()
        if fst_byte == '\xe0':
            return read_direction()
        fst_byte = fst_byte.upper()
        if fst_byte == '\x08':
            return Special_Input.backspace
        elif fst_byte in ['\r', '\t', 'C', 'F']:
            return fst_byte
        elif utils.str_to_int(fst_byte) != -1:
            return fst_byte
        else:
            raise InputException('(非法输入)')

def read_userinput(
    now_played_cards,
    cursor: int,
    user_cards
):
    while True:
        assert(cursor <= len(now_played_cards))
        end_input = False
        try:
            input = read_input()
            if input == Special_Input.left_arrow:
                if cursor > 0:
                    cursor -= 1
            elif input == Special_Input.right_arrow:
                if cursor < len(now_played_cards):
                    cursor += 1
            elif input == Special_Input.backspace:
                if cursor > 0:
                    now_played_cards = now_played_cards[:cursor - 1] + now_played_cards[cursor:]
                    cursor -= 1
            elif input in ['\n', '\r']:
                end_input = True
            elif input == '\t':
                if now_played_cards == ['F']:
                    continue
                if cursor > 0:
                    fill_char = now_played_cards[cursor - 1]
                    used_num = now_played_cards.count(fill_char)
                    total_num = user_cards.count(fill_char)
                    fill_num = total_num - used_num
                    assert (fill_num >= 0)
                    now_played_cards = now_played_cards[:cursor] + fill_num * [fill_char] + now_played_cards[cursor:]
                    cursor += fill_num
            elif input == 'F':
                now_played_cards = ['F']
                cursor = 1
            elif input == 'C':
                now_played_cards = []
                cursor = 0
            else:
                assert(now_played_cards.count(input) <= user_cards.count(input))
                if now_played_cards.count(input) == user_cards.count(input):
                    raise InputException('(你打出的牌超过上限了)')
                if now_played_cards == ['F']:
                    now_played_cards = []
                    cursor = 0
                now_played_cards = now_played_cards[:cursor] + [input] + now_played_cards[cursor:]
                cursor += 1
        except InputException as err:
            show_playingcards(now_played_cards, cursor, err.args[0])
        else:
            show_playingcards(now_played_cards, cursor)
        if end_input:
            break
        assert(now_played_cards == ['F'] or now_played_cards.count('F') == 0)
    
    return now_played_cards, cursor

# user: 用户信息
# last_user: 最后打出牌的用户
# client_user: 客户端正在输入的用户
# played_cards: 场上所有牌信息
def playing(
    user: UserInfo,
    last_user: int,
    client_user: int,
    played_cards
) -> int:
    print('请输入要出的手牌(\'F\'表示跳过):')
    # 保存当前光标位置
    print('\x1b[s',end='')
    show_playingcards([], 0)

    now_played_cards = []
    cursor = 0

    if os.name == 'posix':
        #关闭核显，这里偷个懒假设大家都有stty程序
        #echo 核显，icanon 禁止缓冲
        os.system("stty -echo -icanon")
    elif os.name == 'nt':
        pass
    else:
        raise RuntimeError('unknow os!') 

    while True:
        now_played_cards, cursor = read_userinput(now_played_cards, cursor, user.cards)
        user_input = [utils.str_to_int(c) for c in now_played_cards]
        _if_input_legal, score = if_input_legal(user_input,
                                                [utils.str_to_int(c) for c in user.cards],
                                                last_user == client_user,
                                                [utils.str_to_int(c) for c in played_cards[last_user]])
        if _if_input_legal:
            user.played_card = now_played_cards
            if now_played_cards[0] != 'F':
                for x in now_played_cards:
                    user.cards.remove(x)
            break
        else:
            show_playingcards(now_played_cards, cursor, '(非法牌型)')

    if os.name == 'posix':
        #恢复核显
        os.system("stty echo icanon")
    elif os.name == 'nt':
        pass
    else:
        raise RuntimeError('unknow os!') 
    
    return score
    
    