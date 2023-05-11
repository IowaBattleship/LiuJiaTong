import json
import random
import struct
import threading
import time
from socketserver import BaseRequestHandler, ThreadingTCPServer
import utils

RECV_LEN = 1024
HEADER_LEN = 4

users_name = []
users_cards = []
users_score = []
if_users_run = [0 for _ in range(0, 6)]
played_cards = []  # 场上所出手牌
all_cards = []
now_score = 0  # 场上分数
now_user = 0  # 当前出牌玩家
head_master = -1  # 头科玩家下标
last_played = 0  # 上一位出牌玩家
team_score = [0, 0]  # 各队分数
team_out = [0, 0]  # 各队逃出人数

lock = threading.Lock()  # 变量锁
if_enough_user = threading.Event()
if_now_round = threading.Event()
_if_now_round = 0


# 初始化牌
def init_cards():
    for i in range(3, 16):
        for j in range(1, 17):
            all_cards.append(i)
    for i in range(16, 18):
        for j in range(1, 5):
            all_cards.append(i)
    random.shuffle(all_cards)
    # print(all_cards)


# 初始化每个玩家的手牌
def init_users_cards():
    users_cards.clear()
    for i in range(0, 6):
        users_cards.append(sorted([all_cards[j] for j in range(i, len(all_cards), 6)]))
        played_cards.append([])
        users_score.append(0)
    for i in range(0, 6):
        users_cards[i] = [utils.int_to_str(x) for x in users_cards[i]]
    # print(users_cards)


# 下一位玩家出牌
def next_user(_now_user):
    _now_user = (_now_user + 1) % 6
    # while len(users_cards[_now_user]) == 0:
    while if_users_run[_now_user] == 1:
        _now_user = (_now_user + 1) % 6
    return _now_user


'''
判断游戏是否结束
返回值
0 表示没有结束 
1, -1 分别表示偶数队获胜,双统
2, -2 分别表示奇数队获胜,双统
'''


def if_game_over():
    # 没有头科肯定没有结束
    if head_master == -1:
        return 0
    # 根据各队分数以及逃出人数判断
    for i in range(2):
        if team_score[i] >= 200 and team_out[i] == 3 and team_out[1 - i] == 0:
            return -(i + 1)
        elif (team_score[i] >= 200 and team_out[1 - i] != 0) or team_out[i] == 3:
            return i + 1
    return 0


class Handler(BaseRequestHandler):
    def handle(self):
        address, pid = self.client_address
        print(f'{address} connected, pid = {pid}')

        # recv username
        with lock:
            users_name.append((self.request.recv(RECV_LEN).decode(), pid))
            users_num = len(users_name)
            print(users_name)

        global if_enough_user, if_now_round, now_user, now_score, head_master, last_played, _if_now_round, if_users_run
        _local_if_now_round = _if_now_round

        if users_num == 6:  # 该线程作为发牌手
            random.shuffle(users_name)  # 随机出牌顺序
            now_user = 0  # 首位作为第一位出牌
            now_score = 0
            head_master = -1
            init_cards()  # 初始化牌并发牌
            init_users_cards()
            if_enough_user.set()
        else:
            if_enough_user.wait()  # 等待其它玩家

        # 找到该线程对应的玩家下标
        tag = 0
        for i in range(0, 6):
            x, y = users_name[i]
            if pid == y:
                tag = i
                break
        # 将username, tag发送给客户端
        try:
            data = json.dumps([x for x, y in users_name]).encode()  # username
            header = struct.pack('i', len(data))
            self.request.sendall(header)
            self.request.sendall(data)

            data = str(tag).encode()
            header = struct.pack('i', len(data))
            self.request.sendall(header)
            self.request.sendall(data)
        except Exception as e:
            print(e)
            return

        _if_game_over = 0
        while True:

            # 非此轮的线程阻塞等待
            if tag != now_user:
                # if_now_round.clear()
                # if_now_round.wait()
                while True:
                    if _if_now_round > _local_if_now_round:
                        break
            else:
                # 标记该玩家是否run
                with lock:
                    if len(users_cards[tag]) == 0:
                        if_users_run[tag] = 1

                # 一轮结束，统计此轮信息
                if last_played == tag:
                    # 队伍有头科，此轮分数直接累加到队伍分数中
                    if head_master != -1 and tag % 2 == head_master % 2:
                        team_score[tag % 2] += now_score
                    # 若是刚好此轮逃出，此轮分数也直接累加到队伍分数中
                    # 同时直接跳到下家出牌
                    elif len(users_cards[tag]) == 0:
                        team_score[tag % 2] += now_score
                        last_played = now_user = next_user(now_user)

                    # 判断游戏是否结束
                    _if_game_over = if_game_over()

                    # 清除打出牌的信息
                    for x in played_cards:
                        x.clear()

                    users_score[tag] += now_score
                    now_score = 0
                else:
                    played_cards[tag].clear()
                # if_now_round.set()
                _if_now_round += 1

            _local_if_now_round += 1

            # 将手牌等信息发送至各客户端
            try:
                data = str(_if_game_over).encode()
                header = struct.pack('i', len(data))
                self.request.sendall(header)
                self.request.sendall(data)

                data = json.dumps(users_score).encode()
                header = struct.pack('i', len(data))
                self.request.sendall(header)
                self.request.sendall(data)

                data = json.dumps([len(x) for x in users_cards]).encode()  # user cards len
                header = struct.pack('i', len(data))
                self.request.sendall(header)
                self.request.sendall(data)

                data = json.dumps(played_cards).encode()
                header = struct.pack('i', len(data))
                self.request.sendall(header)
                self.request.sendall(data)

                data = json.dumps(users_cards[tag]).encode()
                header = struct.pack('i', len(data))
                self.request.sendall(header)
                self.request.sendall(data)

                data = str(now_score).encode()
                header = struct.pack('i', len(data))
                self.request.sendall(header)
                self.request.sendall(data)

                data = str(now_user).encode()
                header = struct.pack('i', len(data))
                self.request.sendall(header)
                self.request.sendall(data)

                data = str(head_master).encode()
                header = struct.pack('i', len(data))
                self.request.sendall(header)
                self.request.sendall(data)
            except Exception as e:
                print(e)
                return

            # 非此轮的线程阻塞等待
            if tag != now_user:
                if_now_round.clear()
                if_now_round.wait()
            else:
                print(f'Now Round:{users_name[now_user]}')
                # 接受出牌信息
                with lock:

                    if if_users_run[tag] == 0:
                        header = self.request.recv(HEADER_LEN)
                        header = struct.unpack('i', header)[0]
                        users_cards[tag] = json.loads(self.request.recv(header).decode())

                        header = self.request.recv(HEADER_LEN)
                        header = struct.unpack('i', header)[0]
                        played_cards[tag] = json.loads(self.request.recv(header).decode())

                        header = self.request.recv(HEADER_LEN)
                        header = struct.unpack('i', header)[0]
                        now_score = json.loads(self.request.recv(header).decode())

                        print(f'Played Cards:{played_cards[tag]}')

                        # skip
                        if played_cards[tag][0] == 'F':
                            played_cards[tag].clear()
                        else:
                            last_played = tag

                            # 此轮逃出，更新队伍信息、头科，判断游戏是否结束
                            if len(users_cards[tag]) == 0:
                                team_out[tag % 2] += 1

                                if head_master == -1:
                                    head_master = tag
                                    for i in range(6):
                                        if i % 2 == head_master % 2:
                                            team_score[i % 2] += users_score[i]
                                # 若队伍有头科，就不需要累加，没有则累加
                                elif head_master % 2 != tag % 2:
                                    team_score[tag % 2] += users_score[tag]

                                _if_game_over = if_game_over()

                    now_user = next_user(now_user)  # 下一位出牌

                if_now_round.set()


if __name__ == '__main__':
    server = ThreadingTCPServer(('0.0.0.0', 8080), Handler)
    print("Listening")
    server.serve_forever()
    # init_cards()
    # init_users_cards()
