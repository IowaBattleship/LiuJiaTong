import time
import utils
import logger
from game_vars import gvar
from state_machine import GameState, GameStateMachine

class Player(GameStateMachine):
    # 私有方法
    def __handle_error(self, e):
        utils.error(f"Player {self.pid}({self.client_player}, {self.state}) error: {e}")
        self.error = True
    def __update_local_cache(self):
        with gvar.game_lock:
            self.__game_over = gvar.game_over
            self.__now_player = gvar.now_player
    # 抽象类方法
    def game_start(self): 
        raise RuntimeError("Unsupport state")
    def game_over(self): 
        if self.error:
            with gvar.users_info_lock:
                gvar.users_error[self.client_player] = True
            utils.warn(f"Player {self.pid}({self.client_player}) error exit -> cookie: {self.tcp_handler.user_cookie}")
        else:
            utils.success(f"Player {self.pid}({self.client_player}) exit successfully")
        self.tcp_handler.close()
    def onlooker_register(self): 
        raise RuntimeError("Unsupport state")
    def next_turn(self): 
        raise RuntimeError("Unsupport state")
    def send_waiting_hall_info(self):
        assert self.error is False
        try:
            users_num = 0
            send_counter = 10
            while True:                
                with gvar.users_info_lock:
                    new_users_num = self.tcp_handler.update_users_info()
                send_counter -= 1
                if new_users_num > users_num or send_counter == 0:
                    self.tcp_handler.send_waiting_hall_info()
                    users_num = new_users_num
                    send_counter = 10
                if users_num == 6:
                    break
                time.sleep(0.1)
        except Exception as e:
            self.__handle_error(e)
    def send_field_info(self): 
        assert self.error is False
        try:
            self.tcp_handler.send_field_info()
        except Exception as e:
            self.__handle_error(e)
    def send_round_info(self): 
        assert self.error is False
        try:
            with gvar.game_lock:
                self.tcp_handler.send_round_info()
        except Exception as e:
            self.__handle_error(e)
    def recv_player_info(self): 
        """
        接收玩家信息，并更新游戏状态

        该函数负责接收客户端发送的玩家信息，包括玩家手牌、已出牌和当前得分。
        同时，它还会更新游戏状态，包括玩家手牌、已出牌和当前得分。
        """
        assert self.error is False
        try:
            with gvar.users_info_lock:
                print(f"Now round:{self.client_player} -> {gvar.users_info[self.client_player]}")

            # 等待客户端的heartbeat返回值为真，意味着出了有效牌
            while not self.tcp_handler.recv_playing_heartbeat():
                pass

            # 接收客户端发送的玩家信息
            user_cards, user_played_cards, now_score = self.tcp_handler.recv_player_reply()
            logger.info(f"Player {self.pid}({self.client_player}) cards:{user_cards}")
            logger.info(f"Player {self.pid}({self.client_player}) played cards:{user_played_cards}")
            logger.info(f"Player {self.pid}({self.client_player}) score:{now_score}")
            
            # 更新游戏状态
            with gvar.game_lock:
                assert gvar.users_played_cards[self.client_player] == [], \
                    gvar.users_played_cards[self.client_player]
                gvar.users_cards[self.client_player]        = user_cards        # 更新玩家手牌
                gvar.users_played_cards[self.client_player] = user_played_cards # 更新玩家已出牌
                gvar.now_score                              = now_score         # 更新当前得分
                print(f'Player {self.pid}({self.client_player}) played cards:{gvar.users_played_cards[self.client_player]}')
        except Exception as e:
            self.__handle_error(e)
    def init_sync(self): 
        gvar.game_init_barrier.wait()
    def onlooker_sync(self): 
        raise RuntimeError("Unsupport state")
    def game_start_sync(self): 
        gvar.game_start_barrier.wait()
        # 这里放松了条件，因为在下一个同步点之前数据是只读的
        self.__update_local_cache()
    def send_round_info_sync(self): 
        gvar.send_round_info_barrier.wait()
    def recv_player_info_sync(self): 
        gvar.recv_player_info_barrier.wait()
    def next_turn_sync(self): 
        gvar.next_turn_barrier.wait()
        # 这里放松了条件，因为在下一个同步点之前数据是只读的
        self.__update_local_cache()
    
    # 这个代码太tm抽象了，看我画的drawio的图，为了支持断线重连真不容易……
    def get_next_state(self) -> bool:
        recovery = False
        def need_recovery():
            if self.state == GameState.init:
                self.state = GameState.send_waiting_hall_info
            elif self.state == GameState.send_waiting_hall_info:
                self.state = GameState.send_field_info
            elif self.state == GameState.send_field_info:
                self.state = GameState.send_round_info
            elif self.state == GameState.send_round_info:
                self.state = GameState.recv_player_info
            else:
                raise RuntimeError(f"unknown state: {self.state}")
            if self.state == self.his_state:
                self.his_state = None
            nonlocal recovery; recovery = True
        # 状态转移
        if self.state == GameState.init:
            if self.his_state is None:
                self.state = GameState.send_waiting_hall_info
            else:
                need_recovery()
        elif self.state == GameState.send_waiting_hall_info:
            if self.error:
                self.state = GameState.game_over
            elif self.his_state is None:
                self.state = GameState.init_sync
            else:
                need_recovery()
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
                need_recovery()
        elif self.state == GameState.send_round_info:
            if self.error:
                self.state = GameState.game_over
            elif self.his_state is None:
                self.state = GameState.send_round_info_sync
            else:
                need_recovery()
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
            else:
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
            raise RuntimeError("Unsupport state")
        if recovery is False and self.error is False:
            with gvar.users_info_lock:
                gvar.users_his_state[self.client_player] = self.state
        logger.info(f"Player {self.client_player}({self.state}, error={self.error})")
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
        assert self.his_state in [
            None,
            GameState.send_waiting_hall_info,
            GameState.send_field_info, 
            GameState.send_round_info,
            GameState.recv_player_info,
        ], self.his_state
        self.tcp_handler = tcp_handler
        _, self.pid = tcp_handler.client_address
        
        self.error = False
        self.__update_local_cache()