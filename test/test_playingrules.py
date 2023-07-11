#!/usr/bin/env python
#!coding:utf-8
import pytest
import sys 
sys.path.append("..") 
from client.playingrules import *

@pytest.mark.parametrize('user_input, expect', [
    [[15, 15, 15, 15], (1, 15)],
])
def test_judge_and_transform_cards(user_input, expect):
    assert judge_and_transform_cards(user_input)==expect
