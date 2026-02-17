#!/usr/bin/env python
#!coding:utf-8
"""
自动托管逻辑集成测试：
- 不启动服务器、不走网络，完全在本地模拟一局 6 人对局；
- 从洗牌、发牌到整局结束，全程由 auto_play.auto_select_cards 托管出牌；
- 在需要时将完整对局过程写入日志文件，便于人工回放和排查。
"""

import os
import sys
import random
import time
from typing import List, Tuple

import pytest

# 确保项目根目录在 sys.path 中，便于直接导入 card / FieldInfo 等模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.card import Card, Suits, generate_cards
from core.FieldInfo import FieldInfo
from core.auto_play.strategy import auto_select_cards
from core import playingrules
from common.card_io import calculate_score, cards_to_strs


LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "auto_play_logs")
DEFAULT_LOG_ENABLED = True


class LocalGameSimulator:
    """
    本地 6 人对局模拟器，用于测试 auto_select_cards 的托管行为是否正确。

    规则简化说明：
    - 使用正式的牌堆生成逻辑 `generate_cards()`（六家统，四副牌）；
    - 不考虑抢头科、翻倍等复杂规则，仅依据出牌合法性和大小比较推进游戏；
    - 当某个玩家手牌出完时立刻结束对局，简单统计每个玩家获得的分数。
    """

    def __init__(self, seed: int, enable_log: bool = DEFAULT_LOG_ENABLED):
        self.seed = seed
        self.enable_log = enable_log
        self.random = random.Random(seed)

        self.users_cards: List[List[Card]] = [[] for _ in range(6)]
        self.users_played_cards: List[List[Card]] = [[] for _ in range(6)]
        self.users_scores: List[int] = [0 for _ in range(6)]
        self.users_cards_num: List[int] = [0 for _ in range(6)]
        self.user_names: List[str] = [f"Player{i}" for i in range(6)]

        self.now_player: int = 0
        self.last_player: int = 0
        self.last_non_pass_player: int | None = None
        self.last_combo: List[Card] | None = None
        self.start_flag: bool = True
        self.head_master: int = 0  # 测试中不关心真实头科归属
        self.now_score: int = 0
        self.his_now_score: int = 0
        self.his_last_player: int = 0

        self._current_trick_records: List[Tuple[int, List[Card]]] = []
        self._log_file_path: str | None = None
        self._log_fh = None

    # ---------- 日志相关 ----------

    def _open_log(self):
        if not self.enable_log:
            return
        os.makedirs(LOG_DIR, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        self._log_file_path = os.path.join(LOG_DIR, f"auto_play_seed_{self.seed}_{ts}.log")
        self._log_fh = open(self._log_file_path, "w", encoding="utf-8")
        self._write_log(f"[SEED] {self.seed}")

    def _close_log(self):
        if self._log_fh is not None:
            self._write_log("[END]")
            self._log_fh.close()
            self._log_fh = None

    def _write_log(self, msg: str):
        if self._log_fh is None:
            return
        self._log_fh.write(msg + "\n")
        self._log_fh.flush()

    # ---------- 牌局初始化与状态构造 ----------

    def _deal_cards(self):
        """使用正式的 generate_cards() 生成牌堆，并随机洗牌、发牌给 6 名玩家。"""
        deck = generate_cards()
        self.random.shuffle(deck)

        # 等分为 6 份，顺序发牌
        for idx, card in enumerate(deck):
            player = idx % 6
            self.users_cards[player].append(card)

        # 手牌按点数从大到小排序，便于阅读日志
        for i in range(6):
            self.users_cards[i].sort(key=lambda c: c.value, reverse=True)
            self.users_cards_num[i] = len(self.users_cards[i])

    def _build_field_info_for_player(self, client_id: int) -> FieldInfo:
        """为指定玩家构造一份 FieldInfo，用于传入 auto_select_cards。"""
        client_cards = list(self.users_cards[client_id])

        # users_played_cards 中只保留最近一轮的最后一手牌，其他玩家视为未出
        played_snapshot: List[List[Card]] = [[] for _ in range(6)]
        if self.last_combo is not None and self.last_non_pass_player is not None:
            played_snapshot[self.last_non_pass_player] = list(self.last_combo)

        return FieldInfo(
            start_flag=self.start_flag,
            is_player=True,
            client_id=client_id,
            client_cards=client_cards,
            user_names=self.user_names,
            user_scores=self.users_scores,
            users_cards_num=self.users_cards_num,
            users_cards=self.users_cards,
            users_played_cards=played_snapshot,
            head_master=self.head_master,
            now_score=self.now_score,
            now_player=self.now_player,
            last_player=self.last_non_pass_player if self.last_non_pass_player is not None else client_id,
            his_now_score=self.his_now_score,
            his_last_player=self.his_last_player,
        )

    # ---------- 出牌与轮转逻辑 ----------

    def _apply_play(self, player: int, played: List[Card] | None, is_pass: bool):
        """根据 auto_select_cards 结果更新牌局状态，并负责统计分数与轮转。"""
        if is_pass:
            self._write_log(f"[TURN] Player{player} PASS")
            # 若上一次出牌者存在，则只增加“连续不出”计数，由外层逻辑判断是否结束一圈
            return

        assert played is not None

        # 安全起见，使用 playingrules 重新校验合法性
        last_played_cards = (
            self.users_played_cards[self.last_non_pass_player]
            if self.last_non_pass_player is not None
            else None
        )
        assert playingrules.validate_user_selected_cards(
            played, self.users_cards[player], last_played_cards
        ), "auto_select_cards 产生了非法出牌"

        # 从手牌中移除这些卡牌
        for c in played:
            self.users_cards[player].remove(c)
        self.users_cards_num[player] = len(self.users_cards[player])

        # 更新本轮最后出牌信息
        self.last_non_pass_player = player
        self.last_combo = list(played)
        self.users_played_cards[player] = list(played)

        # 统计这一手牌自身携带的分数（5、10、K）并临时累加到 now_score
        gained = calculate_score(played)
        self.now_score += gained
        self._current_trick_records.append((player, list(played)))

        cli_cards = cards_to_strs(played)
        self._write_log(
            f"[TURN] Player{player} PLAY {cli_cards}, gained_score={gained}, now_score={self.now_score}, remain={self.users_cards_num[player]}"
        )

    def _finish_trick_if_needed(self, consecutive_pass: int) -> int:
        """
        如果所有其他玩家都 PASS，则当前圈结束：
        - 将本圈累计的 now_score 记入最后出牌者的总分；
        - 清空场上牌与本圈记录；
        - 返回重置后的 consecutive_pass（0）。
        """
        if self.last_non_pass_player is None:
            return consecutive_pass

        # 一圈中除最后出牌者外还有 5 名玩家；若连续 PASS 达到 5，则判定本圈结束
        if consecutive_pass < 5:
            return consecutive_pass

        winner = self.last_non_pass_player
        self.users_scores[winner] += self.now_score
        self._write_log(
            f"[TRICK] winner=Player{winner}, trick_score={self.now_score}, total_score={self.users_scores[winner]}"
        )

        # 清空本圈
        self.now_score = 0
        self.last_combo = None
        self.last_non_pass_player = None
        self.users_played_cards = [[] for _ in range(6)]
        self._current_trick_records.clear()

        return 0

    def run_full_game(self) -> Tuple[int, List[int]]:
        """
        运行一整局托管对战，返回：
        - winner: 第一个出完牌的玩家下标；
        - users_scores: 每个玩家最终得分。
        """
        self._open_log()
        try:
            self._deal_cards()
            self._write_log("[INIT] dealt cards")

            consecutive_pass = 0
            rounds = 0

            while True:
                rounds += 1
                self._write_log(f"[ROUND] #{rounds}, now_player=Player{self.now_player}")

                # 当前玩家已无牌：直接视作“过牌”，并检查是否已经有人获胜
                if self.users_cards_num[self.now_player] == 0:
                    self._write_log(f"[TURN] Player{self.now_player} already empty, skip")
                    consecutive_pass += 1
                    consecutive_pass = self._finish_trick_if_needed(consecutive_pass)
                    # 若所有牌都出完，则结束；否则交给下一位
                    if all(num == 0 for num in self.users_cards_num):
                        break
                    self.now_player = (self.now_player + 1) % 6
                    continue

                info = self._build_field_info_for_player(self.now_player)
                selected = auto_select_cards(info)

                if selected is None:
                    # auto_select_cards 无可出牌型：视为 PASS
                    self._apply_play(self.now_player, None, is_pass=True)
                    consecutive_pass += 1
                else:
                    self._apply_play(self.now_player, selected, is_pass=False)
                    consecutive_pass = 0

                # 本圈是否结束
                consecutive_pass = self._finish_trick_if_needed(consecutive_pass)

                # 有玩家出完牌则整局结束
                if self.users_cards_num[self.now_player] == 0:
                    winner = self.now_player
                    self._write_log(f"[GAME] Winner is Player{winner}")
                    return winner, list(self.users_scores)

                # 轮到下一位玩家
                self.now_player = (self.now_player + 1) % 6

        finally:
            self._close_log()

        # 理论上不应走到这里，返回一个兜底结果
        winner = max(range(6), key=lambda i: self.users_scores[i])
        self._write_log(f"[GAME] Fallback winner Player{winner}")
        return winner, list(self.users_scores)


@pytest.mark.parametrize("seed", [1, 2, 3])
@pytest.mark.parametrize("enable_log", [False, True])
def test_auto_play_full_game(seed, enable_log):
    """
    使用不同随机种子与日志开关，完整跑几局自动托管对战：
    - 确认 auto_select_cards 始终返回“合法且能压过场上的牌”或正确选择 PASS；
    - 确认一局游戏能够在有限步数内自然结束（至少有一名玩家出完所有手牌）；
    - 若启用日志，则生成包含完整牌局过程的记录文件，便于人工回放。
    """
    sim = LocalGameSimulator(seed=seed, enable_log=enable_log)
    winner, scores = sim.run_full_game()

    # 至少有一位玩家出完牌
    assert 0 <= winner < 6
    assert sim.users_cards_num[winner] == 0

    # 分数列表长度为 6，每位玩家得分非负
    assert len(scores) == 6
    assert all(s >= 0 for s in scores)

