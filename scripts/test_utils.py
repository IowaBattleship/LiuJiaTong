import sys
import os
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.card import Card, Suits
from common.card_io import strs_to_ints, draw_cards, calculate_score

class TestUtils(unittest.TestCase):
    def test_strs_to_ints(self):
        strs = ['3', '4', '5', '6', '7']
        expected = [3, 4, 5, 6, 7]
        self.assertEqual(strs_to_ints(strs), expected)

    def test_draw_cards(self):
        cards = [Card(Suits.heart, 3), Card(Suits.diamond, 4), Card(Suits.club, 5), Card(Suits.spade, 6), Card(Suits.heart, 7)]
        targets = ['3', '4', '5', '6', '7']
        self.assertEqual(draw_cards(cards, targets), cards)

    def test_calculate_score(self):
        cards = [Card(Suits.heart, 3), Card(Suits.diamond, 4), Card(Suits.club, 5), Card(Suits.spade, 6), Card(Suits.heart, 7)]
        self.assertEqual(calculate_score(cards), 5)

        # KKK 55
        cards = [Card(Suits.heart, 13), Card(Suits.diamond, 13), Card(Suits.club, 13), Card(Suits.spade, 5), Card(Suits.heart, 5)]
        self.assertEqual(calculate_score(cards), 40)

        # BBB 55
        cards = [Card(Suits.heart, 10), Card(Suits.diamond, 10), Card(Suits.club, 10), Card(Suits.spade, 5), Card(Suits.heart, 5)]
        self.assertEqual(calculate_score(cards), 40)

        # 555 22
        cards = [Card(Suits.heart, 5), Card(Suits.diamond, 5), Card(Suits.club, 5), Card(Suits.spade, 15), Card(Suits.heart, 15)]
        self.assertEqual(calculate_score(cards), 15)

if __name__ == '__main__':
    unittest.main()