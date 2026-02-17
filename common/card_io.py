"""牌面与字符串/序列化、分数与队伍计算等纯逻辑。供 server 与 client 共用。"""

from core.card import Card


def str_to_int(c: str = "") -> int:
    if "3" <= c <= "9":
        return int(c)
    elif c == "B":
        return 10
    elif c == "J":
        return 11
    elif c == "Q":
        return 12
    elif c == "K":
        return 13
    elif c == "A":
        return 14
    elif c == "2":
        return 15
    elif c == "0":  # joker
        return 16
    elif c == "1":
        return 17
    elif c == "F":  # skip this round
        return 0
    return -1


def int_to_str(x: int = -1) -> str:
    if 3 <= x <= 9:
        return str(x)
    elif x == 10:
        return "B"
    elif x == 11:
        return "J"
    elif x == 12:
        return "Q"
    elif x == 13:
        return "K"
    elif x == 14:
        return "A"
    elif x == 15:
        return "2"
    elif x == 16:  # joker
        return "0"
    elif x == 17:
        return "1"
    elif x == 0:  # skip this round
        return "F"
    return "-"


def strs_to_ints(cards: list[str] | None):
    if cards is None:
        return None
    return [str_to_int(c) for c in cards]


def cards_to_ints(cards: list[Card] | None):
    if cards is None:
        return None
    for c in cards:
        if not isinstance(c, Card):
            raise TypeError("cards must be Card type")
    return [c.value for c in cards]


def cards_to_strs(cards: list[Card] | None):
    if cards is None:
        return None
    for c in cards:
        if not isinstance(c, Card):
            raise TypeError("cards must be Card type")
    return [str(c) for c in cards]


def draw_cards(cards: list[Card], targets: list[str]) -> list[Card]:
    """双指针遍历 cards 和 targets，找到 value 与 targets 中 int 值相同的 card。"""
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


def calculate_score(cards: list[Card]) -> int:
    score = 0
    for c in cards:
        if c.value == 5:
            score += 5
        elif c.value == 10 or c.value == 13:
            score += 10
    return score


def get_card_count(client_cards: list[Card], card: str) -> int:
    """统计某一牌面在手牌中的数量。"""
    result = 0
    for c in client_cards:
        if c.get_cli_str() == card:
            result += 1
    return result


def head_master_in_team(head_master: int, client_id: int) -> bool:
    return head_master in [client_id, (client_id + 2) % 6, (client_id + 4) % 6]


def calculate_head_master_team_score(client_id: int, users_scores: list[int]) -> int:
    return users_scores[client_id] + users_scores[(client_id + 2) % 6] + users_scores[(client_id + 4) % 6]


def calculate_normal_team_score(
    client_id: int, users_cards_num: list[int], users_scores: list[int]
) -> int:
    team_score = 0
    team_score += users_scores[client_id] if users_cards_num[client_id] == 0 else 0
    team_score += users_scores[(client_id + 2) % 6] if users_cards_num[(client_id + 2) % 6] == 0 else 0
    team_score += users_scores[(client_id + 4) % 6] if users_cards_num[(client_id + 4) % 6] == 0 else 0
    return team_score


def calculate_team_scores(
    head_master: int,
    client_id: int,
    users_cards_num: list[int],
    users_scores: list[int],
) -> tuple[int, int]:
    if head_master_in_team(head_master, client_id):
        my_team_score = calculate_head_master_team_score(client_id, users_scores)
        opposing_team_score = calculate_normal_team_score(
            (client_id + 1) % 6, users_cards_num, users_scores
        )
    elif head_master_in_team(head_master, (client_id + 1) % 6):
        opposing_team_score = calculate_head_master_team_score((client_id + 1) % 6, users_scores)
        my_team_score = calculate_normal_team_score(client_id, users_cards_num, users_scores)
    else:
        my_team_score = calculate_normal_team_score(client_id, users_cards_num, users_scores)
        opposing_team_score = calculate_normal_team_score(
            (client_id + 1) % 6, users_cards_num, users_scores
        )
    return my_team_score, opposing_team_score


def last_played(played_cards, player: int) -> int:
    """返回上一位出牌玩家下标。"""
    i = (player - 1 + 6) % 6
    while i != player:
        if len(played_cards[i]) != 0:
            return i
        i = (i - 1 + 6) % 6
    return player
