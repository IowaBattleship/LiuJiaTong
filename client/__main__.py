import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import utils
utils.check_packages({
    "nt": [
        ("win32api", "pypiwin32"),
        ("win32con", "pypiwin32"),
    ],
})
import json
import socket
import struct
import time
import argparse
from interface import main_interface, game_over_interface, waiting_hall_interface
from playing_handler import playing
from terminal_printer import TerminalHandler
import logger

CONFIG_NAME = 'LiuJiaTong.json'

class Config:
    def __init__(self, ip, port, name, cookie=None):
        self.ip = ip
        self.port = port
        self.name = name
        self.cookie = cookie
    
    def __eq__(self, other):
        if isinstance(other, Config) is False:
            return False
        return self.ip == other.ip and self.port == other.port and self.name == other.name

    def __ne__(self, other) -> bool:
        if isinstance(other, Config) is False:
            return True
        return self.ip != other.ip or self.port != other.port or self.name != other.name
    
    def dump(self):
        with open(CONFIG_NAME, "w") as file:
            data = {
                "ip": self.ip,
                "port": self.port,
                "name": self.name,
                "cookie": self.cookie,
            }
            json.dump(data, file)
    
    def update_cookie(self, cookie):
        self.cookie = cookie
        self.dump()

class Client:
    def __init__(self, no_cookie: bool):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.config = None # 客户端配置文件
        self.no_cookie = no_cookie # 禁用cookie恢复
        self.client_player = 0 # 客户端用户标识
        self.client_cards = [] # 持有牌
        self.users_cards = [[] for _ in range(6)] # 所有用户的牌，用于最后游戏结束时展现寻找战犯
        self.is_player = False  # 玩家/旁观者
        self.users_name = ["" for _ in range(6)] # 用户名字
        self.game_over = 0 # 游戏结束标志，非0代表已经结束
        self.now_score = 0 # 场上的分数
        self.now_player = 0 # 当前的玩家
        self.users_cards_num = [0 for _ in range(6)] # 用户牌数
        self.users_score = [0 for _ in range(6)] # 用户分数
        self.users_played_cards = [[] for _ in range(6)] # 场上的牌
        self.head_master = 0 # 头科
        self.his_now_score = 0 # 历史场上分数，用于判断是否发生了得分
        self.his_last_player = None # 历史上一个打牌的人，用于判断是否上次发生打牌事件
        self.is_start = False # 记录是否游戏还在开局
    
    def take_log(self, last_player):
        logger.info(f"----------new round------------")
        logger.info(f"cilent_cards: {self.client_cards}")
        logger.info(f"users_score: {self.users_score}")
        logger.info(f"users_played_cards: {self.users_played_cards}")
        logger.info(f"now_score: {self.now_score}")
        logger.info(f"now_player: {self.users_name[self.now_player]}")
        logger.info(f"last_player: {self.users_name[last_player]}")
        logger.info(f"head_master: {self.users_name[self.head_master] if self.head_master != -1 else None}")
        logger.info(f"his_now_score: {self.his_now_score}")
        logger.info(f"his_last_player: {self.his_last_player}")

    def load_config(self):
        try:
            with open(CONFIG_NAME, "r") as file:
                data = json.load(file)
                self.config = Config(data["ip"], int(data["port"]), data["name"], data["cookie"])
        except:
            self.config = None

        if self.config is not None:
            print("已经检测到之前输入的配置，配置如下:")
        
        while True:
            if self.config is not None:
                print(f"IP地址: {self.config.ip}")
                print(f"端口:   {self.config.port}")
                print(f"用户名: {self.config.name}")
                if utils.user_confirm(prompt="是否使用配置？", default=True) is False:
                    self.config = None
            if self.config is not None:
                break
            while True:
                ip = input(f"请输入IP地址: ")
                port = input(f"请输入端口: ")
                name = input(f"请输入用户名: ")
                try:
                    if self.config != Config(ip, int(port), name):
                        self.config = Config(ip, int(port), name)
                except:
                    print(f"输入有误，请重新输入")
                else:
                    self.config.dump()
                    print('')
                    break

    def connect(self, server_ip, server_port):
        if_connected = False
        try_times = 0
        while if_connected is False and try_times < 10:
            try:
                print("尝试与服务器连接...")
                try_times += 1
                self.client.connect((server_ip, server_port))
            except Exception as e:
                utils.error(f"连接错误: {e}")
                time.sleep(1)
            else:
                if_connected = True
        if if_connected:
            utils.success("连接成功")
        else:
            utils.fatal("连接失败")

    def close(self):
        self.client.close()
    
    def send_data(self, data):
        data = json.dumps(data).encode()
        header = struct.pack('i', len(data))
        self.client.sendall(header)
        self.client.sendall(data)
    
    def recv_data(self):
        HEADER_LEN = 4
        header = self.client.recv(HEADER_LEN)
        header = struct.unpack('i', header)[0]
        data = self.client.recv(header)
        data = json.loads(data.decode())
        return data

    def send_user_info(self):
        # 发送本地的cookie信息
        logger.info(f"Client coockie {self.config.cookie}")
        if self.no_cookie:
            logger.info("Disable cookie")
            self.send_data(False)
        elif self.config.cookie is not None and isinstance(self.config.cookie, str):
            self.send_data(True)
            self.send_data(self.config.cookie)
        else:
            self.send_data(False)
        # 服务端判断cookie是否合法，如果不合法重发cookie
        # 重发cookie的同时还得同步用户名
        if_valid_cookie = self.recv_data()
        if if_valid_cookie:
            print("cookie合法，开始恢复")
            if_recovery = self.recv_data()
            if if_recovery is False:
                raise RuntimeError("恢复失败，是不是有客户端还在运行？")
        else:
            self.send_data(self.config.name)
            self.config.update_cookie(self.recv_data())
            logger.info(f"cookie invalid, new cookie {self.config.cookie}")
    
    # 接收等待大厅信息
    def recv_waiting_hall_info(self):
        th = TerminalHandler()
        while True:
            self.users_name = self.recv_data()
            # 收集用户在线/离线信息
            users_error = self.recv_data()
            waiting_hall_interface(th, self.users_name, users_error)
            if len(self.users_name) == 6:
                break

    # 接收用户信息
    def recv_field_info(self):
        self.is_player = self.recv_data()
        self.users_name = self.recv_data()
        self.client_player = self.recv_data()

        logger.info(f"is_player: {self.is_player}")
        logger.info(f"users_name: {self.users_name}")
        logger.info(f"client_player: {self.client_player}")

    # 接收场上信息
    def recv_round_info(self):
        self.game_over = self.recv_data()
        self.users_score = self.recv_data()
        self.users_cards_num = self.recv_data()
        self.users_played_cards = self.recv_data()
        if self.game_over != 0:
            self.users_cards = self.recv_data()
        self.client_cards = self.recv_data()
        self.now_score = self.recv_data()
        self.now_player = self.recv_data()
        self.head_master = self.recv_data()

    # 向server发送打出牌或skip的信息
    def send_player_info(self):
        self.send_data(self.client_cards)
        self.send_data(self.users_played_cards[self.client_player])
        self.send_data(self.now_score)

    def send_playing_heartbeat(self, finished: bool):
        self.send_data(finished)

    def handle_connection_error(self, func, msg):
        try:
            ret = func()
            return ret
        except Exception as e:
            self.close()
            utils.fatal(f"{msg}: {e}")

    def run(self):
        self.handle_connection_error(self.send_user_info, "在注册时与服务器的链接失效")
        self.handle_connection_error(self.recv_waiting_hall_info, "在游戏时与服务器链接失效(等待大厅)")
        self.handle_connection_error(self.recv_field_info, "在游戏时与服务器链接失效(获取全局信息)")
        print("游戏开始，你是一名" + "玩家" if self.is_player else f"旁观者({self.users_name[self.client_player]})")
        while True:
            self.handle_connection_error(self.recv_round_info, "在游戏时与服务器链接失效(获取牌局信息)")
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
                self.users_cards, self.users_played_cards, self.head_master,
                # 运行时数据
                self.now_score, self.now_player, last_player,
                # 历史数据
                self.his_now_score, self.his_last_player 
            )
            self.take_log(last_player)
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
                def player_playing_cards():
                    new_played_cards, new_score = playing(self.client_cards, last_player, 
                                self.client_player, self.users_played_cards, self)
                    new_played_cards.sort(key = utils.str_to_int)
                    self.users_played_cards[self.client_player] = new_played_cards
                    if new_played_cards != ['F']:
                        for card in new_played_cards:
                            self.client_cards.remove(card)
                    self.now_score += new_score
                    self.send_player_info()
                self.handle_connection_error(player_playing_cards, "在游戏时与服务器链接失效(用户打牌)")

def ctrl_c_handler():
    utils.fatal("Keyboard Interrupt")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='启动六家统客户端')
    parser.add_argument('--ip', type=str, help='ip address')
    parser.add_argument('--port', type=int, help='port')
    parser.add_argument('--user-name', type=str, help='user name')
    parser.add_argument('-n', '--no-cookie', action='store_true', default=False, help='disable cookies')
    args = parser.parse_args()

    logger.init_logger()
    utils.register_signal_handler(ctrl_c_handler)

    client = Client(args.no_cookie)
    if args.ip == None or args.port == None or args.user_name == None:
        client.load_config()
    else:
        client.config = Config(args.ip, args.port, args.user_name)

    client.connect(client.config.ip, client.config.port)
    utils.disable_echo()
    client.run()
    utils.enable_echo()
    client.close()
