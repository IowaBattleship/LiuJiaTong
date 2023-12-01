import os
import logger
from game_vars import gvar
from state_machine import GameState, GameStateMachine

class Onlooker(GameStateMachine):
    def game_start(self): 
        raise RuntimeError("unsupport state")
    def game_over(self): 
        print(f"onlooker {self.pid} exit")
        self.close()
    def onlooker_register(self): 
        while True:
            if_locked = gvar.onlooker_lock.acquire(timeout=1)
            if self.serving_game_round < gvar.serving_game_round:
                print(os.getpid(), "onlooker register failed: game end")
                self.error = True
            if if_locked and self.error is False:
                gvar.onlooker_number += 1
            if if_locked:
                gvar.onlooker_lock.release()
            if if_locked or self.error:
                break
    def next_turn(self): 
        raise RuntimeError("unsupport state")
    def send_field_info(self): 
        try:
            self.tcp_handler.send_field_info()
        except Exception as e:
            print(os.getpid(), "error :", e)
            self.error = True
    def send_round_info(self): 
        if self.error:
            return
        try:
            self.tcp_handler.send_round_info()
        except Exception as e:
            print(os.getpid(), "error :", e)
            self.error = True
    def recv_player_info(self): 
        raise RuntimeError("unsupport state")
    def init_sync(self): 
        raise RuntimeError("unsupport state")
    def onlooker_sync(self): 
        gvar.onlooker_event.wait()
        # 这里放松了条件，因为在下一个同步点之前数据是只读的
        self.__game_over = gvar.game_over
    def game_start_sync(self): 
        raise RuntimeError("unsupport state")
    def send_round_info_sync(self): 
        if self.error:
            assert gvar.onlooker_lock.locked()
            with gvar.onlooker_local_lock:
                gvar.onlooker_number -= 1
        gvar.onlooker_barrier.wait()
    def recv_player_info_sync(self): 
        raise RuntimeError("unsupport state")
    def next_turn_sync(self): 
        raise RuntimeError("unsupport state")
    
    # 这个代码太tm抽象了，看我画的drawio的图，为了支持断线重连真不容易……
    def get_next_state(self) -> bool:
        if self.state == GameState.init:
            self.state = GameState.onlooker_register
        elif self.state == GameState.onlooker_register:
            if self.error:
                self.state = GameState.game_over
            else:
                self.state = GameState.send_field_info
        elif self.state == GameState.send_field_info:
            self.state = GameState.onlooker_sync
        elif self.state == GameState.onlooker_sync:
            self.state = GameState.send_round_info
        elif self.state == GameState.send_round_info:
            self.state = GameState.send_round_info_sync
        elif self.state == GameState.send_round_info_sync:
            if self.error or self.__game_over != 0:
                self.state = GameState.game_over
            else:
                self.state = GameState.onlooker_sync
        elif self.state == GameState.game_over:
            return False
        else:
            raise RuntimeError("unsupport state")
        logger.info(f"onlooker: state={self.state}, error={self.error}")
        return True
    
    def __init__(
        self,
        client_player: int,
        serving_game_round: int,
        tcp_handler,
    ):
        super().__init__()
        self.client_player = client_player
        self.serving_game_round = serving_game_round
        self.tcp_handler = tcp_handler
        _, self.pid = tcp_handler.client_address
        
        self.error = False
        self.__game_over = 0
    
    def send_data(self, data):
        self.tcp_handler.send_data(data)
    
    def recv_data(self):
        return self.tcp_handler.recv_data()
    
    def close(self):
        self.tcp_handler.close()
