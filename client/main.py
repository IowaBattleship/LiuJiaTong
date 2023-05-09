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

user = UserInfo()


class Client:
    def __init__(self):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

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
        user.input_name()
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
    _ip = input('请输入服务器IP，输入\'127\'则设置为默认本机IP与端口：')
    if _ip == '127':
        _ip = '127.0.0.1'
        _port = 8080
    else:
        _port = int(input('请输入服务器端口：'))
    client = Client()
    client.connect(_ip, _port)
    client.run()
    client.close()
