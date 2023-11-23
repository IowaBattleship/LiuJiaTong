import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import socket
import struct
import time
import argparse
from interface import main_interface, game_over_interface
from playing_handler import playing
import utils

RECV_LEN = 1024
HEADER_LEN = 4

CONFIG_NAME = 'LiuJiaTong.json'

class Config:
    def __init__(self, ip, port, name):
        self.ip = ip
        self.port = port
        self.name = name

class Client:
    def __init__(self):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.client_player = 0 # 客户端用户标识
        self.client_cards = []  # 持有牌
        self.is_player = False  # 玩家/旁观者
        self.users_name = [] # 用户名字
        self.game_over = 0 # 游戏结束标志，非0代表已经结束
        self.now_score = 0 # 场上的分数
        self.now_player = 0 # 当前的玩家
        self.users_cards_num = [] # 用户牌数
        self.users_score = [] # 用户分数
        self.users_played_cards = [] # 场上的牌
        self.head_master = 0 # 头科
        self.his_now_score = 0 # 历史场上分数，用于判断是否发生了得分
        self.his_last_player = None # 历史上一个打牌的人，用于判断是否上次发生打牌事件
        self.is_start = False # 记录是否游戏还在开局

    def get_config(self):
        try:
            with open(CONFIG_NAME, "r") as file:
                data = json.load(file)
                self.config = Config(data["ip"], int(data["port"]), data["name"])
        except:
            if hasattr(self, "config"):
                del self.config

        if hasattr(self, "config"):
            print("已经检测到之前输入的配置，配置如下:")
        
        while True:
            if hasattr(self, "config"):
                print(f"IP地址: {self.config.ip}")
                print(f"端口:   {self.config.port}")
                print(f"用户名: {self.config.name}")
                print(f"是否使用配置？[Y/n]: ", end='')
                while True:
                    resp = input().upper()
                    if resp in ['', 'Y']:
                        break
                    elif resp == 'N':
                        del self.config
                        break
                    else:
                        print(f"非法输入: ", end='')
            
            if hasattr(self, "config"):
                break
            
            while True:
                ip = input(f"请输入IP地址: ")
                port = input(f"请输入端口: ")
                name = input(f"请输入用户名: ")
                try:
                    self.config = Config(ip, int(port), name)
                except:
                    print(f"输入有误，请重新输入")
                else:
                    with open(CONFIG_NAME, "w") as file:
                        data = {
                            "ip": self.config.ip,
                            "port": self.config.port,
                            "name": self.config.name
                        }
                        json.dump(data, file)
                    print('')
                    break

    def connect(self, server_ip='127.0.0.1', server_port=8080):
        if_connected = False

        while if_connected is False:
            print("Try to connect with server...")
            if_connected = True
            try:
                self.client.connect((server_ip, server_port))
            except Exception as e:
                print(e)
                if_connected = False
                time.sleep(1)
        print("Successfully connected")

    def close(self):
        self.client.close()
    
    def send_data(self, data):
        data = json.dumps(data).encode()
        header = struct.pack('i', len(data))
        self.client.sendall(header)
        self.client.sendall(data)
    
    def recv_data(self):
        header = self.client.recv(HEADER_LEN)
        header = struct.unpack('i', header)[0]
        data = self.client.recv(header)
        data = json.loads(data.decode())
        return data
    
    # 接收场上信息
    def recv_card_info(self):
        self.game_over = self.recv_data()
        self.users_score = self.recv_data()
        self.users_cards_num = self.recv_data()
        self.users_played_cards = self.recv_data()
        self.client_cards = self.recv_data()
        self.now_score = self.recv_data()
        self.now_player = self.recv_data()
        self.head_master = self.recv_data()
    
    # 向server发送打出牌或skip的信息
    def send_card_info(self):
        self.send_data(self.client_cards)
        self.send_data(self.users_played_cards[self.client_player])
        self.send_data(self.now_score)

    def run(self):
        self.send_data(client.config.name)

        # 接收用户信息
        self.is_player = self.recv_data()
        self.users_name = self.recv_data()
        self.client_player = self.recv_data()

        while True:
            self.recv_card_info()
            # UI
            last_player = utils.last_played(self.users_played_cards, self.now_player)
            # 这里需要额外考虑一个情况就是当一个人打完所有牌，所有玩家无法跟时
            # 历史的最后打牌人可能会发生不一致性，因为永远轮不到逃走的人打牌
            # 当一轮结束后，会移交给下一个可以打的人打牌，历史最后打牌人记录应该同步
            # 要不然会触发出牌的效果音(如果历史中最后打牌的人与当前判断最后打牌的人一致视为过牌，否则视为打牌)
            if last_player == self.now_player and last_player != self.his_last_player:
                self.his_last_player = last_player
            main_interface(
                # 客户端变量
                self.is_start, self.is_player, self.client_cards, self.client_player,
                # 场面信息
                self.users_name, self.users_score, self.users_cards_num, 
                self.users_played_cards, self.head_master,
                # 运行时数据
                self.now_score, self.now_player, last_player,
                # 历史数据
                self.his_now_score, self.his_last_player 
            )
            # 记录历史信息
            self.his_now_score = self.now_score
            self.his_last_player = last_player if last_player != self.now_player else None
            self.is_start = True
            # 游戏结束
            if self.game_over != 0:
                game_over_interface(self.client_player, self.game_over)
                break
            # 轮到出牌
            if self.is_player and self.client_player == self.now_player:
                new_played_cards, new_score = playing(self.client_cards, last_player, 
                                self.client_player, self.users_played_cards, self.client)
                new_played_cards.sort(key = utils.str_to_int)
                self.users_played_cards[self.client_player] = new_played_cards
                self.now_score += new_score
                self.send_card_info()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='启动六家统客户端')
    parser.add_argument('--ip', type=str, help='ip address')
    parser.add_argument('--port', type=int, help='port')
    parser.add_argument('--user-name', type=str, help='user name')
    args = parser.parse_args()

    client = Client()
    if args.ip == None or args.port == None or args.user_name == None:
        client.get_config()
    else:
        client.config = Config(args.ip, args.port, args.user_name)

    client.connect(client.config.ip, client.config.port)
    client.run()
    client.close()
