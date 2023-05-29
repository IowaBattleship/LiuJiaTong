import json
import random
import struct
import threading
import time
from socketserver import BaseRequestHandler, ThreadingTCPServer
import utils

RECV_LEN = 1024
HEADER_LEN = 4

class Game_Var:
    def init_game_env(self):
        self.users_cards = [[] for _ in range(6)]
        self.users_score = [0 for _ in range(6)]
        self.user_finished = [False for _ in range(6)] # 玩家打完所有的牌
        self.played_cards = [[] for _ in range(6)]  # 场上所出手牌
        self.now_score = 0  # 场上分数
        self.now_user = 0  # 当前出牌玩家
        self.head_master = -1  # 头科玩家下标
        self.last_played = 0  # 上一位出牌玩家
        self.team_score = [0, 0]  # 各队分数
        self.team_out = [0, 0]  # 各队逃出人数
        self.game_over = 0 # 游戏结束状态
    def __init__(self) -> None:
        self.users_name = []
        self.users_name_lock = threading.Lock()
        self.user_join_barrier = threading.Barrier(6)

        self.init_game_env()
        
        self.finish_sending_user_barrier = threading.Barrier(6)
        self.finish_sending_card_barrier = threading.Barrier(6)
        self.before_playing_barrier = threading.Barrier(6)
        self.after_playing_barrier = threading.Barrier(6)

gvar = Game_Var()
    
'''
判断游戏是否结束
返回值
0 表示没有结束 
1, -1 分别表示偶数队获胜,双统
2, -2 分别表示奇数队获胜,双统
'''
def if_game_over():
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

# 初始化牌
def init_cards():
    all_cards = []
    # 3~10,J,Q,K,A,2
    for i in range(3, 16):
        for _ in range(16):
            all_cards.append(i)
    # Jockers
    for i in range(16, 18):
        for _ in range(4):
            all_cards.append(i)
    random.shuffle(all_cards)

    for i in range(0, 6):
        user_cards = sorted([all_cards[j] for j in range(i, len(all_cards), 6)])
        gvar.users_cards[i] = [utils.int_to_str(x) for x in user_cards]

def start_game():
    random.shuffle(gvar.users_name)  # 随机出牌顺序
    gvar.init_game_env()
    init_cards()  # 初始化牌并发牌

# 下一位玩家出牌
def set_next_player():
    gvar.now_user = (gvar.now_user + 1) % 6
    while gvar.user_finished[gvar.now_user]:
        gvar.now_user = (gvar.now_user + 1) % 6

def before_playing():
    # 玩家是否打完所有的牌
    # 不在打完之后马上结算是因为玩家的分没拿
    # 考虑到有多个人同时打完牌的情况，得用循环
    while len(gvar.users_cards[gvar.now_user]) == 0 \
            and gvar.last_played != gvar.now_user:
        gvar.user_finished[gvar.now_user] = True
        gvar.played_cards[gvar.now_user].clear()
        set_next_player()
    
    # 一轮结束，统计此轮信息
    if gvar.last_played == gvar.now_user:
        # 统计用户分数
        gvar.users_score[gvar.now_user] += gvar.now_score
        # 队伍有头科，此轮分数直接累加到队伍分数中
        if gvar.head_master != -1 and gvar.now_user % 2 == gvar.head_master % 2:
            gvar.team_score[gvar.now_user % 2] += gvar.now_score
        # 若是刚好此轮逃出，此轮分数也直接累加到队伍分数中
        elif len(gvar.users_cards[gvar.now_user]) == 0:
            gvar.team_score[gvar.now_user % 2] += gvar.now_score
        # 判断游戏是否结束
        gvar.game_over = if_game_over()
        # 初始化场上分数
        gvar.now_score = 0
        # 如果刚好在此轮逃出，第一个出牌的人就要改变
        if len(gvar.users_cards[gvar.now_user]) == 0:
            gvar.user_finished[gvar.now_user] = True
            gvar.played_cards[gvar.now_user].clear()
            set_next_player()
            gvar.last_played = gvar.now_user

    # 清除当前玩家的场上牌
    gvar.played_cards[gvar.now_user].clear()

def after_playing():
    # skip
    if gvar.played_cards[gvar.now_user][0] == 'F':
        gvar.played_cards[gvar.now_user].clear()
    else:
        gvar.last_played = gvar.now_user
    
    # 此轮逃出，更新队伍信息、头科，判断游戏是否结束
    if len(gvar.users_cards[gvar.now_user]) == 0:
        gvar.team_out[gvar.now_user % 2] += 1
        if gvar.head_master == -1:
            gvar.head_master = gvar.now_user
            for i in range(6):
                if i % 2 == gvar.head_master % 2:
                    gvar.team_score[i % 2] += gvar.users_score[i]
        # 若队伍有头科，就不需要累加，没有则累加
        elif gvar.head_master % 2 != gvar.now_user % 2:
            gvar.team_score[gvar.now_user % 2] += gvar.users_score[gvar.now_user]

        gvar.game_over = if_game_over()
    
    # 最后更新一下打牌的user
    set_next_player()

class Game_Handler(BaseRequestHandler):
    
    def send_data(self, data):
        data = json.dumps(data).encode()
        header = struct.pack('i', len(data))
        self.request.sendall(header)
        self.request.sendall(data)
    
    def recv_data(self):
        header = self.request.recv(HEADER_LEN)
        header = struct.unpack('i', header)[0]
        data = self.request.recv(header)
        data = json.loads(data.decode())
        return data

    # 将username, tag发送给客户端
    def send_users_info(self, tag):
        while True:
            try:
                # 用户名
                users_name = [user_name for user_name, _ in gvar.users_name]
                self.send_data(users_name)
                # 用户标识号
                self.send_data(tag)
                break
            except Exception as e:
                print(e)
                time.sleep(1)
    
    def send_cards_info(self, tag):
        while True:
            try:
                # 游戏结束
                self.send_data(gvar.game_over)
                # 用户得分
                self.send_data(gvar.users_score)
                # 用户手牌数
                self.send_data([len(x) for x in gvar.users_cards])
                # 场上手牌
                self.send_data(gvar.played_cards)
                # 当前用户手牌
                self.send_data(gvar.users_cards[tag])
                # 场上得分
                self.send_data(gvar.now_score)
                # 当前玩家
                self.send_data(gvar.now_user)
                # 头科
                self.send_data(gvar.head_master)
                break
            except Exception as e:
                print(e)
                time.sleep(1)
    
    def recv_player_reply(self):
        user_cards = self.recv_data()
        played_cards = self.recv_data()
        now_score = self.recv_data()
        return user_cards, played_cards, now_score
        
    def handle(self):
        address, pid = self.client_address
        print(f'{address} connected, pid = {pid}')
        
        # recv username
        with gvar.users_name_lock:
            user_idx = len(gvar.users_name)
            user_name = self.recv_data()
            gvar.users_name.append((user_name, pid))
            print(gvar.users_name)
        
        if user_idx < 6:
            if user_idx == 0:  # 该线程作为发牌手
                start_game()
            gvar.user_join_barrier.wait()  # 等待其它玩家
            if user_idx == 0:
                gvar.user_join_barrier.reset()
        else:
            assert(0)

        # 找到该线程对应的玩家下标
        tag = next((i for i, (_, user_pid) in enumerate(gvar.users_name) if pid == user_pid), 0)

        if tag == 0:
            print(gvar.users_cards)

        self.send_users_info(tag)
        gvar.finish_sending_user_barrier.wait()
        if user_idx == 0:
            gvar.finish_sending_user_barrier.reset()

        while True:
            # 打牌前的处理
            if user_idx == 0:
                before_playing()
                gvar.before_playing_barrier.wait()
                gvar.before_playing_barrier.reset()
            else:
                gvar.before_playing_barrier.wait()
                
            # 将手牌等信息发送至各客户端
            now_user = gvar.now_user
            self.send_cards_info(tag)
            gvar.finish_sending_card_barrier.wait()
            if user_idx == 0:
                gvar.finish_sending_card_barrier.reset()
            
            # 非此轮的线程阻塞等待
            # 这里另起局部变量判断而不是用全局变量是因为now_user可能在tag用户的操作下发生变化
            # 虽然感觉在gil下不会有问题……纯小题大做233……并发真不是正常人能玩的
            if tag != now_user:
                gvar.after_playing_barrier.wait()
            else:
                # 接受出牌信息
                print(f'Now Round:{gvar.users_name[tag]}')
                assert(gvar.played_cards[tag] == [])
                gvar.users_cards[tag], gvar.played_cards[tag], gvar.now_score \
                    = self.recv_player_reply()
                print(f'Played Cards:{gvar.played_cards[tag]}')

                # 打牌后的处理
                after_playing()
                gvar.after_playing_barrier.wait()
                gvar.after_playing_barrier.reset()



if __name__ == '__main__':
    server = ThreadingTCPServer(('0.0.0.0', 8080), Game_Handler)
    print("Listening")
    server.serve_forever()
