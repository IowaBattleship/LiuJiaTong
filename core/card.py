from enum import Enum

class Suits(Enum): # 花色
    spade   = "Spade" # 黑桃
    heart   = "Heart" # 红心
    club    = "Club" # 梅花
    diamond = "Diamond" # 方块
    empty   = "" # 空，大小王没有花色

class Card:
    # 3~10为数字牌, 11~13为JQK, 14为2, 15为小王, 16为大王
    def __init__(self, suit: Suits, value: int):
        self.suit  = suit  # 花色
        self.value = value # 牌面

    # def __le__(self, other):
    #     if isinstance(other, Card):
    #         return self.value <= other.value
    #     if isinstance(other, int):
    #         return self.value <= other
        
    #     return NotImplemented
    
    # def __ge__(self, other):
    #     if isinstance(other, Card):
    #         return self.value >= other.value
    #     if isinstance(other, int):
    #         return self.value >= other
        
    #     return NotImplemented
    def __lt__(self, other):
        # 确保比较的是Card对象或者int
        if isinstance(other, Card):
            return self.value < other.value
        if isinstance(other, int):
            return self.value < other
        
        return NotImplemented
    
    # def __gt__(self, other):
    #     if isinstance(other, Card):
    #         return self.value > other.value
    #     if isinstance(other, int):
    #         return self.value > other
        
    #     return NotImplemented
    
    def __eq__(self, other):
        if isinstance(other, Card):
            return self.value == other.value and self.suit == other.suit
        if isinstance(other, int):
            return self.value == other
        
        return NotImplemented
    
    # def __ne__(self, other):
    #     if isinstance(other, Card):
    #         return self.value != other.value
    #     if isinstance(other, int):
    #         return self.value != other
        
    #     return NotImplemented
    
    # # 减法
    # def __sub__(self, other):
    #     if isinstance(other, Card):
    #         return self.value - other.value
    #     if isinstance(other, int):
    #         return self.value - other
        
    # def __add__(self, other):
    #     if isinstance(other, Card):
    #         return self.value + other.value
    #     if isinstance(other, int):
    #         return self.value + other
    
    # def __hash__(self):
    #     return hash((self.suit, self.value))
    
    def __str__(self):
        return f"{self.suit}_{self.get_cli_str()}"
    
    @classmethod
    def from_dict(cls, card_dict):
        return cls(Suits(card_dict['suit']), card_dict['value'])
    
    def to_dict(self):
        # 返回一个可以被 json.dumps() 序列化的字典
        return {'suit': self.suit.value, 'value': self.value}
    
    # 用于在 CLI 中显示
    def get_cli_str(self):
        if self.value == 10:
            return "B"
        elif self.value == 11:
            return "J"
        elif self.value == 12:
            return "Q"
        elif self.value == 13:
            return "K"
        elif self.value == 14:
            return "A"
        elif self.value == 15:
            return "2"
        elif self.value == 16:
            return "0"
        elif self.value == 17:
            return "1"
        else:
            return str(self.value)

def generate_cards() -> list[Card]:
    cards = []

    for _ in range(4): # 六家统使用四副牌
        # 洗入普通牌
        for value in range(3, 16): # 3~15
            for suit in Suits: # 4种花色
                if suit == Suits.empty:
                    continue
                cards.append(Card(suit, value))
        
        # 洗入大小王
        for value in range(16, 18): # 16~17
            cards.append(Card(Suits.empty, value))
    return cards

SPADE_10 = Card(Suits.spade, 10)
HEART_JACK = Card(Suits.heart, 11)
CLUB_QUEEN = Card(Suits.club, 12)
DIAMOND_KING = Card(Suits.diamond, 13)
