import json
import random
import struct
import secrets
import string
import time
import random
import logger
from player import Player
from onlooker import Onlooker
from game_vars import gvar
from socketserver import BaseRequestHandler

class Game_Handler(BaseRequestHandler):
    def __init__(self, request, client_address, server):
        self.is_player = False
        self.is_recovery = False
        self.serving_game_round = 0
        self.client_player = -1
        self.user_cookie = None
        self.his_state = None
        self.pid = 0
        
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

    def send_field_info(self):
        # 玩家/旁观者
        self.send_data(self.is_player)
        users_name = [user_name for user_name, _ in gvar.users_info]
        self.send_data(users_name)
        self.send_data(self.client_player)
    
    def send_round_info(self):
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
                self.is_recovery = False
                # 不合法当做正常的玩家加入
                user_idx = len(gvar.users_info)
                user_name = self.recv_data()
                if user_idx == 6:
                    self.is_player = False
                    self.client_player = random.randint(0, 5)
                    self.send_data(None)
                    print(f"{user_name} joined game. It is a onlooker")
                else:
                    self.is_player = True
                    self.client_player = -1
                    # 生成cookie
                    self.user_cookie = self.generate_cookie()
                    self.send_data(self.user_cookie)
                    print(f"{user_name} joined game. It is a player. cookie: {self.user_cookie}")
                    logger.info(f"{user_name}({self.pid}) -> user_cookie: {self.user_cookie}")
                # 修改是放在最后的，防止中间出现任何的网络通信失败
                if self.is_player:
                    assert self.client_player == -1
                    gvar.users_info.append((user_name, self.pid))
                    gvar.users_cookie[self.user_cookie] = self.client_player
            else:
                # 合法就先发送标识，之后考虑恢复的情况
                self.send_data(True)
                self.is_recovery = True
                self.is_player = True
        except Exception as e:
            print("recv user info error:", e)
            return False
        else:
            return True
    
    def try_recovery(self):
        # 因为只有游戏开始之后才知道自己的player标识
        # 如果拿到cookie成功匹配之后发现值是-1就意味着游戏还没开始，只能硬等
        while self.client_player == -1:
            time.sleep(0.5)
            with gvar.users_info_lock:
                self.client_player = gvar.users_cookie[self.user_cookie]
        # 需要判断是否能够实现正确恢复,最多只有一个线程能够恢复
        print(f"valid cookie {self.user_cookie} -> {self.client_player}")
        try:
            with gvar.users_info_lock:
                if gvar.users_error[self.client_player]:
                    self.send_data(True)
                    self.his_state = gvar.users_his_state[self.client_player]
                    gvar.users_error[self.client_player] = False
                    return True
                else:
                    self.send_data(False)
                    return False
        except Exception as e:
            print("try recovery error:", e)
            return False

    def handle(self):        
        with gvar.users_info_lock:
            address, self.pid = self.client_address
            print(f'{address} connected, pid = {self.pid}')
            self.serving_game_round = gvar.serving_game_round
            if self.recv_user_info() is False:
                return
        # 尝试恢复            
        if self.is_recovery:
            if self.try_recovery() is False:
                return
        
        if self.is_player:
            player = Player(
                self.client_player,
                self.his_state,
                self,
            )
            player.run()
        else:
            onlooker = Onlooker(
                self.client_player,
                self.serving_game_round,
                self,
            )
            onlooker.run()


        