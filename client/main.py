import json
import socket
import struct
import time
import utils
from userinfo import UserInfo
from interface import main_interface, game_over_interface
from playing_handler import playing

RECV_LEN = 1024
HEADER_LEN = 4

CONFIG_NAME = 'LiuJiaTong.json'

user = UserInfo()

class Config:
    def __init__(self, ip, port, name):
        self.ip = ip
        self.port = port
        self.name = name

class Client:
    def __init__(self):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

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

    def run(self):
        user.name = client.config.name
        try:
            self.client.sendall(user.name.encode())
        except Exception as e:
            print(e)
            return

        # 接收username, tag
        header = self.client.recv(HEADER_LEN)
        header = struct.unpack('i', header)[0]
        users_name = json.loads(self.client.recv(header).decode())

        header = self.client.recv(HEADER_LEN)
        header = struct.unpack('i', header)[0]
        tag = int(self.client.recv(header).decode())

        while True:
            # 接收场上信息
            header = self.client.recv(HEADER_LEN)
            header = struct.unpack('i', header)[0]
            _if_game_over = int(self.client.recv(header).decode())

            header = self.client.recv(HEADER_LEN)
            header = struct.unpack('i', header)[0]
            users_score = json.loads(self.client.recv(header).decode())
            user.score = users_score[tag]

            header = self.client.recv(HEADER_LEN)
            header = struct.unpack('i', header)[0]
            users_cards_len = json.loads(self.client.recv(header).decode())

            header = self.client.recv(HEADER_LEN)
            header = struct.unpack('i', header)[0]
            played_cards = json.loads(self.client.recv(header).decode())
            user.played_card = played_cards[tag]

            header = self.client.recv(HEADER_LEN)
            header = struct.unpack('i', header)[0]
            user.cards = json.loads(self.client.recv(header).decode())

            header = self.client.recv(HEADER_LEN)
            header = struct.unpack('i', header)[0]
            now_score = int(self.client.recv(header).decode())

            header = self.client.recv(HEADER_LEN)
            header = struct.unpack('i', header)[0]
            now_user = int(self.client.recv(header).decode())

            header = self.client.recv(HEADER_LEN)
            header = struct.unpack('i', header)[0]
            head_master = int(self.client.recv(header).decode())

            biggest_player = utils.last_played(played_cards, now_user)

            main_interface(users_name, tag, users_score, users_cards_len, played_cards,
                           user, now_score, now_user, head_master, biggest_player)

            # 游戏结束
            if _if_game_over != 0:
                game_over_interface(tag, _if_game_over)
                return

            # 轮到出牌
            if tag == now_user:
                last_user = utils.last_played(played_cards, tag)
                now_score += playing(user, last_user, tag, played_cards)                

                # 向server发送打出牌或skip的信息
                data = json.dumps(user.cards).encode()
                header = struct.pack('i', len(data))
                self.client.sendall(header)
                self.client.sendall(data)

                data = json.dumps(user.played_card).encode()
                header = struct.pack('i', len(data))
                self.client.sendall(header)
                self.client.sendall(data)

                data = str(now_score).encode()
                header = struct.pack('i', len(data))
                self.client.sendall(header)
                self.client.sendall(data)

            # print(users_name)
            # print(users_score)
            # print(users_cards_len)
            # print(played_cards)
            # print(user.cards)
            # print(now_score)
            # print(now_user)

if __name__ == '__main__':
    client = Client()
    client.get_config()
    client.connect(client.config.ip, client.config.port)
    client.run()
    client.close()
