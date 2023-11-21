import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import socket
import struct
import time
import argparse
from userinfo import UserInfo
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
        self.user = UserInfo()

        self.is_player = False # 玩家/旁观者
        self.tag = 0 # 用户标识
        self.users_name = [] # 用户名字
        self.game_over = 0 # 游戏结束标志，非0代表已经结束
        self.now_score = 0 # 场上的分数
        self.now_user = 0 # 当前的用户
        self.cards_num = [] # 用户牌数
        self.users_score = [] # 用户分数
        self.played_cards = [] # 场上的牌
        self.head_master = 0 # 头科

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
        self.user.score = self.users_score[self.tag]
        
        self.cards_num = self.recv_data()
        
        self.played_cards = self.recv_data()
        self.user.played_card = self.played_cards[self.tag]

        self.user.cards = self.recv_data()

        self.now_score = self.recv_data()

        self.now_user = self.recv_data()

        self.head_master = self.recv_data()
    
    # 向server发送打出牌或skip的信息
    def send_card_info(self):
        self.send_data(self.user.cards)
        self.send_data(self.user.played_card)
        self.send_data(self.now_score)

    def run(self):
        self.user.name = client.config.name
        self.send_data(self.user.name)

        # 接收用户信息
        self.is_player = self.recv_data()
        self.users_name = self.recv_data()
        self.tag = self.recv_data()

        while True:
            self.recv_card_info()
            biggest_player = utils.last_played(self.played_cards, self.now_user)

            main_interface(self.users_name, self.tag, self.users_score, self.cards_num, self.played_cards,
                           self.user, self.now_score, self.now_user, self.head_master, biggest_player)

            # 游戏结束
            if self.game_over != 0:
                game_over_interface(self.tag, self.game_over)
                return

            # 轮到出牌
            if self.is_player and self.tag == self.now_user:
                last_user = utils.last_played(self.played_cards, self.tag)
                self.now_score += playing(self.user, last_user, self.tag, self.played_cards, self.client)                
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
