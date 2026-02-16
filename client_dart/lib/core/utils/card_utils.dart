import 'package:liujiatong/core/models/card.dart';

/// 牌面字符 → 牌值。F 表示跳过，返回 0；非法返回 -1。
int strToInt(String c) {
  if (c.isEmpty) return -1;
  if (c.compareTo('3') >= 0 && c.compareTo('9') <= 0) return int.parse(c);
  switch (c) {
    case 'B':
      return 10;
    case 'J':
      return 11;
    case 'Q':
      return 12;
    case 'K':
      return 13;
    case 'A':
      return 14;
    case '2':
      return 15;
    case '0':
      return 16;
    case '1':
      return 17;
    case 'F':
      return 0;
    default:
      return -1;
  }
}

/// 牌面图片资源路径（与 pubspec 中 assets/images/ 对应），用于 Image.asset。
/// Flutter 要求 name 与 pubspec 声明一致，使用 assets/images/xxx.png。
String cardImageAssetPath(Card card) {
  if (card.suit == Suits.empty) {
    return 'assets/images/${card.value == 16 ? "JOKER-B" : "JOKER-A"}.png';
  }
  final suffix =
      card.value > 10 ? intToStr(card.value) : card.value.toString();
  return 'assets/images/${card.suit.value}$suffix.png';
}

/// 背景图资源路径（牌背）。
String get backgroundImageAssetPath => 'assets/images/Background.png';

/// 牌值 → 牌面字符。0 为跳过 F。
String intToStr(int x) {
  if (x >= 3 && x <= 9) return x.toString();
  switch (x) {
    case 10:
      return 'B';
    case 11:
      return 'J';
    case 12:
      return 'Q';
    case 13:
      return 'K';
    case 14:
      return 'A';
    case 15:
      return '2';
    case 16:
      return '0';
    case 17:
      return '1';
    case 0:
      return 'F';
    default:
      return '-';
  }
}

List<int>? strsToInts(List<String>? cards) {
  if (cards == null) return null;
  return cards.map(strToInt).toList();
}

List<int>? cardsToInts(List<Card>? cards) {
  if (cards == null) return null;
  return cards.map((c) => c.value).toList();
}

List<String>? cardsToStrs(List<Card>? cards) {
  if (cards == null) return null;
  return cards.map((c) => c.toString()).toList();
}

/// 从手牌中按 targets 牌面顺序取出对应的牌（双指针）。
List<Card> drawCards(List<Card> cards, List<String> targets) {
  final result = <Card>[];
  int i = 0, j = 0;
  while (i < cards.length && j < targets.length) {
    if (cards[i].value == strToInt(targets[j])) {
      result.add(cards[i]);
      i++;
      j++;
    } else {
      i++;
    }
  }
  return result;
}

/// 出牌中的分数：5→5分，10/K→10分。
int calculateScore(List<Card> cards) {
  int score = 0;
  for (final c in cards) {
    if (c.value == 5) {
      score += 5;
    } else if (c.value == 10 || c.value == 13) {
      score += 10;
    }
  }
  return score;
}

/// 统计某牌面在手牌中的数量。card 为 displayStr 字符，如 "5"、"J"。
int getCardCount(List<Card> clientCards, String card) {
  final v = strToInt(card);
  if (v <= 0) return 0;
  return clientCards.where((c) => c.value == v).length;
}

/// 头科是否与 clientId 同队（0,2,4 一队；1,3,5 一队）。
bool headMasterInTeam(int headMaster, int clientId) {
  return headMaster == clientId ||
      headMaster == (clientId + 2) % 6 ||
      headMaster == (clientId + 4) % 6;
}

/// 头科队的三人总分。
int calculateHeadMasterTeamScore(int clientId, List<int> usersScores) {
  return usersScores[clientId] +
      usersScores[(clientId + 2) % 6] +
      usersScores[(clientId + 4) % 6];
}

/// 非头科队中已出完牌的玩家分数之和。
int calculateNormalTeamScore(
  int clientId,
  List<int> usersCardsNum,
  List<int> usersScores,
) {
  int teamScore = 0;
  for (final i in [clientId, (clientId + 2) % 6, (clientId + 4) % 6]) {
    if (usersCardsNum[i] == 0) teamScore += usersScores[i];
  }
  return teamScore;
}

/// 我方与对方队伍分数。
List<int> calculateTeamScores(
  int headMaster,
  int clientId,
  List<int> usersCardsNum,
  List<int> usersScores,
) {
  int myTeamScore;
  int opposingTeamScore;
  if (headMasterInTeam(headMaster, clientId)) {
    myTeamScore = calculateHeadMasterTeamScore(clientId, usersScores);
    opposingTeamScore = calculateNormalTeamScore(
      (clientId + 1) % 6,
      usersCardsNum,
      usersScores,
    );
  } else if (headMasterInTeam(headMaster, (clientId + 1) % 6)) {
    opposingTeamScore =
        calculateHeadMasterTeamScore((clientId + 1) % 6, usersScores);
    myTeamScore =
        calculateNormalTeamScore(clientId, usersCardsNum, usersScores);
  } else {
    myTeamScore =
        calculateNormalTeamScore(clientId, usersCardsNum, usersScores);
    opposingTeamScore = calculateNormalTeamScore(
      (clientId + 1) % 6,
      usersCardsNum,
      usersScores,
    );
  }
  return [myTeamScore, opposingTeamScore];
}

/// 上一位出牌玩家下标（逆序找第一个非空出牌）。
int lastPlayed(List<List<dynamic>> playedCards, int player) {
  int i = (player - 1 + 6) % 6;
  while (i != player) {
    if (playedCards[i].isNotEmpty) return i;
    i = (i - 1 + 6) % 6;
  }
  return player;
}
