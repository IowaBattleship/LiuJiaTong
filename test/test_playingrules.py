#!/usr/bin/env python
#!coding:utf-8
import pytest
import sys 
sys.path.append("..") 
from client.playingrules import *

@pytest.mark.parametrize('user_input, expect', [
    [[15, 15, 15, 15], (CardType.normal_bomb, 15)],
    [[16, 16, 16, 16], (CardType.black_joker_bomb, 16)],
    [[17, 17, 17, 17], (CardType.red_joker_bomb, 17)],
    [[17, 16, 11, 10, 8],  (CardType.straight, 12)],
    [[16, 4, 3, 3],  (CardType.straight_pairs, 4)],
    [[16, 16, 4, 3, 3, 3],  (CardType.straight_triples, 4)],
    [[17, 16, 9, 9, 9, 8, 6, 6, 5, 5],  (CardType.flight, 9)],
    [[17],  (CardType.single, 17)],
    [[17, 15],  (CardType.pair, 15)],
    [[17, 15, 15],  (CardType.triple, 15)],
    [[16, 5, 5, 5, 4],  (CardType.triple_pair, 5)],
])
def test_judge_and_transform_cards(user_input, expect):
    assert judge_and_transform_cards(user_input)==expect


@pytest.mark.parametrize('user_input, user_card, if_first_played, expect', [
    [[4,5,6,7,8,9,13,10,16,17], [4,5,6,7,8,9,9,9,9,9,10,13,14,14,14,15,16,17], True, (True, 25)],
])
def test_if_put_legal(user_input, user_card, if_first_played, expect):
    assert if_input_legal(user_input, user_card, if_first_played)==expect
