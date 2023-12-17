import logger
from game_vars import gvar
from state_machine import GameState, GameStateMachine

class Onlooker(GameStateMachine):
    def game_start(self): 
        raise RuntimeError("Unsupport state")
    def game_over(self): 
        print(f"Onlooker {self.pid} exit")
        self.tcp_handler.close()
    def onlooker_register(self): 
        try:
            while True:
                if_locked = gvar.onlooker_lock.acquire(timeout=1)
                with gvar.users_info_lock:
                    if self.serving_game_round < gvar.serving_game_round:
                        raise RuntimeError("Game end")
                if if_locked:
                    gvar.onlooker_number += 1
                    gvar.onlooker_lock.release()
                    break
        except ConnectionResetError as e:
            print(f"\x1b[31m\x1b[1mOnlooker {self.pid}({self.state}) error: {e}\x1b[0m")
            self.error = True
    def next_turn(self): 
        raise RuntimeError("Unsupport state")
    def send_field_info(self): 
        try:
            self.tcp_handler.send_field_info()
        except ConnectionResetError as e:
            print(f"\x1b[31m\x1b[1mOnlooker {self.pid}({self.state}) error: {e}\x1b[0m")
            self.error = True
    def send_round_info(self): 
        if self.error:
            return
        try:
            with gvar.game_lock:
                self.tcp_handler.send_round_info()
        except ConnectionResetError as e:
            print(f"\x1b[31m\x1b[1mOnlooker {self.pid}({self.state}) error: {e}\x1b[0m")
            self.error = True
    def recv_player_info(self): 
        raise RuntimeError("Unsupport state")
    def init_sync(self): 
        raise RuntimeError("Unsupport state")
    def onlooker_sync(self): 
        gvar.onlooker_event.wait()
        # 这里放松了条件，因为在下一个同步点之前数据是只读的
        with gvar.game_lock:
            self.__game_over = gvar.game_over
    def game_start_sync(self): 
        raise RuntimeError("Unsupport state")
    def send_round_info_sync(self): 
        if self.error:
            assert gvar.onlooker_lock.locked()
            with gvar.onlooker_local_lock:
                gvar.onlooker_number -= 1
        gvar.onlooker_barrier.wait()
    def recv_player_info_sync(self): 
        raise RuntimeError("Unsupport state")
    def next_turn_sync(self): 
        raise RuntimeError("Unsupport state")
    
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
            raise RuntimeError("Unsupport state")
        logger.info(f"Onlooker {self.pid}({self.state}, error={self.error})")
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
        with gvar.game_lock:
            self.__game_over = gvar.game_over
