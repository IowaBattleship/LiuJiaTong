import secrets
import string
import logger
import utils
from player import Player
from onlooker import Onlooker
from game_vars import gvar
from socketserver import BaseRequestHandler
from my_network import recv_data_from_socket, send_data_to_socket
from card import Card

class Game_Handler(BaseRequestHandler):
    def __init__(self, request, client_address, server):
        self.is_player = False
        self.serving_game_round = 0
        self.client_player = None
        self.user_cookie = None
        self.his_state = None
        self.pid = 0
        self.users_name = []
        self.users_error = []
        
        super().__init__(request, client_address, server)

    # 11/03/2024: 把send_data和recv_data方法提取到Network文件中去了

    def close(self):
        self.request.close()

    def update_users_info(self):
        assert gvar.users_info_lock.locked()
        self.users_name = []
        self.users_error = []
        for i in range(6):
            if gvar.users_info[i] is None:
                continue
            user_name, _ = gvar.users_info[i]
            self.users_name.append(user_name)
            self.users_error.append(gvar.users_error[i])
        return len(self.users_name)

    def send_field_info(self):
        # 玩家/旁观者
        send_data_to_socket(self.is_player, self.request)
        assert len(self.users_name) == 6, self.users_name
        send_data_to_socket(self.users_name, self.request)
        send_data_to_socket(self.client_player, self.request)
    
    def send_round_info(self):
        assert gvar.game_lock.locked()
        send_data_to_socket(gvar.game_over, self.request)
        send_data_to_socket(gvar.users_score, self.request)

        # 用户手牌数
        send_data_to_socket([len(cards) for cards in gvar.users_cards], self.request) # 更新用户手牌数
        send_data_to_socket(gvar.users_played_cards, self.request) # 更新场上出的牌
        if gvar.game_over != 0:
            send_data_to_socket(gvar.users_cards, self.request)

        # 当前用户手牌
        send_data_to_socket(gvar.users_cards[self.client_player], self.request)
        send_data_to_socket(gvar.now_score, self.request)
        send_data_to_socket(gvar.now_player, self.request)
        send_data_to_socket(gvar.head_master, self.request)

    def recv_player_reply(self) -> tuple[list[Card], list[Card], int]:
        user_cards = recv_data_from_socket(self.request)
        user_played_cards = recv_data_from_socket(self.request)
        now_score = recv_data_from_socket(self.request)
        return user_cards, user_played_cards, now_score

    def recv_playing_heartbeat(self):
        print("Trying to receive heartbeat...")
        finished = recv_data_from_socket(self.request)
        print(f"Received heartbeat: {finished}")
        assert isinstance(finished, bool), finished
        return finished
    
    def send_waiting_hall_info(self):
        send_data_to_socket(self.users_name, self.request)
        send_data_to_socket(self.users_error, self.request)
    
    def generate_cookie(self, length=8):
        # 可以使用的字符集合
        characters = string.ascii_letters + string.digits
        # 使用 secrets 模块生成安全的随机字符串
        cookie = ''.join(secrets.choice(characters) for _ in range(length))
        return cookie

    def recv_user_info(self):
        assert gvar.users_info_lock.locked()
        logger.info(f"{self.pid} waiting for user info")
        try:
            if_has_cookie = recv_data_from_socket(self.request)
            logger.info(f"if_has_cookie: {if_has_cookie}")
            if if_has_cookie:
                self.user_cookie = recv_data_from_socket(self.request)
                self.client_player = gvar.users_cookie.get(self.user_cookie)
            else:
                self.client_player = None
            # cookie是否合法
            if self.client_player is None:
                send_data_to_socket(False, self.request)
                # 不合法当做正常的玩家加入
                user_idx = gvar.users_num
                user_name = recv_data_from_socket(self.request)
                if user_idx == 6:
                    self.is_player = False
                    self.client_player = secrets.randbelow(6)
                    send_data_to_socket(None, self.request)
                    utils.success(f"Onlooker {user_name}({self.pid}) joined game -> player: {self.client_player}")
                else:
                    self.is_player = True
                    self.client_player = gvar.users_player_id[user_idx]
                    # 生成cookie
                    self.user_cookie = self.generate_cookie()
                    while gvar.users_cookie.get(self.user_cookie) is not None:
                        self.user_cookie = self.generate_cookie()
                    send_data_to_socket(self.user_cookie, self.request)
                    utils.success(f"Player {user_name}({self.client_player}, {self.pid}) joined game -> cookie: {self.user_cookie}")
                    logger.info(f"{user_name}({self.client_player}, {self.pid}) -> user_cookie: {self.user_cookie}")
                # 修改是放在最后的，防止中间出现任何的网络通信失败
                if self.is_player:
                    gvar.users_num += 1
                    gvar.users_info[self.client_player] = (user_name, self.pid)
                    assert 0 <= self.client_player and self.client_player < 6, self.client_player
                    gvar.users_cookie[self.user_cookie] = self.client_player
            else:
                # 发送合法标识，并尝试恢复
                send_data_to_socket(True, self.request)
                self.is_player = True
                assert 0 <= self.client_player and self.client_player < 6, self.client_player
                if gvar.users_error[self.client_player]:
                    send_data_to_socket(True, self.request)
                    # 修改是放在最后的，防止中间出现任何的网络通信失败
                    self.his_state = gvar.users_his_state[self.client_player]
                    gvar.users_error[self.client_player] = False
                    user_name, old_pid = gvar.users_info[self.client_player]
                    gvar.users_info[self.client_player] = (user_name, self.pid)
                    utils.success(f"{self.pid} recover: {(user_name, old_pid)} -> {(user_name, self.pid)}")
                else:
                    send_data_to_socket(False, self.request)
                    raise RuntimeError("Recover failed because user is playing")
        except Exception as e:
            utils.error(f"{self.pid} error receiving user info: {e}") # 11/03/2024: Fix typo
            return False
        else:
            return True

    def handle(self):        
        with gvar.users_info_lock:
            address, self.pid = self.client_address
            print(f'{address}({self.pid}) connected')
            self.serving_game_round = gvar.serving_game_round
            if self.recv_user_info() is False:
                return
        if self.is_player:
            Player(
                self.client_player,
                self.his_state,
                self,
            ).run()
        else:
            Onlooker(
                self.client_player,
                self.serving_game_round,
                self,
            ).run()


        