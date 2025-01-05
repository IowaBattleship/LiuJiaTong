from enum import Enum

class Suits(Enum): # 花色
    spade   = "spade" # 黑桃
    heart   = "heart" # 红心
    club    = "club" # 梅花
    diamond = "diamond" # 方块
    empty   = "" # 空，大小王没有花色

class Card:
    # 3~10为数字牌, 11~13为JQK, 14为2, 15为小王, 16为大王
    def __init__(self, suit: Suits, value: int):
        self.suit  = suit  # 花色
        self.value = value # 牌面

    def __lt__(self, other):
        # 确保比较的是Card对象
        if not isinstance(other, Card):
            return NotImplemented
        
        return self.value < other.value
    
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
        if self.value == 14:
            return "2"
        elif self.value == 15:
            return "0"
        elif self.value == 16:
            return "1"
        else:
            return str(self.value)

def generate_cards() -> list[Card]:
    cards = []

    for i in range(4): # 六家统使用四副牌
        # 洗入普通牌
        for value in range(3, 15): # 3~14
            for suit in Suits: # 4种花色
                cards.append(Card(suit, value))
        
        # 洗入大小王
        for value in range(15, 17): # 15~16
            cards.append(Card(Suits.empty, value))
    return cards

SPADE_10 = Card(Suits.spade, 10)
HEART_JACK = Card(Suits.heart, 11)
CLUB_QUEEN = Card(Suits.club, 12)
DIAMOND_KING = Card(Suits.diamond, 13)
