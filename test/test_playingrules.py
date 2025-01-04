#!/usr/bin/env python
#!coding:utf-8
import pytest
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from client.playingrules import *
import unittest
from card import Card, Suits

@pytest.mark.parametrize('user_input, expect', [
    [[15,15,15,15], (CardType.normal_bomb, 15)],
    [[16,16,16,16], (CardType.black_joker_bomb, 16)],
    [[17,17,17,17], (CardType.red_joker_bomb, 17)],
    [[8,10,11,16,17], (CardType.straight, 12)],
    [[3,3,4,16], (CardType.straight_pairs, 4)],
    [[3,3,3,4,16,16], (CardType.straight_triples, 4)],
    [[5,5,6,6,8,9,9,9,16,17], (CardType.flight, 9)],
    [[17], (CardType.single, 17)],
    [[15,17], (CardType.pair, 15)],
    [[15,15,17], (CardType.triple, 15)],
    [[4,5,5,5,16], (CardType.triple_pair, 5)],
    [[4,4,5,5,5], (CardType.triple_pair, 5)],
    [[4,4,4,4,17], (CardType.normal_bomb, 4)],
    [[9,9,10,10,11,11,11,12,12,12], (CardType.flight,12)],
    [[8,8,8,17,17], (CardType.normal_bomb, 8)],
])
def test_judge_and_transform_cards(user_input, expect):
    assert judge_and_transform_cards(sorted(user_input, reverse=True)) == expect

@pytest.mark.parametrize('user_input, user_card, last_played_cards, expect', [
    [[4,5,6,7,8,9,13,10,16,17], [4,5,6,7,8,9,9,9,9,9,10,13,14,14,14,15,16,17], None, (False, 25)],
    [[15,15,15,15,15], None, [4,4,4,4,17], (True, 0)],
])
def test_if_input_legal(user_input, user_card, last_played_cards, expect):
    assert if_input_legal(user_input, user_card, last_played_cards) == expect

class TestPlayingRules(unittest.TestCase):
    def test_if_enough_card_valid(self):
        user_card = [Card(Suits.heart, 4), Card(Suits.spade, 5), Card(Suits.diamond, 5),
                     Card(Suits.heart, 6), Card(Suits.heart, 7), Card(Suits.heart, 8)]
        
        user_input = [4, 5, 6, 7, 8]
        _if_enough, score = if_enough_card(user_input, user_card)
        self.assertTrue(_if_enough)
        self.assertEqual(score, 5)

    def test_if_enough_card_invalid_missing_card(self):
        user_card = [Card(Suits.heart, 4), Card(Suits.spade, 5), Card(Suits.diamond, 5),
                     Card(Suits.heart, 6), Card(Suits.heart, 7), Card(Suits.heart, 8)]
        
        user_input = [9]
        _if_enough, score = if_enough_card(user_input, user_card)
        self.assertFalse(_if_enough)
        self.assertEqual(score, 0)

    def test_if_enough_card_invalid_card_number_exceed(self):
        user_card = [Card(Suits.heart, 4), Card(Suits.spade, 5), Card(Suits.diamond, 5),
                     Card(Suits.heart, 6), Card(Suits.heart, 7), Card(Suits.heart, 8)]
        
        user_input = [4, 4]
        _if_enough, score = if_enough_card(user_input, user_card)
        self.assertFalse(_if_enough)
        self.assertEqual(score, 0)

class TestUserInput(unittest.TestCase):
    def test_first_input_legal_valid_input(self):
        self.assertEqual(first_input_legal([3, 3]), True)
        self.assertEqual(first_input_legal([3, 3, 3]), True)
        self.assertEqual(first_input_legal([5, 5]), True)

    def test_first_input_legal_invalid_input(self):
        self.assertEqual(first_input_legal([4, 3]), False)
        self.assertEqual(first_input_legal([4, 3, 3]), False)

if __name__ == '__main__':
    unittest.main()