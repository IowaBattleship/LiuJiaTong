from sound import playsound, playsounds
from playingrules import judge_and_transform_cards, CardType
from terminal_printer import *
import utils
import copy

def gen_paragraph(string: str) -> Paragraph:
    sentence = Sentence()
    sentence.string = string
    return [sentence]

def gen_waiting_hall_header_chapter() -> Chapter:
    chapter = [
        gen_paragraph("等待大厅"),
    ]
    return chapter

def gen_waiting_hall_users_chapter(users_name, users_error) -> Chapter:
    chapter = []
    
    for i in range(len(users_name)):
        paragraph = []

        user_name = Sentence()
        user_name.string = users_name[i]
        paragraph.append(user_name)

        user_error = Sentence()
        user_error.string = "离线" if users_error[i] else "在线"
        user_error.highlight = True
        user_error.color = 31 if users_error[i] else 32
        paragraph.append(user_error)

        chapter.append(paragraph)

    return chapter

def waiting_hall_interface(th: TerminalHandler, users_name, users_error):
    header_chapter = gen_waiting_hall_header_chapter()
    users_chapter = gen_waiting_hall_users_chapter(users_name, users_error)
    
    article = [
        header_chapter,
        users_chapter,
    ]
    th.reset_cursor()
    th.update_max_column(article_columns(article))
    print_article(article, th)

def gen_help_chapter() -> Chapter:
    chapter = [
        gen_paragraph("B 代表 10  0 代表 小王  1 代表 大王"),
        gen_paragraph("tab键 补全牌  C键 清空手中的牌"),
        gen_paragraph("左右方向键 改变输入的位置"),
    ]
    return chapter

def gen_score_chapter(
    now_score: int,
    client_player: int,
    users_score
) -> Chapter :
    chapter = []

    def gen_field_score() -> Paragraph:
        prompt = Sentence()
        prompt.string = '当前场上分数:'
        score = Sentence()
        score.string = f'{now_score}'
        score.highlight = True
        if now_score == 0:
            score.highlight = False
        elif now_score <= 30 :
            score.color = 34
        elif now_score <= 80:
            score.color = 33
        else:
            score.color = 33
            score.blink = True
            score.underline = True
        return [prompt, score]
    chapter.append(gen_field_score())

    def gen_team_score() -> Paragraph:
        paragraph = []
        
        own_score = Sentence()
        score = 0
        for i in range(6):
            if i % 2 == client_player % 2:
                score += users_score[i]
        own_score.string = f'己方得分: {score}'
        own_score.highlight = True
        own_score.color = 32
        paragraph.append(own_score)

        opp_score = Sentence()
        score = 0
        for i in range(6):
            if i % 2 != client_player % 2:
                score += users_score[i]
        opp_score.string = f'对方得分: {score}'
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

def gen_player_field_paragraph(
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

    def set_color(sentence: Sentence):
        # 如果是同一队的，就用绿色输出，否则用红色
        if is_same_team:
            sentence.color = 32
        else:
            sentence.color = 31
        sentence.highlight = True

    head_master = Sentence()
    head_master.minwidth = 4
    if is_head_master:
        head_master.string += '头科'
        set_color(head_master)
    paragraph.append(head_master)

    player_name = Sentence()
    player_name.minwidth = name_maxlen
    set_color(player_name)
    # 如果该玩家已经逃出，则将其名字打上删除线
    if num_of_cards == 0:
        player_name.strikethrough = True
    # 如果该玩家现在在打牌，则将其名字闪烁显示并加上*
    if is_current_player:
        player_name.blink = True
    player_name.string += name
    paragraph.append(player_name)

    player_score = Sentence()
    set_color(player_score)
    player_score.string += f'{num_of_cards:>2}张{score:>3}分'
    paragraph.append(player_score)

    player_played_cards = Sentence()
    player_played_cards.minwidth = 20
    if is_last_player:
        player_played_cards.underline = True 
    player_played_cards.string += gen_cards_string(played_cards)
    paragraph.append(player_played_cards)

    return paragraph

def gen_player_cards_paragraph(user_cards) -> Paragraph:
    return gen_paragraph(gen_cards_string(user_cards))

def gen_cards_chapter(is_player, client_cards) -> Chapter:
    chapter = [
        gen_paragraph("你的手牌" + ("(旁观)" if not is_player else "") + ":"),
        gen_paragraph(gen_cards_string(client_cards))
    ]
    return chapter

def main_interface(
    # 客户端变量
    is_start,
    is_player,
    client_cards,
    client_player,
    # 场面信息
    users_name,
    users_score,
    users_cards_num,
    users_cards,
    users_played_cards,
    head_master,
    # 运行时数据
    now_score,
    now_player,
    last_player,
    # 历史数据
    his_now_score, 
    his_last_player,
):
    # 输出帮助
    help_chapter = gen_help_chapter()
    # 输出得分
    score_chapter = gen_score_chapter(now_score, client_player, users_score)
    __users_name = copy.deepcopy(users_name)
    for i in range(6):
        __users_name[i] = " " + ("*" if i == now_player else "") + __users_name[i] + " "
    name_maxlen = 10
    for i in range(6):
        name_maxlen = max(name_maxlen, columns(__users_name[i]))
    # 输出其它玩家
    other_player_chapter = []
    client_player_chapter = []
    for i in range(0, 6):
        player = (client_player + i + 1) % 6
        player_field_paragraph = gen_player_field_paragraph(
            name=__users_name[player],
            name_maxlen=name_maxlen,
            num_of_cards=users_cards_num[player],
            score=users_score[player],
            played_cards=users_played_cards[player],
            is_current_player=(player == now_player),
            is_head_master=(player == head_master),
            is_same_team=(player % 2 == client_player % 2),
            is_last_player=(player == last_player)
        )
        if player == client_player:
            client_player_chapter.append(player_field_paragraph)
        else:
            other_player_chapter.append(player_field_paragraph)

        if users_cards[player] == []:
            continue
        player_cards_paragraph = gen_player_cards_paragraph(users_cards[player])
        if player != client_player:
            other_player_chapter.append(player_cards_paragraph)

    cards_chapter = gen_cards_chapter(is_player, client_cards)

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
    # 最后的输出
    th = TerminalHandler()
    th.update_max_column(article_columns(article))
    th.clear_screen_all()
    th.move_cursor()
    print_article(article, th)

    # 根据手牌判断播放的音效
    if not is_start:
        playsounds(["start", "open"], True)
    elif last_player == now_player and his_now_score > 0:
        playsound("fen", True, None)
    elif last_player == his_last_player:
        playsound("pass", True, None)
    else:
        last_played_cards = [utils.str_to_int(c) for c in users_played_cards[last_player]]
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


def game_over_interface(client_player, if_game_over):
    if (client_player + 1) % 2 == (if_game_over + 2) % 2:
        print('游戏结束，你的队伍获得了胜利', end='')
        if if_game_over < 0:
            print('，并成功双统')
    else:
        print('游戏结束，你的队伍未能取得胜利', end='')
        if if_game_over < 0:
            print('，并被对方双统')
    playsound("clap", False, None)