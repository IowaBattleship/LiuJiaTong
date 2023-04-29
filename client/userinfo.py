class UserInfo:
    def __init__(self):
        self.name = ''
        self.cards = []  # 持有牌
        self.played_card = []  # 打出的牌
        self.score = 0  # 抓分

    def input_name(self):
        self.name = input('Please input your name: ')

