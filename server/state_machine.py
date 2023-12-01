from abc import ABC, abstractmethod
from enum import Enum, auto

'''
设计原则：
1. 每个状态要么有同步操作(就考虑event,barrier.lock感觉可以不算),要么有网络(socket)
不允许一个状态既是同步又有网络,但是可以两个都没有
2. 对于同步操作,同步后的状态理应啥都不能相信，防止出现数据竞争
所以需要在同步操作之前将一些关键的全局变量进行保存
当然这个设计原则有点离谱,相当于需要进行大量的变量的地址迁移
看情况适当放松,比如两个同步点之间的所有状态对全局内存是只读就不需要保存
'''

class GameState(Enum):
    init = auto(),
    game_start = auto(),
    game_over = auto(),
    onlooker_register = auto(),
    next_turn = auto(),
    # socket
    send_field_info = auto(),
    send_round_info = auto(),
    recv_player_info = auto(),
    # synchronize
    init_sync = auto(),
    onlooker_sync = auto(),
    game_start_sync = auto(),
    send_round_info_sync = auto(),
    recv_player_info_sync = auto(),
    next_turn_sync = auto(),


class GameStateMachine(ABC):
    @abstractmethod
    def game_start(self): 
        pass
    @abstractmethod
    def game_over(self): 
        pass
    @abstractmethod
    def onlooker_register(self): 
        pass
    @abstractmethod
    def next_turn(self): 
        pass
    @abstractmethod
    def send_field_info(self): 
        pass
    @abstractmethod
    def send_round_info(self): 
        pass
    @abstractmethod
    def recv_player_info(self): 
        pass
    @abstractmethod
    def init_sync(self): 
        pass
    @abstractmethod
    def onlooker_sync(self): 
        pass
    @abstractmethod
    def game_start_sync(self): 
        pass
    @abstractmethod
    def send_round_info_sync(self): 
        pass
    @abstractmethod
    def recv_player_info_sync(self): 
        pass
    @abstractmethod
    def next_turn_sync(self): 
        pass
    
    def __init__(self):
        self.state = GameState.init
        self.__state_function_set = {
            GameState.game_start: self.game_start,
            GameState.game_over: self.game_over,
            GameState.onlooker_register: self.onlooker_register,
            GameState.next_turn: self.next_turn,
            GameState.send_field_info: self.send_field_info,
            GameState.send_round_info: self.send_round_info,
            GameState.recv_player_info: self.recv_player_info,
            GameState.init_sync: self.init_sync,
            GameState.onlooker_sync: self.onlooker_sync,
            GameState.game_start_sync: self.game_start_sync,
            GameState.send_round_info_sync: self.send_round_info_sync,
            GameState.recv_player_info_sync: self.recv_player_info_sync,
            GameState.next_turn_sync: self.next_turn_sync,
        }

    @abstractmethod
    def get_next_state(self) -> bool:
        pass

    def run(self):
        while self.get_next_state():
            self.__state_function_set[self.state]()