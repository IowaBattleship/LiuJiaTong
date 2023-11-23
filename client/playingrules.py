import copy
from collections import Counter
from enum import Enum
import utils

'''
3 ~ 15 -> 3 ~ 10 + J Q K A 2
16, 17 -> Joker
关键牌即用于比较俩出牌的大小
'''
# 出牌类型
class CardType(Enum):
    illegal_type = 0
    normal_bomb = 1
    black_joker_bomb = 2
    red_joker_bomb = 3
    straight = 4
    straight_pairs = 5
    straight_triples = 6
    flight = 7
    single = 8
    pair = 9
    triple = 10
    triple_pair = 11


# 尝试凑牌
def try_transform_cards(card_num, rg, joker_num, try_num):
    for i in rg:
        if card_num.get(i, 0) > try_num:
            return False
        if card_num.get(i, 0) < try_num:
            joker_num -= try_num - card_num.get(i, 0)
        if joker_num < 0:  # 大小王不够替换
            return False
    return True


# 判断是否为炸弹，返回（出牌类型，关键牌，转换后牌）
def if_bomb(cards, card_num):
    if len(cards) < 4:
        return CardType.illegal_type, 0

    # 统计相同张数的牌（除大小王外），判断是否只有 1 or 0 种
    sp_type_num = sum([1 for k in card_num.keys() if 3 <= k <= 15])
    if sp_type_num == 1:
        return CardType.normal_bomb, cards[-1]  # 转换可能存在的大小王
    elif sp_type_num != 0:
        return CardType.illegal_type, 0
    elif card_num.get(16, 0) == 4:  # 小王炸
        return CardType.black_joker_bomb, 16
    elif card_num.get(17, 0) == 4:  # 大王炸
        return CardType.red_joker_bomb, 17

    return CardType.illegal_type, 0


# 判断是否为顺子，返回（出牌类型，关键牌，转换后牌）
def if_straight(cards, card_num, type_num, joker_num):
    # 保证为5张牌，且非5单张时有王可替
    if len(cards) != 5 or (type_num.get(1, 0) != 5 and joker_num == 0):
        return CardType.illegal_type, 0

    # 保证除大小王外最大与最小牌相差不超过5
    if cards[joker_num] - cards[-1] + 1 > 5:
        return CardType.illegal_type, 0

    # 最小牌为J时，需要从A开始尝试倒序替换大小王
    # 其他情况从最小牌开始尝试递增替换大小王
    rg = range(14, 9, -1) if cards[-1] > 10 else range(cards[-1], cards[-1] + 5)

    if try_transform_cards(card_num, rg, joker_num, 1):
        return CardType.straight, max(list(rg))
    else:
        return CardType.illegal_type, 0


# 判断是否为连对，返回（出牌类型，关键牌，转换后牌）
def if_straight_pairs(cards, card_num, joker_num):
    # 至少4张牌，且为偶数
    if len(cards) < 4 or len(cards) % 2 == 1:
        return CardType.illegal_type, 0

    pairs_num = int(len(cards) // 2)
    # 连对数不超过12次，且除大小王外最大与最小牌相差不超过连对数
    if pairs_num > 12 or cards[joker_num] - cards[-1] + 1 > pairs_num:
        return CardType.illegal_type, 0

    # 最小牌为J时，需要从A开始尝试倒序替换大小王
    # 其他情况从最小牌开始尝试递增替换大小王
    rg = range(14, 14 - pairs_num, -1) \
        if cards[-1] + pairs_num - 1 > 14 else range(cards[-1], cards[-1] + pairs_num)

    if try_transform_cards(card_num, rg, joker_num, 2):
        return CardType.straight_pairs, max(list(rg))
    else:
        return CardType.illegal_type, 0


# 判断是否为连三张，返回（出牌类型，关键牌，转换后牌）
def if_straight_triples(cards, card_num, joker_num):
    # 至少6张牌，且为3的倍数
    if len(cards) < 6 or len(cards) % 3 != 0:
        return CardType.illegal_type, 0

    triples_num = int(len(cards) // 3)
    # 连三张数不超过12次，且除大小王外最大与最小牌相差不超过连三张数
    if triples_num > 12 or cards[joker_num] - cards[-1] + 1 > triples_num:
        return CardType.illegal_type, 0

    # 最小牌为J时，需要从A开始尝试倒序替换大小王
    # 其他情况从最小牌开始尝试递增替换大小王
    rg = range(14, 14 - triples_num, -1) \
        if cards[-1] + triples_num - 1 > 14 else range(cards[-1], cards[-1] + triples_num)

    if try_transform_cards(card_num, rg, joker_num, 3):
        return CardType.straight_triples, max(list(rg))
    else:
        return CardType.illegal_type, 0


# 尝试将最小牌作为飞机中的三张或对子，返回（能否，剩余王数）
def try_min_card_type(card_num, rg, joker_num, try_num):
    for i in rg:
        if card_num.get(i, 0) < try_num:
            joker_num -= try_num - card_num.get(i, 0)
        if joker_num < 0:  # 大小王不够替换
            return False, 0
        if i in card_num:
            card_num[i] = max(card_num[i] - try_num, 0)
    return True, joker_num


# 判断是否为飞机，返回（出牌类型，关键牌，转换后牌）
def if_flight(cards, card_num, joker_num):
    # 至少10张牌，且为5的倍数
    if len(cards) < 10 or len(cards) % 5 != 0:
        return CardType.illegal_type, 0

    triple_pair_num = int(len(cards) // 5)
    if triple_pair_num > 12:
        return CardType.illegal_type, 0

    rg = range(14, 14 - triple_pair_num, -1) \
        if cards[-1] + triple_pair_num - 1 > 14 else range(cards[-1], cards[-1] + triple_pair_num)

    _card_num = copy.deepcopy(card_num)
    key_card = 0

    # 尝试将最小牌作为对子
    if_pairs, _joker_num = try_min_card_type(_card_num, rg, joker_num, 2)
    if if_pairs:
        min_pair_card = 0
        # 找到剩余非王牌中最小牌
        for i in range(cards[-1], cards[joker_num] + 1):
            if _card_num.get(i, 0) > 0:
                min_pair_card = i
                break

        # 若没找到，则尝试用王作为所有三张
        if min_pair_card == 0:
            # 王必须数量刚好
            if _joker_num == triple_pair_num * 3:
                return CardType.flight, 14
        # 其它情况正常凑连三张
        else:
            _rg = range(14, 14 - triple_pair_num, -1) \
                if min_pair_card + triple_pair_num - 1 > 14 else range(min_pair_card, min_pair_card + triple_pair_num)

            # 凑成功则记录该连三张的最大张作为关键牌
            if try_transform_cards(_card_num, _rg, _joker_num, 3):
                key_card = max(list(_rg))

    _card_num = copy.deepcopy(card_num)
    _key_card = 0

    # 尝试将最小牌作为三张
    if_triples, _joker_num = try_min_card_type(_card_num, rg, joker_num, 3)
    if if_triples:
        # 将凑出的连三张中最大张作为关键牌
        _key_card = max(list(rg))

        min_pair_card = 0
        # 找到剩余非王牌中最小牌
        for i in range(cards[-1], cards[joker_num] + 1):
            if _card_num.get(i, 0) > 0:
                min_pair_card = i
                break

        # 若没找到，则尝试用王作为所有对子
        if min_pair_card == 0:
            # 王必须数量刚好
            # 凑失败则清除关键牌
            if _joker_num != triple_pair_num * 2:
                _key_card = 0
        # 其它情况正常凑连对
        else:
            _rg = range(14, 14 - triple_pair_num, -1) \
                if min_pair_card + triple_pair_num - 1 > 14 else range(min_pair_card, min_pair_card + triple_pair_num)

            # 凑失败则清除关键牌
            if try_transform_cards(_card_num, _rg, _joker_num, 2) is False:
                _key_card = 0

    # 取两次尝试中较大牌型
    if key_card >= _key_card and key_card != 0:
        return CardType.flight, key_card
    elif key_card < _key_card:
        return CardType.flight, _key_card
    else:
        return CardType.illegal_type, 0


# 判断是否为单张，返回（出牌类型，关键牌，转换后牌）
def if_single(cards):
    if len(cards) == 1:
        return CardType.single, cards[-1]
    return CardType.illegal_type, 0


# 判断是否为对子，返回（出牌类型，关键牌，转换后牌）
def if_pair(cards, card_num, type_num, joker_num):
    if len(cards) != 2:
        return CardType.illegal_type, 0

    # AA
    if type_num.get(2, 0) == 1 or card_num.get(16, 0) == 2 or card_num.get(17, 0) == 2:
        return CardType.pair, cards[-1]
    # 0A
    elif joker_num == 1:
        return CardType.pair, cards[-1]

    return CardType.illegal_type, 0


# 判断是否为三张，返回（出牌类型，关键牌，转换后牌）
def if_triple(cards, card_num, type_num, joker_num):
    if len(cards) != 3:
        return CardType.illegal_type, 0

    # AAA
    if type_num.get(3, 0) == 1 or card_num.get(16, 0) == 3 or card_num.get(17, 0) == 3:
        return CardType.triple, cards[0]
    # 0AA or 00A
    elif (joker_num == 1 and type_num.get(2, 0) == 1) or (joker_num == 2 and type_num.get(1, 0) == 1):
        return CardType.triple, cards[-1]

    return CardType.illegal_type, 0


# 找到手牌中满足牌数的最大的牌
def find_max_card(card_num, target, if_joker=False):
    max_card = 17 if if_joker else 15
    for i in range(max_card, 2, -1):
        if card_num.get(i, 0) == target:
            return i
    return 0


# 判断是否为三带二，返回（出牌类型，关键牌，转换后牌）
def if_triple_pair(cards, card_num, type_num, joker_num):
    if len(cards) != 5:
        return CardType.illegal_type, 0

    # AAABB
    if (type_num.get(3, 0) == 1 and type_num.get(2, 0) == 1) or \
            (card_num.get(16, 0) == 3 and card_num.get(17, 0) == 2) or \
            (card_num.get(16, 0) == 2 and card_num.get(17, 0) == 3):
        return CardType.triple_pair, find_max_card(card_num, 3, True)
    else:
        # 0AABB
        if joker_num == 1 and type_num.get(2, 0) == 2:
            return CardType.triple_pair, cards[1]
        # 0AAAB
        elif joker_num == 1 and type_num.get(3, 0) == 1 and type_num.get(1, 0) == 1:
            return CardType.triple_pair, find_max_card(card_num, 3)
        # 00AAB (0 0 A A B or 0 0 B A A)
        elif joker_num == 2 and type_num.get(2, 0) == 1 and type_num.get(1, 0) == 1:
            return CardType.triple_pair, find_max_card(card_num, 2)
        # 000AB
        elif joker_num == 3 and type_num.get(1, 0) == 2:
            return CardType.triple_pair, cards[3]

    return CardType.illegal_type, 0


# 判断出牌类型并转换大小王，确认关键牌
def judge_and_transform_cards(cards: list[int]):
    assert sorted(cards, reverse=True) == cards, cards
    card_num = dict(Counter(cards))  # 统计每种牌有多少张
    type_num = dict(Counter([v for k, v in card_num.items() if k <= 15]))  # 统计除去王牌 相同张数的牌有多少种

    # 1 2 3
    card_type, key_card = if_bomb(cards, card_num)
    if card_type is not CardType.illegal_type:
        return card_type, key_card

    joker_num = card_num.get(16, 0) + card_num.get(17, 0)

    # 8
    card_type, key_card = if_single(cards)
    if card_type is not CardType.illegal_type:
        return card_type, key_card

    # 9
    card_type, key_card = if_pair(cards, card_num, type_num, joker_num)
    if card_type is not CardType.illegal_type:
        return card_type, key_card

    # 10
    card_type, key_card = if_triple(cards, card_num, type_num, joker_num)
    if card_type is not CardType.illegal_type:
        return card_type, key_card

    # 11
    card_type, key_card = if_triple_pair(cards, card_num, type_num, joker_num)
    if card_type is not CardType.illegal_type:
        return card_type, key_card

    # 4
    card_type, key_card = if_straight(cards, card_num, type_num, joker_num)
    if card_type is not CardType.illegal_type:
        return card_type, key_card

    # 5
    card_type, key_card = if_straight_pairs(cards, card_num, joker_num)
    if card_type is not CardType.illegal_type:
        return card_type, key_card

    # 6
    card_type, key_card = if_straight_triples(cards, card_num, joker_num)
    if card_type is not CardType.illegal_type:
        return card_type, key_card

    # 7
    card_type, key_card = if_flight(cards, card_num, joker_num)
    if card_type is not CardType.illegal_type:
        return card_type, key_card

    return CardType.illegal_type, 0


# 判断为首个出牌时，输入是否合法
def if_first_input_legal(user_input: list[int]):
    type_card, key_card = judge_and_transform_cards(user_input)
    if type_card is not CardType.illegal_type:
        return True
    return False


# 判断存在上家出牌时，输入是否合法
def if_not_first_input_legal(user_input, last_played_cards):
    card_len = len(user_input)
    last_card_len = len(last_played_cards)
    type_card, key_card = judge_and_transform_cards(user_input)
    if type_card is CardType.illegal_type:
        return False
    last_type_card, last_key_card = judge_and_transform_cards(last_played_cards)

    # 先判断炸弹
    last_if_bomb = 0
    if 1 <= last_type_card.value <= 3:
        last_if_bomb = last_type_card.value
    _if_bomb = 0
    if 1 <= type_card.value <= 3:
        _if_bomb = type_card.value

    if last_if_bomb != 0 and _if_bomb == 0:
        return False
    elif last_if_bomb == 0 and _if_bomb != 0:
        return True
    elif last_if_bomb != 0 and _if_bomb != 0:
        # 都是炸弹 先判断大小王炸与普通炸弹的大小
        if (last_if_bomb > _if_bomb and card_len < 9) or (last_if_bomb < _if_bomb and last_card_len > 8):
            return False
        elif (last_if_bomb > _if_bomb and card_len > 8) or (last_if_bomb < _if_bomb and last_card_len < 9):
            return True
        # 比长度
        elif last_card_len > card_len:
            return False
        elif last_card_len < card_len:
            return True
        # 比大小
        else:
            return key_card > last_key_card

    # 都不是炸弹先判断长度是否一致，再直接比较关键牌
    if last_card_len != card_len:
        return False
    return key_card > last_key_card


# 判断手中牌是否足够出，并返回输入牌的分数
def if_enough_card(user_input, user_card):
    input_num = dict(Counter(user_input))  # 统计每种牌有多少张
    if user_card is not None:
        card_num = dict(Counter(user_card))
        for k, v in input_num.items():
            if card_num.get(k, 0) < v:
                return False, 0
    return True, input_num.get(5, 0) * 5 + (input_num.get(10, 0) + input_num.get(13, 0)) * 10


# 判断输入是否合法，若合法，返回重新排列后的输入
def if_input_legal(
    user_input: list[int],
    user_card: list[int],
    last_played_cards: list[int]
):
    assert user_input is not None
    # 判断输入字符是否合法，并判断是否skip
    for x in user_input:
        if x < 0 or (len(user_input) > 1 and x == 0):
            return False, 0
    if user_input == [0]:
        return last_played_cards is not None, 0

    _if_enough, score = if_enough_card(user_input, user_card)
    if _if_enough is False:
        return False, 0

    _user_input = sorted(user_input, reverse=True)
    if last_played_cards is None:
        return if_first_input_legal(_user_input), score
    else:
        _last_played_cards = sorted(last_played_cards, reverse=True)
        return if_not_first_input_legal(_user_input, _last_played_cards), score