import socket
import json
import tkinter as tk
import time
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
import logging
import logger
from playing_handler import playing
from terminal_printer import TerminalHandler
from my_network import send_data_to_socket, recv_data_from_socket
from interface import main_interface, game_over_interface, waiting_hall_interface
from config import Config, CONFIG_NAME

ASCII_ART = '''
    __    _              ___          ______                 
   / /   (_)_  __       / (_)___ _   /_  __/___  ____  ____ _
  / /   / / / / /  __  / / / __ `/    / / / __ \/ __ \/ __ `/
 / /___/ / /_/ /  / /_/ / / /_/ /    / / / /_/ / / / / /_/ / 
/_____/_/\__,_/   \____/_/\__,_/    /_/  \____/_/ /_/\__, /  
                                                    /____/   
'''

class Client:
    def __init__(self, no_cookie: bool):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # 连接到服务端

        self.config             = None                   # 客户端配置文件
        self.no_cookie          = no_cookie              # 禁用cookie恢复
        self.client_player      = 0                      # 客户端用户标识
        self.client_cards       = []                     # 持有牌
        self.users_cards        = [[] for _ in range(6)] # 所有用户的牌，用于最后游戏结束时展现寻找战犯
        self.is_player          = False                  # 玩家/旁观者
        self.users_name         = ["" for _ in range(6)] # 用户名字
        self.game_over          = 0                      # 游戏结束标志，非0代表已经结束
        self.now_score          = 0                      # 场上的分数
        self.now_player         = 0                      # 当前的玩家
        self.users_cards_num    = [0 for _ in range(6)]  # 用户牌数
        self.users_score        = [0 for _ in range(6)]  # 用户分数
        self.users_played_cards = [[] for _ in range(6)] # 场上的牌
        self.head_master        = 0                      # 头科
        self.his_now_score      = 0                      # 历史场上分数，用于判断是否发生了得分
        self.his_last_player    = None                   # 历史上一个打牌的人，用于判断是否上次发生打牌事件
        self.is_start           = False                  # 记录是否游戏还在开局, False代表游戏尚未开始
        self.logger             = None                   # 日志 01/05/2025: 每个用户都使用自己的looger
    
    # 记录日志
    def take_log(self, last_player):
        logger.info(f"----------new round------------")
        self.log_client_cards()
        logger.info(f"users_score: {self.users_score}")
        logger.info(f"users_cards_num: {self.users_cards_num}")
        logger.info(f"users_played_cards: {self.users_played_cards}")
        logger.info(f"now_score: {self.now_score}")
        logger.info(f"now_player: {self.users_name[self.now_player]}")
        logger.info(f"last_player: {self.users_name[last_player]}")
        logger.info(f"head_master: {self.users_name[self.head_master] if self.head_master != -1 else None}")
        logger.info(f"his_now_score: {self.his_now_score}")
        logger.info(f"his_last_player: {self.his_last_player}")

    def log_client_cards(self):
        cards_str = [str(c) for c in self.client_cards]
        logger.info(f"client_cards: {cards_str}")

    def load_config(self):
        """
        加载配置文件，并根据配置文件或用户输入初始化配置对象
        """
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
                if utils.user_confirm(prompt="是否使用配置？", default=True) is True:
                    # 配置logger
                    self.init_logger()
                    break

            # 用户输入配置信息
            self.config = None
            while True:
                ip = input(f"请输入IP地址: ")
                port = input(f"请输入端口: ")
                name = input(f"请输入用户名: ")
                try:
                    if self.config != Config(ip, int(port), name):
                        self.config = Config(ip, int(port), name)
                        self.init_logger()
                except:
                    print(f"输入有误，请重新输入")
                else:
                    self.config.dump()
                    print('')
                    break

    def init_logger(self):
        # 设置输出文件为self.config.name+时间戳.log
        log_filename = f"{self.config.name}_{time.strftime('%Y-%m-%d_%H-%M-%S')}.log"
        log_filepath = os.path.join(logger.LOGGER_DIR, log_filename)  # 指定日志文件的路径
        # 检查文件是否存在
        if os.path.exists(log_filepath):
            os.remove(log_filepath)
        # 创建日志文件
        open(log_filepath, 'w').close()

        # 创建一个日志记录器
        self.logger = logging.getLogger(self.config.name)
        self.logger.setLevel(logging.INFO)  # 设置日志级别

        # 创建一个文件处理器，用于将日志写入文件
        file_handler = logging.FileHandler(log_filepath)
        file_handler.setLevel(logging.INFO)

        # 定义日志格式
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)

        # 为日志记录器添加处理器
        self.logger.addHandler(file_handler)

        # 避免日志消息被多次输出
        self.logger.propagate = False

        self.logger.info(f"Client logger initialized. Client coockie {self.config.cookie}")

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

    # 关闭客户端
    def close(self):
        self.client.close()
    
    # 11/03/2024: 把网络相关代码移动到MyNetwork.py中了

    def send_user_info(self):
        # 发送本地的cookie信息
        logger.info(f"Client coockie {self.config.cookie}")
        if self.no_cookie:
            logger.info("Disable cookie")
            send_data_to_socket(False, self.client)
        elif self.config.cookie is not None and isinstance(self.config.cookie, str):
            send_data_to_socket(True, self.client)
            send_data_to_socket(self.config.cookie, self.client)
        else:
            send_data_to_socket(False, self.client)
            
        # 服务端判断cookie是否合法，如果不合法重发cookie
        # 重发cookie的同时还得同步用户名
        if_valid_cookie = recv_data_from_socket(self.client)
        if if_valid_cookie:
            utils.success("cookie合法，开始恢复")
            if_recovery = recv_data_from_socket(self.client)
            if if_recovery is False:
                raise RuntimeError("恢复失败，是不是有客户端还在运行？")
        else:
            send_data_to_socket(self.config.name, self.client)
            self.config.update_cookie(recv_data_from_socket(self.client))
            logger.info(f"cookie invalid, new cookie {self.config.cookie}")
    
    # 接收等待大厅信息
    def recv_waiting_hall_info(self):
        th = TerminalHandler()
        while True:
            self.users_name = recv_data_from_socket(self.client)
            # 收集用户在线/离线信息
            users_error = recv_data_from_socket(self.client)
            waiting_hall_interface(th, self.users_name, users_error)
            if len(self.users_name) == 6:
                break

    # 接收用户信息
    def recv_field_info(self):
        self.is_player = recv_data_from_socket(self.client)
        self.users_name = recv_data_from_socket(self.client)
        self.client_player = recv_data_from_socket(self.client)

        logger.info(f"is_player: {self.is_player}")
        logger.info(f"users_name: {self.users_name}")
        logger.info(f"client_player: {self.client_player}")

    # 接收场上信息
    def recv_round_info(self):
        self.game_over = recv_data_from_socket(self.client)
        self.users_score = recv_data_from_socket(self.client)
        self.users_cards_num = recv_data_from_socket(self.client)
        self.users_played_cards = recv_data_from_socket(self.client)
        if self.game_over != 0:
            self.users_cards = recv_data_from_socket(self.client)
        self.client_cards = recv_data_from_socket(self.client)
        self.now_score = recv_data_from_socket(self.client)
        self.now_player = recv_data_from_socket(self.client)
        self.head_master = recv_data_from_socket(self.client)

    # 向server发送打出牌或skip的信息
    def send_player_info(self):
        send_data_to_socket(self.client_cards, self.client) # 发送用户手牌
        send_data_to_socket(self.users_played_cards[self.client_player], self.client) # 发送自己出的牌
        send_data_to_socket(self.now_score, self.client) # 发送场上分数

    def send_playing_heartbeat(self, finished: bool):
        send_data_to_socket(finished, self.client) 

    def handle_connection_error(self, func, msg):
        try:
            ret = func()
            return ret
        except Exception as e:
            self.close()
            utils.fatal(f"{msg}: {e}")

    def run(self):
        """
        开始游戏

        1. 首先尝试与服务器进行连接
        2. 服务器返回当前等待大厅信息
        3. 服务器返回当前场上信息
        4. 游戏开始
        5. 客户端轮询地在等待大厅中等待
        6. 如果是玩家，轮到自己出牌
        7. 如果是旁观者，直接显示牌局
        8. 如果游戏结束，显示游戏结果

        :return:
        """
        pass
        self.handle_connection_error(self.send_user_info, "在注册时与服务器的链接失效")
        print(ASCII_ART)
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

            # 用户界面
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
                logger.info(f"game_over: {self.game_over}")
                logger.info(f"users_cards: {self.users_cards}")
                game_over_interface(self.client_player, self.game_over)
                break

            # 轮到出牌
            if self.is_player and self.client_player == self.now_player:
                def player_playing_cards():
                    self.logger.info("player_playing_cards")
                    # 获取用户输入
                    new_played_cards, new_score = playing(
                        self.client_cards, 
                        last_player, 
                        self.client_player,
                        self.users_played_cards,
                        self
                    )
                    new_played_cards.sort(key = lambda x: x.value) # 排序

                    # 更新本地数据
                    self.users_played_cards[self.client_player] = new_played_cards # 更新玩家打出的牌
                    if new_played_cards != ['F']:
                        for card in new_played_cards:
                            self.client_cards.remove(card) # 更新剩余手牌
                    self.now_score += new_score # 更新场上分数

                    # 更新服务端数据
                    self.send_player_info() # 将数据发送给服务器
                self.handle_connection_error(player_playing_cards, "在游戏时与服务器链接失效(用户打牌)")
