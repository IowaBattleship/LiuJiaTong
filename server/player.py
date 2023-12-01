import os
import logger
from game_vars import gvar
from state_machine import GameState, GameStateMachine

class Player(GameStateMachine):
    def game_start(self): 
        raise RuntimeError("unsupport state")
    def game_over(self): 
        if self.error:
            print(f"player {self.client_player} error exit")
            with gvar.users_info_lock:
                gvar.users_error[self.client_player] = True
        else:
            print(f"player {self.client_player} exit")
        self.close()
    def onlooker_register(self): 
        raise RuntimeError("unsupport state")
    def next_turn(self): 
        raise RuntimeError("unsupport state")
    def send_field_info(self): 
        try:
            self.tcp_handler.send_field_info()
        except Exception as e:
            print(os.getpid(), "error :", e)
            self.error = True
    def send_round_info(self): 
        assert self.error is False
        try:
            self.tcp_handler.send_round_info()
        except Exception as e:
            print(os.getpid(), "error :", e)
            self.error = True
    def recv_player_info(self): 
        assert self.error is False
        try:
            print(f'Now Round:{gvar.users_info[self.client_player]}')
            assert(gvar.users_played_cards[self.client_player] == [])
            user_cards, user_played_cards, now_score = \
                self.tcp_handler.recv_player_reply()
            gvar.users_cards[self.client_player] = user_cards
            gvar.users_played_cards[self.client_player] = user_played_cards
            gvar.now_score = now_score
            print(f'Played Cards:{gvar.users_played_cards[self.client_player]}')
        except Exception as e:
            print(os.getpid(), "error :", e)
            self.error = True
    def init_sync(self): 
        gvar.game_init_barrier.wait()
    def onlooker_sync(self): 
        raise RuntimeError("unsupport state")
    def game_start_sync(self): 
        gvar.game_start_barrier.wait()
        # 这里放松了条件，因为在下一个同步点之前数据是只读的
        assert self.tcp_handler.client_player == -1 and self.client_player == -1
        with gvar.users_info_lock:
            self.tcp_handler.client_player = self.client_player = \
                next((i for i, (_, user_pid) in enumerate(gvar.users_info) if self.pid == user_pid), 0)
            user_name, _ = gvar.users_info[self.client_player]
            gvar.users_cookie[self.tcp_handler.user_cookie] = self.client_player
        logger.info(f"{user_name}({self.pid}) -> client_player: {self.client_player}")
    def send_round_info_sync(self): 
        gvar.send_round_info_barrier.wait()
    def recv_player_info_sync(self): 
        gvar.recv_player_info_barrier.wait()
    def next_turn_sync(self): 
        gvar.next_turn_barrier.wait()
        # 这里放松了条件，因为在下一个同步点之前数据是只读的
        self.__game_over = gvar.game_over
        self.__now_player = gvar.now_player
    
    # 这个代码太tm抽象了，看我画的drawio的图，为了支持断线重连真不容易……
    def get_next_state(self) -> bool:
        recovery = False
        if self.state == GameState.init:
            if self.his_state is None:
                self.state = GameState.init_sync
            else:
                assert self.his_state in [
                    GameState.send_field_info, 
                    GameState.send_round_info,
                    GameState.recv_player_info,
                ], self.his_state
                self.state = GameState.send_field_info
                if self.state == self.his_state:
                    self.his_state = None
                recovery = True
        elif self.state == GameState.init_sync:
            assert self.his_state is None, self.his_state
            self.state = GameState.game_start_sync
        elif self.state == GameState.game_start_sync:
            assert self.his_state is None, self.his_state
            self.state = GameState.send_field_info
        elif self.state == GameState.send_field_info:
            if self.error:
                self.state = GameState.game_over
            elif self.his_state is None:
                self.state = GameState.send_round_info
            else:
                assert self.his_state in [
                    GameState.send_round_info,
                    GameState.recv_player_info,
                ], self.his_state
                self.state = GameState.send_round_info
                if self.state == self.his_state:
                    self.his_state = None
                recovery = True
        elif self.state == GameState.send_round_info:
            if self.error:
                self.state = GameState.game_over
            elif self.his_state is None:
                self.state = GameState.send_round_info_sync
            else:
                assert self.his_state in [
                    GameState.recv_player_info,
                ], self.his_state
                self.state = GameState.recv_player_info
                if self.state == self.his_state:
                    self.his_state = None
                recovery = True
        elif self.state == GameState.send_round_info_sync:
            assert self.his_state is None, self.his_state
            if self.__game_over != 0:
                self.state = GameState.game_over
            elif self.client_player == self.__now_player:
                self.state = GameState.recv_player_info
            else:
                self.state = GameState.recv_player_info_sync
        elif self.state == GameState.recv_player_info:
            assert self.his_state is None, self.his_state
            if self.error:
                self.state = GameState.game_over
            elif self.his_state is None:
                self.state = GameState.recv_player_info_sync
        elif self.state == GameState.recv_player_info_sync:
            assert self.his_state is None, self.his_state
            self.state = GameState.next_turn_sync
        elif self.state == GameState.next_turn_sync:
            assert self.his_state is None, self.his_state
            self.state = GameState.send_round_info
        elif self.state == GameState.game_over:
            assert self.his_state is None, self.his_state
            return False
        else:
            raise RuntimeError("unsupport state")
        if recovery is False and self.error is False:
            with gvar.users_info_lock:
                gvar.users_his_state[self.client_player] = self.state
        logger.info(f"player {self.client_player}: state={self.state}, error={self.error}")
        return True

    def __init__(
        self,
        client_player: int,
        his_state,
        tcp_handler,
    ):
        super().__init__()
        self.client_player = client_player
        self.his_state = his_state
        self.tcp_handler = tcp_handler
        _, self.pid = tcp_handler.client_address
        
        self.error = False
        self.__now_player = 0
        self.__game_over = 0
    
    def send_data(self, data):
        self.tcp_handler.send_data(data)
    
    def recv_data(self):
        return self.tcp_handler.recv_data()
    
    def close(self):
        self.tcp_handler.close()