import threading
from state_machine import GameState
class Game_Var:
    def init_game_env(self):
        assert self.game_lock.locked()
        self.users_cards = [[] for _ in range(6)]
        self.users_score = [0 for _ in range(6)]
        self.users_finished = [False for _ in range(6)] # 玩家打完所有的牌
        self.users_played_cards = [[] for _ in range(6)]  # 场上所出手牌

        self.now_score = 0  # 场上分数
        self.now_player = 0  # 当前出牌玩家
        self.head_master = -1  # 头科玩家下标
        self.last_player = 0  # 上一位出牌玩家
        self.team_score = [0, 0]  # 各队分数
        self.team_out = [0, 0]  # 各队逃出人数
        self.game_over = 0 # 游戏结束状态
    
    def init_global_env(self):
        assert self.users_info_lock.locked()
        assert self.onlooker_lock.locked()
        self.serving_game_round += 1
        self.users_info = []
        self.users_cookie = {}
        self.users_his_state = [GameState.init for _ in range(6)]
        self.users_error = [False for _ in range(6)]
    
    def __init__(self) -> None:
        # 用户登录
        self.users_info_lock = threading.Lock()
        self.serving_game_round = 0
        self.users_info = []
        self.users_cookie = {}
        self.users_his_state = [GameState.init for _ in range(6)] # 用户记录的历史状态
        self.users_error = [False for _ in range(6)] # 用户是否发生异常
        # 牌局变量
        self.game_lock = threading.Lock()
        with self.game_lock:
            self.init_game_env()
        # 玩家
        self.game_init_barrier = threading.Barrier(7)
        self.game_start_barrier = threading.Barrier(7)
        self.send_round_info_barrier = threading.Barrier(7)
        self.recv_player_info_barrier = threading.Barrier(7)
        self.next_turn_barrier = threading.Barrier(7)
        # 旁观者
        self.onlooker_lock = threading.Lock()
        self.onlooker_local_lock = threading.Lock()
        self.onlooker_number = 0
        self.onlooker_barrier = threading.Barrier(1)
        self.onlooker_event = threading.Event()

gvar = Game_Var()