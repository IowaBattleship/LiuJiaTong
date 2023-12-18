import json
import struct
import secrets
import string
import time
import logger
from player import Player
from onlooker import Onlooker
from game_vars import gvar
from socketserver import BaseRequestHandler

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

    def send_data(self, data):
        data = json.dumps(data).encode()
        header = struct.pack('i', len(data))
        self.request.sendall(header)
        self.request.sendall(data)
    
    def recv_data(self):
        HEADER_LEN = 4
        header = self.request.recv(HEADER_LEN)
        header = struct.unpack('i', header)[0]
        data = self.request.recv(header)
        data = json.loads(data.decode())
        return data

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
        self.send_data(self.is_player)
        assert len(self.users_name) == 6, self.users_name
        self.send_data(self.users_name)
        self.send_data(self.client_player)
    
    def send_round_info(self):
        assert gvar.game_lock.locked()
        self.send_data(gvar.game_over)
        self.send_data(gvar.users_score)
        # 用户手牌数
        self.send_data([len(x) for x in gvar.users_cards])
        self.send_data(gvar.users_played_cards)
        if gvar.game_over != 0:
            self.send_data(gvar.users_cards)
        # 当前用户手牌
        self.send_data(gvar.users_cards[self.client_player])
        self.send_data(gvar.now_score)
        self.send_data(gvar.now_player)
        self.send_data(gvar.head_master)

    def recv_player_reply(self):
        user_cards = self.recv_data()
        user_played_cards = self.recv_data()
        now_score = self.recv_data()
        return user_cards, user_played_cards, now_score

    def recv_playing_heartbeat(self):
        finished = self.recv_data()
        assert isinstance(finished, bool), finished
        return finished
    
    def send_waiting_hall_info(self):
        self.send_data(self.users_name)
        self.send_data(self.users_error)
    
    def generate_cookie(self, length=8):
        # 可以使用的字符集合
        characters = string.ascii_letters + string.digits
        # 使用 secrets 模块生成安全的随机字符串
        cookie = ''.join(secrets.choice(characters) for _ in range(length))
        return cookie

    def recv_user_info(self):
        assert gvar.users_info_lock.locked()
        try:
            if_has_cookie = self.recv_data()
            if if_has_cookie:
                self.user_cookie = self.recv_data()
                self.client_player = gvar.users_cookie.get(self.user_cookie)
            else:
                self.client_player = None
            # cookie是否合法
            if self.client_player is None:
                self.send_data(False)
                # 不合法当做正常的玩家加入
                user_idx = gvar.users_num
                user_name = self.recv_data()
                if user_idx == 6:
                    self.is_player = False
                    self.client_player = secrets.randbelow(6)
                    self.send_data(None)
                    print(f"\x1b[32m\x1b[1mOnlooker {user_name}({self.pid}) joined game -> player: {self.client_player}\x1b[0m")
                else:
                    self.is_player = True
                    self.client_player = gvar.users_player_id[user_idx]
                    # 生成cookie
                    self.user_cookie = self.generate_cookie()
                    while gvar.users_cookie.get(self.user_cookie) is not None:
                        self.user_cookie = self.generate_cookie()
                    self.send_data(self.user_cookie)
                    print(f"\x1b[32m\x1b[1mPlayer {user_name}({self.client_player}, {self.pid}) joined game -> cookie: {self.user_cookie}\x1b[0m")
                    logger.info(f"{user_name}({self.client_player}, {self.pid}) -> user_cookie: {self.user_cookie}")
                # 修改是放在最后的，防止中间出现任何的网络通信失败
                if self.is_player:
                    gvar.users_num += 1
                    gvar.users_info[self.client_player] = (user_name, self.pid)
                    assert 0 <= self.client_player and self.client_player < 6, self.client_player
                    gvar.users_cookie[self.user_cookie] = self.client_player
            else:
                # 发送合法标识，并尝试恢复
                self.send_data(True)
                self.is_player = True
                assert 0 <= self.client_player and self.client_player < 6, self.client_player
                if gvar.users_error[self.client_player]:
                    self.send_data(True)
                    # 修改是放在最后的，防止中间出现任何的网络通信失败
                    self.his_state = gvar.users_his_state[self.client_player]
                    gvar.users_error[self.client_player] = False
                    user_name, old_pid = gvar.users_info[self.client_player]
                    gvar.users_info[self.client_player] = (user_name, self.pid)
                    print(f"\x1b[32m\x1b[1m{self.pid} recover: {(user_name, old_pid)} -> {(user_name, self.pid)}\x1b[0m")
                else:
                    self.send_data(False)
                    raise RuntimeError("recover failed because user is playing")
        except Exception as e:
            print(f"\x1b[31m\x1b[1m{self.pid} error recieving user info: {e}\x1b[0m")
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


        