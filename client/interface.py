import os
from sound import playsound, playsounds
from playingrules import judge_and_transform_cards, CardType
from typing import List

import utils

def columns(string: str) -> int:
    columns = 0
    for ch in string:
        if '\u4e00' <= ch <= '\u9fff':
            columns += 2 #中文字符占两格
        else:
            columns += 1
    return columns
class Sentence:
    """
    打印的切片数据
    :string : 打印的字符串（不带控制序列字符）
    :highlight : 是否要高亮版的字符串
    :color : 如果color为0则打印白色字符，否则打印对应的颜色的字符，控制序列格式串为f'\\x1b[{color}m'
    :blink : 是否需要闪烁字符串
    :underline : 是否需要对字符串添加下划线
    """
    def __init__(self):
        self.string: str = ""
        self.highlight: bool = False
        self.color: int = 0
        self.blink: bool = False
        self.underline: bool = False

    def __str__(self):
        return self.string
    
    def columns(self) -> int:
        return columns(self.string)
    
    def gen_print(self) -> str:
        print_str = ""
        # 打印控制序列字符
        if self.highlight:
            print_str += '\x1b[1m'
        if self.color > 0:
            print_str += f'\x1b[{self.color}m'
        if self.blink:
            print_str += '\x1b[5m'
        if self.underline:
            print_str += '\x1b[4m'
        # 打印字符串
        print_str += self.string
        # 清除格式
        print_str += '\x1b[0m'
        return print_str
    def gen_csi(self) -> str:
        print_str = ""
        if self.highlight:
            print_str += '\x1b[1m'
        if self.color > 0:
            print_str += f'\x1b[{self.color}m'
        if self.blink:
            print_str += '\x1b[5m'
        if self.underline:
            print_str += '\x1b[4m'
        return print_str

Paragraph = List[Sentence]
Chapter = List[Paragraph]
Article = List[Chapter]

def clear_screen():
    print('\x1b[2J\x1b[H', end='')

def print_hline(term_column: int):
    assert(term_column >= 2)
    print('+', '-' * (term_column - 2), '+', sep='')

def paragraph_columns(paragraph: Paragraph) -> int:
    assert(len(paragraph) > 0)
    columns = len(paragraph) - 1 #中间用空格隔开
    for sentence in paragraph:
        columns += sentence.columns()
    return columns

def print_paragraph(paragraph: Paragraph, term_column: int):
    assert(len(paragraph) > 0)
    assert(term_column >= 4)
    line_begin = False
    line_end = False
    now_column = 0 
    max_column = term_column - 2 
    for sentence in paragraph:
        printed = False
        while not printed:
            if not line_begin:
                print('|', end='')
                line_begin = True
                line_end = False
            else:
                if now_column < max_column:
                    print(' ', end='')
                    now_column += 1
                else:
                    print('|\n|',end='')
                    now_column = 0
            
            if now_column + sentence.columns() > max_column:
                if now_column > 0:
                    print(' ' * (max_column - now_column), '|', sep='')
                    assert(not line_end)
                    line_begin = False
                    line_end = True
                    now_column = 0
                else:
                    csi_flag = False
                    for ch in sentence.gen_print():
                        if ch == '\x1b':
                            csi_flag = True
                        if csi_flag:
                            print(ch, end='')
                            if 'A' <= ch <= 'Z' or 'a' <= ch <= 'z': #这里简单判了，不是很标准
                                csi_flag = False
                            continue
                        if now_column + columns(ch) > max_column:
                            print(' ' * (max_column - now_column), '\x1b[0m', '|', sep='')
                            print('|', sentence.gen_csi(), ch, sep='', end='')
                            now_column = columns(ch)
                        else:
                            print(ch, end='')
                            now_column += columns(ch)
                    printed = True
            else:
                print(sentence.gen_print(), end='')
                now_column += sentence.columns()    
                printed = True        
    if not line_end:
        print(' ' * (max_column - now_column), '|', sep='')

def gen_help_chapter() -> Chapter:
    chapter = []
    
    def gen_paragraph(string: str) -> Paragraph:
        sentence = Sentence()
        sentence.string = string
        return [sentence]
    chapter.append(gen_paragraph("B 代表 10"))
    chapter.append(gen_paragraph("0 代表 小王  1 代表 大王"))
    chapter.append(gen_paragraph("tab键 补全牌  C键 清空手中的牌"))

    return chapter

def gen_score_chapter(
    now_score: int,
    client_player: int,
    users_score
) -> Chapter :
    chapter = []

    def gen_field_score() -> Paragraph:
        score_on_field = Sentence()
        score_on_field.string = f'当前场上分数:{now_score}'
        return [score_on_field]
    chapter.append(gen_field_score())

    def gen_team_score() -> Paragraph:
        paragraph = []
        
        own_score = Sentence()
        score = 0
        for i in range(6):
            if i % 2 == client_player % 2:
                score += users_score[i]
        own_score.string = f'己方得分:{score}'
        own_score.highlight = True
        own_score.color = 32
        paragraph.append(own_score)

        opp_score = Sentence()
        score = 0
        for i in range(6):
            if i % 2 != client_player % 2:
                score += users_score[i]
        opp_score.string = f'对方得分:{score}'
        opp_score.highlight = True
        opp_score.color = 31
        paragraph.append(opp_score)
        return paragraph
    chapter.append(gen_team_score())

    return chapter
    

def gen_cards_string(cards):
    string = ''
    for i in range(len(cards)):
        if i != 0 and cards[i] != cards[i - 1]:
            string += ' '
        string += cards[i]
    return string

def gen_player_paragraph(
    name: str,
    name_maxlen: int,
    num_of_cards: int,
    score: int,
    played_cards,
    is_current_player: bool,
    is_head_master: bool,
    is_same_team: bool,
    is_last_player: bool
) -> Paragraph:
    paragraph = []

    player_name = Sentence()
    player_name.highlight = True
    # 如果是同一队的，就用绿色输出，否则用红色
    if is_same_team:
        player_name.color = 32
    else:
        player_name.color = 31
    # 如果该玩家现在在打牌，则将其名字闪烁显示
    if is_current_player:
        player_name.blink = True
    # 如果当前玩家是头科，则在其前面写上
    if is_head_master:
        player_name.string += '头科 '
    else:
        player_name.string += '     '
    # 输出名字
    player_name.string += f'{name:<{name_maxlen}}'
    paragraph.append(player_name)

    player_score = Sentence()
    player_score.highlight = True
    # 如果是同一队的，就用绿色输出，否则用红色
    if is_same_team:
        player_score.color = 32
    else:
        player_score.color = 31
    player_score.string += f'{num_of_cards:>2}张{score:>3}分'
    paragraph.append(player_score)

    player_played_cards = Sentence()
    if is_last_player:
        player_played_cards.underline = True
    player_played_cards.string += gen_cards_string(played_cards)
    paragraph.append(player_played_cards)

    return paragraph

def gen_cards_chapter(cards) -> Chapter:
    chapter = []

    def gen_paragraph(string: str) -> Paragraph:
        sentence = Sentence()
        sentence.string = string
        return [sentence]
    chapter.append(gen_paragraph("你的手牌:"))
    chapter.append(gen_paragraph(gen_cards_string(cards)))

    return chapter
    
def main_interface(
    users_name, client_player, users_score, users_cards_len,
    played_cards, user, now_score, now_player, head_master, last_player,
    his_now_score, his_last_player, is_start
):
    clear_screen()
    # 输出帮助
    help_chapter = gen_help_chapter()
    # 输出得分
    score_chapter = gen_score_chapter(now_score, client_player, users_score)
    name_maxlen = 8
    for i in range(6):
        name_maxlen = max(name_maxlen, columns(users_name[i]))
    # 输出其它玩家
    other_player_chapter = []
    client_player_chapter = []
    for i in range(0, 6):
        player = (client_player + i + 1) % 6
        player_paragraph = gen_player_paragraph(
            name=users_name[player],
            name_maxlen=name_maxlen,
            num_of_cards=users_cards_len[player],
            score=users_score[player],
            played_cards=played_cards[player],
            is_current_player=(player == now_player),
            is_head_master=(player == head_master),
            is_same_team=(player % 2 == client_player % 2),
            is_last_player=(player == last_player)
        )
        if player == client_player:
            client_player_chapter.append(player_paragraph)
        else:
            other_player_chapter.append(player_paragraph)

    cards_chapter = gen_cards_chapter(user.cards)

    """
    一共五部分，从上到下依次为
    1. 帮助注释
    2. 得分
    3. 其他玩家信息
    4. 自己信息
    5. 手牌
    """
    article = [
        help_chapter,
        score_chapter,
        other_player_chapter,
        client_player_chapter,
        cards_chapter,
    ]
    # 统计最终的终端列数
    term_column = 0
    for chapter in article:
        for paragraph in chapter:
            term_column = max(term_column, paragraph_columns(paragraph))
    term_column += 2
    term_column = min(term_column, os.get_terminal_size().columns - 1)

    # 最后的输出
    for chapter in article:
        print_hline(term_column)
        for paragraph in chapter:
            print_paragraph(paragraph, term_column)
    print_hline(term_column)

    # 根据手牌判断播放的音效
    if not is_start:
        playsounds(["start", "open"], True)
    elif last_player == now_player and his_now_score > 0:
        playsound("fen", True, None)
    elif last_player == his_last_player:
        playsound("pass", True, None)
    else:
        last_played_cards = [utils.str_to_int(c) for c in played_cards[last_player]]
        last_played_cards.sort(reverse=True)
        (cardtype, _) = judge_and_transform_cards(last_played_cards)
        assert cardtype != CardType.illegal_type, (last_player, last_played_cards)
        bombs = [
            CardType.black_joker_bomb,
            CardType.red_joker_bomb,
            CardType.normal_bomb
        ]
        if cardtype in bombs:
            if len(last_played_cards) >= 7:
                playsound("bomb3", True, None)
            elif len(last_played_cards) >= 5:
                playsound("bomb2", True, None)
            else:
                playsound("bomb1", True, None)
        else:
            if len(last_played_cards) >= 5:
                playsound("throw2", True, None)
            else:
                playsound("throw1", True, None)


def game_over_interface(client_player, _if_game_over):
    print('\n')
    if client_player % 2 + 1 == (_if_game_over + 2) % 2:
        print('游戏结束，你的队伍获得了胜利', end='')
        if _if_game_over < 0:
            print('，并成功双统')
    else:
        print('游戏结束，你的队伍未能取得胜利', end='')
        if _if_game_over < 0:
            print('，并被对方双统')
    playsound("clap", False, None)