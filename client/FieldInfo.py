from card import Card

class FieldInfo:
    def __init__(
        self,
        start_flag  : bool,       # 游戏是否开始
        is_player   : bool,       # 当前用户是否是玩家

        # 玩家信息
        client_id   : int,        # 当前玩家的ID
        client_cards: list[Card], # 当前玩家的手牌

        # 场面信息
        user_names        : list[str],        # 所有玩家的名字
        user_scores       : list[int],        # 所有玩家的分数
        users_cards_num   : list[int],        # 所有玩家的牌数
        users_cards       : list[list[Card]], # 所有玩家的牌
        users_played_cards: list[list[Card]], # 所有玩家的出牌
        head_master       : int,              # 头科
        now_score         : int,              # 场面分数
        now_player        : int,              # 当前出牌的玩家
        last_player       : int,              # 上一出牌的玩家
        his_now_score     : int,              # 历史场上分数
        his_last_player   : int,              # 历史上一出牌的玩家
    ):
        self.start_flag = start_flag
        self.is_player = is_player
        self.client_id = client_id
        self.client_cards = client_cards
        self.user_names = user_names
        self.user_scores = user_scores
        self.users_cards_num = users_cards_num
        self.users_cards = users_cards
        self.users_played_cards = users_played_cards
        self.head_master = head_master
        self.now_score = now_score
        self.now_player = now_player
        self.last_player = last_player
        self.his_now_score = his_now_score
        self.his_last_player = his_last_player