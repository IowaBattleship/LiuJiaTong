#!/usr/bin/env python
#!coding:utf-8
import pytest
import sys 
sys.path.append("..") 
from client.playingrules import *

@pytest.mark.parametrize('user_input, expect', [
    [[15, 15, 15, 15], (1, 15)], # test normal bomb
    [[16, 16, 16, 16], (2, 16)], # test black joker bomb
    [[17, 17, 17, 17], (3, 17)], # test red joker bomb
    [[3, 4, 5, 6, 7],  (4, 7)],  # test straight
])
def test_judge_and_transform_cards(user_input, expect):
    assert judge_and_transform_cards(user_input)==expect
