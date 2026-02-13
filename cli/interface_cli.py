"""CLI 端用户接口渲染：等待大厅、牌局界面、游戏结束等控制台输出逻辑。"""

import copy
import sys
from cli.terminal_printer import (
    TerminalHandler, Sentence, Paragraph, Chapter, Article,
    columns, article_columns, print_article,
)

ASCII_ART = r'''
    __    _              ___          ______
   / /   (_)_  __       / (_)___ _   /_  __/___  ____  ____ _
  / /   / / / / /  __  / / / __ `/    / / / __ \/ __ \/ __ `/
 / /___/ / /_/ /  / /_/ / / /_/ /    / / / /_/ / / / / /_/ /
/_____/_/\__,_/   \____/_/\__,_/    /_/  \____/_/ /_/\__, /
                                                    /____/
'''


def _gen_paragraph(string: str, color: int = 0, highlight: bool = False) -> Paragraph:
    sentence = Sentence()
    sentence.string = string
    if color > 0:
        sentence.color = color
    if highlight:
        sentence.highlight = True
    return [sentence]


def _gen_ascii_art_chapter() -> Chapter:
    """LIUJIATONG 大标题，青色高亮。"""
    # 使用 splitlines() 并去除 \r，避免 Windows CRLF 导致首行向左错位
    lines = ASCII_ART.rstrip().replace("\r", "").splitlines()
    return [_gen_paragraph(line, color=36, highlight=True) for line in lines]


def _gen_waiting_hall_header_chapter() -> Chapter:
    """等待大厅标题，黄色高亮。"""
    return [_gen_paragraph("等待大厅", color=33, highlight=True)]


def _gen_waiting_hall_users_chapter(users_name, users_error) -> Chapter:
    """玩家列表：玩家名青色，在线绿色，离线红色。"""
    chapter = []
    for i in range(len(users_name)):
        paragraph = []
        user_name = Sentence()
        user_name.string = users_name[i] if users_name[i] else "(空)"
        user_name.color = 36  # 青色
        user_name.highlight = True
        paragraph.append(user_name)
        user_error = Sentence()
        user_error.string = "离线" if users_error[i] else "在线"
        user_error.highlight = True
        user_error.color = 31 if users_error[i] else 32  # 离线红，在线绿
        paragraph.append(user_error)
        chapter.append(paragraph)
    return chapter


def _gen_help_chapter() -> Chapter:
    return [
        _gen_paragraph("B 代表 10  0 代表 小王  1 代表 大王"),
        _gen_paragraph("tab键 补全牌  C键 清空手中的牌"),
        _gen_paragraph("左右方向键 改变输入的位置"),
    ]


def _gen_score_chapter(now_score: int, client_player: int, users_score) -> Chapter:
    chapter = []

    def gen_field_score() -> Paragraph:
        prompt = Sentence()
        prompt.string = "当前场上分数:"
        score = Sentence()
        score.string = f"{now_score}"
        score.highlight = True
        if now_score == 0:
            score.highlight = False
        elif now_score <= 30:
            score.color = 34
        elif now_score <= 80:
            score.color = 33
        else:
            score.color = 33
            score.blink = True
            score.underline = True
        return [prompt, score]

    def gen_team_score() -> Paragraph:
        paragraph = []
        own_score = Sentence()
        score = sum(users_score[i] for i in range(6) if i % 2 == client_player % 2)
        own_score.string = f"己方得分: {score}"
        own_score.highlight = True
        own_score.color = 32
        paragraph.append(own_score)
        opp_score = Sentence()
        score = sum(users_score[i] for i in range(6) if i % 2 != client_player % 2)
        opp_score.string = f"对方得分: {score}"
        opp_score.highlight = True
        opp_score.color = 31
        paragraph.append(opp_score)
        return paragraph

    chapter.append(gen_field_score())
    chapter.append(gen_team_score())
    return chapter


def _gen_cards_string(cards) -> str:
    string = ""
    for i in range(len(cards)):
        if i != 0 and cards[i].get_cli_str() != cards[i - 1].get_cli_str():
            string += " "
        string += cards[i].get_cli_str()
    return string


def _gen_player_field_paragraph(
    name: str, name_maxlen: int, num_of_cards: int, score: int,
    played_cards, is_current_player: bool, is_head_master: bool,
    is_same_team: bool, is_last_player: bool,
) -> Paragraph:
    paragraph = []

    def set_color(sentence: Sentence):
        sentence.color = 32 if is_same_team else 31
        sentence.highlight = True

    head_master = Sentence()
    head_master.minwidth = 4
    if is_head_master:
        head_master.string += "头科"
        set_color(head_master)
    paragraph.append(head_master)

    player_name = Sentence()
    player_name.minwidth = name_maxlen
    set_color(player_name)
    if num_of_cards == 0:
        player_name.strikethrough = True
    if is_current_player:
        player_name.blink = True
    player_name.string += name
    paragraph.append(player_name)

    player_score = Sentence()
    set_color(player_score)
    player_score.string += f"{num_of_cards:>2}张{score:>3}分"
    paragraph.append(player_score)

    player_played_cards = Sentence()
    player_played_cards.minwidth = 20
    if is_last_player:
        player_played_cards.underline = True
    player_played_cards.string += _gen_cards_string(played_cards)
    paragraph.append(player_played_cards)
    return paragraph


def _gen_player_cards_paragraph(user_cards) -> Paragraph:
    return _gen_paragraph(_gen_cards_string(user_cards))


def _gen_cards_chapter(is_player, client_cards) -> Chapter:
    return [
        _gen_paragraph("你的手牌" + ("(旁观)" if not is_player else "") + ":"),
        _gen_paragraph(_gen_cards_string(client_cards)),
    ]


def render_waiting_hall(users_name, users_error) -> None:
    """将等待大厅信息渲染到控制台（先清屏再打印，与游戏界面一致）。"""
    ascii_chapter = _gen_ascii_art_chapter()
    header_chapter = _gen_waiting_hall_header_chapter()
    users_chapter = _gen_waiting_hall_users_chapter(users_name, users_error)
    article = [ascii_chapter, header_chapter, users_chapter]
    th = TerminalHandler()
    th.move_cursor(1, 1)
    th.clear_screen_all()
    th.update_max_column(article_columns(article))
    print_article(article, th)
    th.flush()
    sys.stdout.flush()


def render_field_info(
    is_start, is_player, client_cards, client_player,
    users_name, users_score, users_cards_num, users_cards,
    users_played_cards, head_master, now_score, now_player, last_player,
    his_now_score, his_last_player,
) -> None:
    """将牌局信息渲染到控制台（从等待大厅切换到游戏界面时需清屏重绘）。"""
    help_chapter = _gen_help_chapter()
    score_chapter = _gen_score_chapter(now_score, client_player, users_score)
    __users_name = copy.deepcopy(users_name)
    for i in range(6):
        __users_name[i] = " " + ("*" if i == now_player else "") + __users_name[i] + " "
    name_maxlen = 10
    for i in range(6):
        name_maxlen = max(name_maxlen, columns(__users_name[i]))

    other_player_chapter = []
    client_player_chapter = []
    for i in range(6):
        player = (client_player + i + 1) % 6
        player_field_paragraph = _gen_player_field_paragraph(
            name=__users_name[player],
            name_maxlen=name_maxlen,
            num_of_cards=users_cards_num[player],
            score=users_score[player],
            played_cards=users_played_cards[player],
            is_current_player=(player == now_player),
            is_head_master=(player == head_master),
            is_same_team=(player % 2 == client_player % 2),
            is_last_player=(player == last_player),
        )
        if player == client_player:
            client_player_chapter.append(player_field_paragraph)
        else:
            other_player_chapter.append(player_field_paragraph)
        if users_cards[player] == []:
            continue
        player_cards_paragraph = _gen_player_cards_paragraph(users_cards[player])
        if player != client_player:
            other_player_chapter.append(player_cards_paragraph)

    cards_chapter = _gen_cards_chapter(is_player, client_cards)
    article = [help_chapter, score_chapter, other_player_chapter, client_player_chapter, cards_chapter]

    th = TerminalHandler()
    th.move_cursor(1, 1)
    th.clear_screen_all()
    th.update_max_column(article_columns(article))
    print_article(article, th)
    th.flush()
    sys.stdout.flush()


def render_game_over(client_player: int, if_game_over: int) -> None:
    """将游戏结束信息渲染到控制台。"""
    if (client_player + 1) % 2 == (if_game_over + 2) % 2:
        print("游戏结束，你的队伍获得了胜利", end="")
        if if_game_over < 0:
            print("，并成功双统")
    else:
        print("游戏结束，你的队伍未能取得胜利", end="")
        if if_game_over < 0:
            print("，并被对方双统")


def create_cli_handler(play_sound_fn):
    """
    创建 CLI 端 UI 处理器，接收 interface 的通知并渲染到控制台。
    play_sound_fn: 播放音效的回调，由 interface 注入。
    """

    class CLIHandler:
        def on_waiting_hall(self, users_name, users_error):
            render_waiting_hall(users_name, users_error)

        def on_field_info(self, field_info):
            info = field_info
            render_field_info(
                info.start_flag, info.is_player, info.client_cards, info.client_id,
                info.user_names, info.user_scores, info.users_cards_num, info.users_cards,
                info.users_played_cards, info.head_master, info.now_score, info.now_player,
                info.last_player, info.his_now_score, info.his_last_player,
            )

        def on_game_over(self, client_player: int, if_game_over: int):
            render_game_over(client_player, if_game_over)
            play_sound_fn("clap", False, None)

    return CLIHandler()
