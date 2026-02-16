import random
import copy
import threading
import core.logger as logger

from core import card
from game_vars import gvar
from state_machine import GameState, GameStateMachine


# 初始化牌
def init_cards():
    assert gvar.game_lock.locked()
    all_cards = card.generate_cards()
    random.shuffle(all_cards)

    for i in range(0, 6):
        user_cards = sorted([all_cards[j] for j in range(i, len(all_cards), 6)]) # 模拟发牌
        gvar.users_cards[i] = copy.deepcopy(user_cards) # 11/03/2024: 支持花色，现在以list[Card]类型保存

'''
判断游戏是否结束
返回值
0 表示没有结束 
1, -1 分别表示偶数队获胜,双统
2, -2 分别表示奇数队获胜,双统
'''
def if_game_over() -> bool:
    assert gvar.game_lock.locked()
    # 没有头科肯定没有结束
    if gvar.head_master == -1:
        return 0
    # 根据各队分数以及逃出人数判断
    for i in range(2):
        if gvar.team_score[i] >= 200 and gvar.team_out[i] == 3 and gvar.team_out[1 - i] == 0:
            return -(i + 1)
        elif (gvar.team_score[i] >= 200 and gvar.team_out[1 - i] != 0) or gvar.team_out[i] == 3:
            return i + 1
    return 0

def if_run_out(player: int) -> bool:
    assert gvar.game_lock.locked()
    return len(gvar.users_cards[player]) == 0

# 下一位玩家出牌
def set_next_player():
    assert gvar.game_lock.locked()
    gvar.now_player = (gvar.now_player + 1) % 6
    while gvar.users_finished[gvar.now_player]:
        gvar.now_player = (gvar.now_player + 1) % 6

def get_next_turn():
    assert gvar.game_lock.locked()
    # skip
    if gvar.users_played_cards[gvar.now_player][0] == 'F':
        gvar.users_played_cards[gvar.now_player].clear()
    else:
        gvar.last_player = gvar.now_player
    
    assert gvar.last_player != -1
    # 此轮逃出，更新队伍信息、头科
    if if_run_out(gvar.now_player):
        gvar.team_out[gvar.now_player % 2] += 1
        if gvar.head_master == -1:
            gvar.head_master = gvar.now_player

    # 更新一下打牌的user
    set_next_player()
    # 玩家是否打完所有的牌
    # 不在打完之后马上结算是因为玩家的分没拿
    # 考虑到有多个人同时打完牌的情况，得用循环
    while if_run_out(gvar.now_player) and gvar.last_player != gvar.now_player:
        gvar.users_finished[gvar.now_player] = True
        gvar.users_played_cards[gvar.now_player].clear()
        set_next_player()

    # 一轮结束，统计此轮信息
    if gvar.last_player == gvar.now_player:
        # 统计用户分数
        gvar.users_score[gvar.now_player] += gvar.now_score
        # 初始化场上分数
        gvar.now_score = 0
        # 如果刚好在此轮逃出，第一个出牌的人就要改变
        if if_run_out(gvar.now_player):
            gvar.users_finished[gvar.now_player] = True
            gvar.users_played_cards[gvar.now_player].clear()
            set_next_player()
            gvar.last_player = -1
    # 清除当前玩家的场上牌
    gvar.users_played_cards[gvar.now_player].clear()

def check_game_over():
    assert gvar.game_lock.locked()
    # 重新统计队伍得分
    gvar.team_score = [0, 0]
    for i in range(6):
        # 有头科的队伍统计所有成员分数
        if gvar.head_master != -1 and gvar.head_master % 2 == i % 2:
            gvar.team_score[i % 2] += gvar.users_score[i]
        # 如果用户逃出，记录成员分数
        elif if_run_out(i):
            gvar.team_score[i % 2] += gvar.users_score[i]
    # 检查游戏是否结束
    gvar.game_over = if_game_over()

def take_turn_log():
    assert gvar.game_lock.locked()
    logger.info(f"Manager: now_player {gvar.now_player}, team_score {gvar.team_score}, team_out {gvar.team_out}, game_over {gvar.game_over}")

class Manager(GameStateMachine):
    # 私有方法
    def __update_local_cache(self):
        with gvar.game_lock:
            self.__game_over = gvar.game_over
    # 抽象类方法
    def game_start(self): 
        with gvar.users_info_lock:
            logger.info(f"Manager: New game --- Round {gvar.serving_game_round}")
        with gvar.game_lock:
            gvar.init_game_env()
            init_cards()  # 初始化牌并发牌

    def game_over(self): 
        with gvar.users_info_lock:
            gvar.init_global_env(self.static_user_order)
    def onlooker_register(self): 
        raise RuntimeError("Unsupport state")
    def next_turn(self): 
        with gvar.game_lock:
            get_next_turn()
            check_game_over()
            take_turn_log()
    def send_waiting_hall_info(self):
        raise RuntimeError("Unsupport state")
    def send_field_info(self): 
        raise RuntimeError("Unsupport state")
    def send_round_info(self): 
        # 会在send_round_info_sync处放掉
        gvar.onlooker_lock.acquire()
        # barrier要考虑自己
        gvar.onlooker_onlooker_sync_barrier = threading.Barrier(gvar.onlooker_number + 1)
        gvar.onlooker_send_round_info_barrier = threading.Barrier(gvar.onlooker_number + 1)
        gvar.onlooker_event.set()
        # 这里先wait等待所有的旁观者线程和manager线程都确认可以发送了
        gvar.onlooker_onlooker_sync_barrier.wait()
        # 然后再将其清理掉，否则万一先clear了，还没闯进来的旁观者线程就阻塞了，manager线程也寄了
        gvar.onlooker_event.clear()
        # 最后等待所有的旁观者线程发送完信息
        gvar.onlooker_send_round_info_barrier.wait()
    def recv_player_info(self): 
        raise RuntimeError("Unsupport state")
    def init_sync(self): 
        gvar.game_init_barrier.wait()
        gvar.game_init_barrier.reset()
    def onlooker_sync(self): 
        raise RuntimeError("Unsupport state")
    def game_start_sync(self): 
        gvar.game_start_barrier.wait()
        gvar.game_start_barrier.reset()
        # 这里放松了条件，因为在下一个同步点之前数据是只读的
        self.__update_local_cache()
        assert gvar.onlooker_lock.locked()
        # 在游戏还没开始前由manager将其锁住
        gvar.onlooker_lock.release()
    def send_round_info_sync(self): 
        gvar.send_round_info_barrier.wait()
        gvar.send_round_info_barrier.reset()
        # 如果游戏还没结束，放掉send_round_info设置的锁
        # 否则一直保持锁直到下一局游戏开始(game_start_sync)
        if self.__game_over == 0:
            gvar.onlooker_lock.release()
    def recv_player_info_sync(self): 
        gvar.recv_player_info_barrier.wait()
        gvar.recv_player_info_barrier.reset()
    def next_turn_sync(self): 
        gvar.next_turn_barrier.wait()
        gvar.next_turn_barrier.reset()
        # 这里放松了条件，因为在下一个同步点之前数据是只读的
        self.__update_local_cache()
    
    # 这个代码太tm抽象了，看我画的drawio的图，为了支持断线重连真不容易……
    def get_next_state(self) -> bool:
        if self.state == GameState.init:
            self.state = GameState.init_sync
        elif self.state == GameState.init_sync:
            self.state = GameState.game_start
        elif self.state == GameState.game_start:
            self.state = GameState.game_start_sync
        elif self.state == GameState.game_start_sync:
            self.state = GameState.send_round_info
        elif self.state == GameState.send_round_info:
            self.state = GameState.send_round_info_sync
        elif self.state == GameState.send_round_info_sync:
            if self.__game_over != 0:
                self.state = GameState.game_over
            else:
                self.state = GameState.recv_player_info_sync
        elif self.state == GameState.recv_player_info_sync:
            self.state = GameState.next_turn
        elif self.state == GameState.next_turn:
            self.state = GameState.next_turn_sync
        elif self.state == GameState.next_turn_sync:
            self.state = GameState.send_round_info
        elif self.state == GameState.game_over:
            self.state = GameState.init_sync
        else:
            raise RuntimeError("Unsupport state")
        logger.info(f"Manager: {self.state}")
        return True

    def __init__(self, static_user_order):
        super().__init__()
        self.static_user_order = static_user_order
        # 在游戏还没开始前由manager将其锁住
        gvar.onlooker_lock.acquire()
        with gvar.users_info_lock:
            gvar.init_global_env(self.static_user_order)
        self.__update_local_cache()
