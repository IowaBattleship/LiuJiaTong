from typing import List, Dict, Iterable, Optional

from card import Card
from client.FieldInfo import FieldInfo
from client import playingrules


def _group_by_value(cards: List[Card]) -> Dict[int, List[Card]]:
    """按点数分组手牌，返回 {value -> [Card,...]}，并保证每个列表中卡牌顺序稳定。"""
    by_value: Dict[int, List[Card]] = {}
    for c in cards:
        by_value.setdefault(c.value, []).append(c)
    return by_value


def _find_consecutive_segments(candidates: List[int]) -> List[List[int]]:
    """在已排序的候选点数中找到若干连续段。"""
    segments: List[List[int]] = []
    if not candidates:
        return segments
    cur = [candidates[0]]
    for v in candidates[1:]:
        if v == cur[-1] + 1:
            cur.append(v)
        else:
            segments.append(cur)
            cur = [v]
    segments.append(cur)
    return segments


def _generate_singles(by_value: Dict[int, List[Card]], values_sorted: List[int]) -> Iterable[List[Card]]:
    for v in values_sorted:
        yield [by_value[v][0]]


def _generate_pairs(by_value: Dict[int, List[Card]], values_sorted: List[int]) -> Iterable[List[Card]]:
    for v in values_sorted:
        if len(by_value[v]) >= 2:
            yield by_value[v][:2]


def _generate_triples(by_value: Dict[int, List[Card]], values_sorted: List[int]) -> Iterable[List[Card]]:
    for v in values_sorted:
        if len(by_value[v]) >= 3:
            yield by_value[v][:3]


def _generate_straights(by_value: Dict[int, List[Card]]) -> Iterable[List[Card]]:
    """只考虑不含大小王、不使用大小王补牌的顺子。"""
    card_vals = sorted([v for v in by_value.keys() if 3 <= v <= 14])
    segs = _find_consecutive_segments(card_vals)
    for seg in segs:
        if len(seg) < 5:
            continue
        # 任意长度 >=5 的连续子段都可构成顺子
        for length in range(5, len(seg) + 1):
            for i in range(0, len(seg) - length + 1):
                sub = seg[i : i + length]
                yield [by_value[v][0] for v in sub]


def _generate_straight_pairs(by_value: Dict[int, List[Card]]) -> Iterable[List[Card]]:
    vals = sorted([v for v in by_value.keys() if len(by_value[v]) >= 2 and 3 <= v <= 14])
    segs = _find_consecutive_segments(vals)
    for seg in segs:
        if len(seg) < 2:
            continue
        for length in range(2, len(seg) + 1):
            for i in range(0, len(seg) - length + 1):
                sub = seg[i : i + length]
                combo: List[Card] = []
                for v in sub:
                    combo.extend(by_value[v][:2])
                yield combo


def _generate_straight_triples(by_value: Dict[int, List[Card]]) -> Iterable[List[Card]]:
    vals = sorted([v for v in by_value.keys() if len(by_value[v]) >= 3 and 3 <= v <= 14])
    segs = _find_consecutive_segments(vals)
    for seg in segs:
        if len(seg) < 2:
            continue
        for length in range(2, len(seg) + 1):
            for i in range(0, len(seg) - length + 1):
                sub = seg[i : i + length]
                combo: List[Card] = []
                for v in sub:
                    combo.extend(by_value[v][:3])
                yield combo


def _generate_triple_pairs(by_value: Dict[int, List[Card]], values_sorted: List[int]) -> Iterable[List[Card]]:
    """简单三带二：AAA + BB，不考虑大小王补牌。"""
    triples_vals = [v for v in values_sorted if len(by_value[v]) >= 3]
    pairs_vals = [v for v in values_sorted if len(by_value[v]) >= 2]
    for tv in triples_vals:
        for pv in pairs_vals:
            if pv == tv:
                continue
            combo = by_value[tv][:3] + by_value[pv][:2]
            yield combo


def _generate_flights(by_value: Dict[int, List[Card]], values_sorted: List[int]) -> Iterable[List[Card]]:
    """简单飞机：若干连续三张 + 若干对子（数量与三张组数相同），不考虑大小王补牌。"""
    triple_vals = sorted([v for v in by_value.keys() if len(by_value[v]) >= 3 and 3 <= v <= 14])
    segs = _find_consecutive_segments(triple_vals)
    pair_vals = [v for v in values_sorted if len(by_value[v]) >= 2]
    for seg in segs:
        if len(seg) < 2:
            continue
        # 一个 seg 可能包含 2,3,... 组连续三张，全部尝试
        for length in range(2, len(seg) + 1):
            for i in range(0, len(seg) - length + 1):
                body = seg[i : i + length]
                # 需要与 body 组数相同数量的对子
                need_pairs = length
                # 先按点数从小到大选取 need_pairs 个不同的对子
                candidate_pair_vals = [v for v in pair_vals if v not in body]
                if len(candidate_pair_vals) < need_pairs:
                    continue
                used_pairs = candidate_pair_vals[:need_pairs]
                combo: List[Card] = []
                for v in body:
                    combo.extend(by_value[v][:3])
                for v in used_pairs:
                    combo.extend(by_value[v][:2])
                yield combo


def _generate_bombs(by_value: Dict[int, List[Card]], values_sorted: List[int]) -> Iterable[List[Card]]:
    for v in values_sorted:
        if len(by_value[v]) >= 4:
            yield by_value[v][:4]


def auto_select_cards(info: FieldInfo) -> Optional[List[Card]]:
    """根据当前手牌和场面，生成一手“尽量小但可出的牌”。

    策略（按优先级从低到高依次尝试）：
    - 单张（从小到大）
    - 对子
    - 三张
    - 顺子（不使用大小王补牌，仅使用现有连续点数）
    - 连对（同上）
    - 连三张（同上）
    - 三带二（简单组合：AAA + BB，不考虑大小王凑牌）
    - 飞机（简单组合：连三张 + 若干对子，不考虑大小王凑牌）
    - 炸弹（最后再考虑，避免轻易浪费炸弹）
    """
    hand = list(info.client_cards)
    if not hand:
        return None

    by_value = _group_by_value(hand)
    values_sorted = sorted(by_value.keys())

    last_played = (
        info.users_played_cards[info.last_player]
        if info.last_player != info.client_id
        else None
    )

    generators = [
        lambda: _generate_singles(by_value, values_sorted),
        lambda: _generate_pairs(by_value, values_sorted),
        lambda: _generate_triples(by_value, values_sorted),
        lambda: _generate_straights(by_value),
        lambda: _generate_straight_pairs(by_value),
        lambda: _generate_straight_triples(by_value),
        lambda: _generate_triple_pairs(by_value, values_sorted),
        lambda: _generate_flights(by_value, values_sorted),
        lambda: _generate_bombs(by_value, values_sorted),
    ]

    for gen in generators:
        for combo in gen():
            if playingrules.validate_user_selected_cards(
                combo, info.client_cards, last_played
            ):
                return combo

    return None

