"""牌面与牌局相关工具：薄封装，统一从 common.card_io 导出，便于 client 现有代码兼容。"""

from common.card_io import (
    str_to_int,
    int_to_str,
    strs_to_ints,
    cards_to_ints,
    cards_to_strs,
    draw_cards,
    calculate_score,
    get_card_count,
    head_master_in_team,
    calculate_head_master_team_score,
    calculate_normal_team_score,
    calculate_team_scores,
    last_played,
)

__all__ = [
    "str_to_int",
    "int_to_str",
    "strs_to_ints",
    "cards_to_ints",
    "cards_to_strs",
    "draw_cards",
    "calculate_score",
    "get_card_count",
    "head_master_in_team",
    "calculate_head_master_team_score",
    "calculate_normal_team_score",
    "calculate_team_scores",
    "last_played",
]
