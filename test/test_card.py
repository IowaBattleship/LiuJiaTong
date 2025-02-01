import unittest
import os
import sys
import pickle

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from card import Card, Suits

class TestCard(unittest.TestCase):
    def test_init(self):
        """测试 Card 类的初始化"""
        card = Card(Suits.heart, 3)
        self.assertEqual(card.value, 3)
        self.assertEqual(card.suit, Suits.heart)

        card = Card(Suits.empty, 15)
        self.assertEqual(card.value, 15)
        self.assertEqual(card.suit, Suits.empty)

    def test_to_dict(self):
        """测试 Card 类的 to_dict 方法"""
        card = Card(Suits.spade, 11)
        expected_dict = {'suit': 'Spade', 'value': 11}
        self.assertEqual(card.to_dict(), expected_dict)
    
    def test_from_dict(self):
        """测试 from_dict 类方法"""
        card_dict = {'suit': 'Diamond', 'value': 12}
        card = Card.from_dict(card_dict)
        self.assertIsInstance(card, Card)
        self.assertEqual(card.suit, Suits.diamond)
        self.assertEqual(card.value, 12)

    def test_pickle_dump_load(self):
        card = Card(Suits.spade, 11)
        data = pickle.dumps([[card]])
        construct = pickle.loads(data)
        self.assertEqual(construct[0][0].suit, Suits.spade)
        self.assertEqual(construct[0][0].value, 11)

class TestSuits(unittest.TestCase):
    def test_suits(self):
        self.assertEqual(Suits.heart.value, 'Heart')
        self.assertEqual(Suits.diamond.value, 'Diamond')
        self.assertEqual(Suits.club.value, 'Club')
        self.assertEqual(Suits.spade.value, 'Spade')
        self.assertEqual(Suits.empty.value, '')

if __name__ == '__main__':
    unittest.main()