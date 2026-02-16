import 'package:liujiatong/core/models/card.dart';

/// 出牌类型（与 Python playingrules.CardType 一致）
enum CardType {
  illegalType(0),
  normalBomb(1),
  blackJokerBomb(2),
  redJokerBomb(3),
  straight(4),
  straightPairs(5),
  straightTriples(6),
  flight(7),
  single(8),
  pair(9),
  triple(10),
  triplePair(11);

  const CardType(this.value);
  final int value;
}

/// 统计 list 中每个元素出现次数
Map<int, int> _counter(List<int> list) {
  final m = <int, int>{};
  for (final x in list) {
    m[x] = (m[x] ?? 0) + 1;
  }
  return m;
}

/// 除大小王外，统计「相同张数」的牌有多少种。如 typeNum[1]=5 表示 5 种牌各 1 张。
Map<int, int> _typeNum(Map<int, int> cardNum) {
  final m = <int, int>{};
  for (final e in cardNum.entries) {
    if (e.key <= 15) {
      final v = e.value;
      m[v] = (m[v] ?? 0) + 1;
    }
  }
  return m;
}

bool _tryTransformCards(
  Map<int, int> cardNum,
  Iterable<int> rg,
  int jokerNum,
  int tryNum,
) {
  int j = jokerNum;
  for (final i in rg) {
    final cnt = cardNum[i] ?? 0;
    if (cnt > tryNum) return false;
    if (cnt < tryNum) j -= tryNum - cnt;
    if (j < 0) return false;
  }
  return true;
}

({CardType type, int keyCard}) _ifBomb(List<int> cards, Map<int, int> cardNum) {
  if (cards.length < 4) return (type: CardType.illegalType, keyCard: 0);

  int spTypeNum = 0;
  for (final k in cardNum.keys) {
    if (k >= 3 && k <= 15) spTypeNum++;
  }
  if (spTypeNum == 1) return (type: CardType.normalBomb, keyCard: cards.first);
  if (spTypeNum != 0) return (type: CardType.illegalType, keyCard: 0);
  if ((cardNum[16] ?? 0) == 4) return (type: CardType.blackJokerBomb, keyCard: 16);
  if ((cardNum[17] ?? 0) == 4) return (type: CardType.redJokerBomb, keyCard: 17);
  return (type: CardType.illegalType, keyCard: 0);
}

({CardType type, int keyCard}) _ifStraight(
  List<int> cards,
  Map<int, int> cardNum,
  Map<int, int> typeNum,
  int jokerNum,
) {
  if (cards.length != 5 || ((typeNum[1] ?? 0) != 5 && jokerNum == 0)) {
    return (type: CardType.illegalType, keyCard: 0);
  }
  if (cards[jokerNum] - cards.last + 1 > 5) {
    return (type: CardType.illegalType, keyCard: 0);
  }
  List<int> rg;
  if (cards.last > 10) {
    rg = [14, 13, 12, 11, 10];
  } else {
    rg = List.generate(5, (i) => cards.last + i);
  }
  if (_tryTransformCards(cardNum, rg, jokerNum, 1)) {
    return (type: CardType.straight, keyCard: rg.last);
  }
  return (type: CardType.illegalType, keyCard: 0);
}

({CardType type, int keyCard}) _ifStraightPairs(
  List<int> cards,
  Map<int, int> cardNum,
  int jokerNum,
) {
  if (cards.length < 4 || cards.length % 2 == 1) {
    return (type: CardType.illegalType, keyCard: 0);
  }
  final pairsNum = cards.length ~/ 2;
  if (pairsNum == 2) {
    final aCnt = cardNum[14] ?? 0;
    final twoCnt = cardNum[15] ?? 0;
    bool hasOtherRank = false;
    for (final k in cardNum.keys) {
      if (k >= 3 && k <= 15 && k != 14 && k != 15) {
        hasOtherRank = true;
        break;
      }
    }
    if (!hasOtherRank && aCnt <= 2 && twoCnt <= 2 && aCnt + twoCnt + jokerNum == 4) {
      final needJoker = (2 - aCnt).clamp(0, 2) + (2 - twoCnt).clamp(0, 2);
      if (needJoker <= jokerNum) return (type: CardType.straightPairs, keyCard: 1);
    }
  }
  if (pairsNum > 12 || cards[jokerNum] - cards.last + 1 > pairsNum) {
    return (type: CardType.illegalType, keyCard: 0);
  }
  List<int> rg;
  if (cards.last + pairsNum - 1 > 14) {
    rg = List.generate(pairsNum, (i) => 14 - i);
  } else {
    rg = List.generate(pairsNum, (i) => cards.last + i);
  }
  if (_tryTransformCards(cardNum, rg, jokerNum, 2)) {
    return (type: CardType.straightPairs, keyCard: rg.last);
  }
  return (type: CardType.illegalType, keyCard: 0);
}

({CardType type, int keyCard}) _ifStraightTriples(
  List<int> cards,
  Map<int, int> cardNum,
  int jokerNum,
) {
  if (cards.length < 6 || cards.length % 3 != 0) {
    return (type: CardType.illegalType, keyCard: 0);
  }
  final triplesNum = cards.length ~/ 3;
  if (triplesNum > 12 || cards[jokerNum] - cards.last + 1 > triplesNum) {
    return (type: CardType.illegalType, keyCard: 0);
  }
  List<int> rg;
  if (cards.last + triplesNum - 1 > 14) {
    rg = List.generate(triplesNum, (i) => 14 - i);
  } else {
    rg = List.generate(triplesNum, (i) => cards.last + i);
  }
  if (_tryTransformCards(cardNum, rg, jokerNum, 3)) {
    return (type: CardType.straightTriples, keyCard: rg.last);
  }
  return (type: CardType.illegalType, keyCard: 0);
}

({bool ok, int jokerNum}) _tryMinCardType(
  Map<int, int> cardNum,
  Iterable<int> rg,
  int jokerNum,
  int tryNum,
) {
  final m = Map<int, int>.from(cardNum);
  int j = jokerNum;
  for (final i in rg) {
    final cnt = m[i] ?? 0;
    if (cnt < tryNum) j -= tryNum - cnt;
    if (j < 0) return (ok: false, jokerNum: 0);
    if (m.containsKey(i)) m[i] = (m[i]! - tryNum).clamp(0, 0x7fffffff);
  }
  return (ok: true, jokerNum: j);
}

({CardType type, int keyCard}) _ifFlight(
  List<int> cards,
  Map<int, int> cardNum,
  int jokerNum,
) {
  if (cards.length < 10 || cards.length % 5 != 0) {
    return (type: CardType.illegalType, keyCard: 0);
  }
  final triplePairNum = cards.length ~/ 5;
  if (triplePairNum > 12) return (type: CardType.illegalType, keyCard: 0);

  List<int> rg;
  if (cards.last + triplePairNum - 1 > 14) {
    rg = List.generate(triplePairNum, (i) => 14 - i);
  } else {
    rg = List.generate(triplePairNum, (i) => cards.last + i);
  }

  int keyCard = 0;
  var cardNumCopy = Map<int, int>.from(cardNum);
  var res = _tryMinCardType(cardNumCopy, rg, jokerNum, 2);
  if (res.ok) {
    int minPairCard = 0;
    for (int i = cards.last; i <= cards[jokerNum]; i++) {
      if ((cardNumCopy[i] ?? 0) > 0) {
        minPairCard = i;
        break;
      }
    }
    if (minPairCard == 0) {
      if (res.jokerNum == triplePairNum * 3) return (type: CardType.flight, keyCard: 14);
    } else {
      List<int> r2;
      if (minPairCard + triplePairNum - 1 > 14) {
        r2 = List.generate(triplePairNum, (i) => 14 - i);
      } else {
        r2 = List.generate(triplePairNum, (i) => minPairCard + i);
      }
      if (_tryTransformCards(cardNumCopy, r2, res.jokerNum, 3)) {
        keyCard = r2.last;
      }
    }
  }

  int keyCard2 = 0;
  cardNumCopy = Map<int, int>.from(cardNum);
  res = _tryMinCardType(cardNumCopy, rg, jokerNum, 3);
  if (res.ok) {
    keyCard2 = rg.last;
    int minPairCard = 0;
    for (int i = cards.last; i <= cards[jokerNum]; i++) {
      if ((cardNumCopy[i] ?? 0) > 0) {
        minPairCard = i;
        break;
      }
    }
    if (minPairCard == 0) {
      if (res.jokerNum != triplePairNum * 2) keyCard2 = 0;
    } else {
      List<int> r2;
      if (minPairCard + triplePairNum - 1 > 14) {
        r2 = List.generate(triplePairNum, (i) => 14 - i);
      } else {
        r2 = List.generate(triplePairNum, (i) => minPairCard + i);
      }
      if (!_tryTransformCards(cardNumCopy, r2, res.jokerNum, 2)) keyCard2 = 0;
    }
  }

  if (keyCard >= keyCard2 && keyCard != 0) return (type: CardType.flight, keyCard: keyCard);
  if (keyCard2 != 0) return (type: CardType.flight, keyCard: keyCard2);
  return (type: CardType.illegalType, keyCard: 0);
}

({CardType type, int keyCard}) _ifSingle(List<int> cards) {
  if (cards.length == 1) return (type: CardType.single, keyCard: cards.last);
  return (type: CardType.illegalType, keyCard: 0);
}

({CardType type, int keyCard}) _ifPair(
  List<int> cards,
  Map<int, int> cardNum,
  Map<int, int> typeNum,
  int jokerNum,
) {
  if (cards.length != 2) return (type: CardType.illegalType, keyCard: 0);
  if ((typeNum[2] ?? 0) == 1 || (cardNum[16] ?? 0) == 2 || (cardNum[17] ?? 0) == 2) {
    return (type: CardType.pair, keyCard: cards.last);
  }
  if (jokerNum == 1) return (type: CardType.pair, keyCard: cards.last);
  return (type: CardType.illegalType, keyCard: 0);
}

({CardType type, int keyCard}) _ifTriple(
  List<int> cards,
  Map<int, int> cardNum,
  Map<int, int> typeNum,
  int jokerNum,
) {
  if (cards.length != 3) return (type: CardType.illegalType, keyCard: 0);
  if ((typeNum[3] ?? 0) == 1 || (cardNum[16] ?? 0) == 3 || (cardNum[17] ?? 0) == 3) {
    return (type: CardType.triple, keyCard: cards.first);
  }
  if ((jokerNum == 1 && (typeNum[2] ?? 0) == 1) || (jokerNum == 2 && (typeNum[1] ?? 0) == 1)) {
    return (type: CardType.triple, keyCard: cards.last);
  }
  return (type: CardType.illegalType, keyCard: 0);
}

int _findMaxCard(Map<int, int> cardNum, int target, {bool ifJoker = false}) {
  final maxCard = ifJoker ? 17 : 15;
  for (int i = maxCard; i > 2; i--) {
    if ((cardNum[i] ?? 0) == target) return i;
  }
  return 0;
}

({CardType type, int keyCard}) _ifTriplePair(
  List<int> cards,
  Map<int, int> cardNum,
  Map<int, int> typeNum,
  int jokerNum,
) {
  if (cards.length != 5) return (type: CardType.illegalType, keyCard: 0);

  if ((typeNum[3] ?? 0) == 1 && (typeNum[2] ?? 0) == 1) {
    return (type: CardType.triplePair, keyCard: _findMaxCard(cardNum, 3, ifJoker: true));
  }
  if ((cardNum[16] ?? 0) == 3 && (cardNum[17] ?? 0) == 2) {
    return (type: CardType.triplePair, keyCard: _findMaxCard(cardNum, 3, ifJoker: true));
  }
  if ((cardNum[16] ?? 0) == 2 && (cardNum[17] ?? 0) == 3) {
    return (type: CardType.triplePair, keyCard: _findMaxCard(cardNum, 3, ifJoker: true));
  }

  if (jokerNum == 1 && (typeNum[2] ?? 0) == 2) {
    return (type: CardType.triplePair, keyCard: cards[1]);
  }
  if (jokerNum == 1 && (typeNum[3] ?? 0) == 1 && (typeNum[1] ?? 0) == 1) {
    return (type: CardType.triplePair, keyCard: _findMaxCard(cardNum, 3));
  }
  if (jokerNum == 2 && (typeNum[2] ?? 0) == 1 && (typeNum[1] ?? 0) == 1) {
    return (type: CardType.triplePair, keyCard: _findMaxCard(cardNum, 2));
  }
  if (jokerNum == 3 && (typeNum[1] ?? 0) == 2) {
    return (type: CardType.triplePair, keyCard: cards[3]);
  }

  return (type: CardType.illegalType, keyCard: 0);
}

/// 判断出牌类型并得到关键牌。cards 须为按 value 降序排列的牌值列表。
({CardType type, int keyCard}) judgeAndTransformCards(List<int> cards) {
  final cardNum = _counter(cards);
  final typeNum = _typeNum(cardNum);

  var r = _ifBomb(cards, cardNum);
  if (r.type != CardType.illegalType) return r;

  final jokerNum = (cardNum[16] ?? 0) + (cardNum[17] ?? 0);

  r = _ifSingle(cards);
  if (r.type != CardType.illegalType) return r;

  r = _ifPair(cards, cardNum, typeNum, jokerNum);
  if (r.type != CardType.illegalType) return r;

  r = _ifTriple(cards, cardNum, typeNum, jokerNum);
  if (r.type != CardType.illegalType) return r;

  r = _ifTriplePair(cards, cardNum, typeNum, jokerNum);
  if (r.type != CardType.illegalType) return r;

  r = _ifStraight(cards, cardNum, typeNum, jokerNum);
  if (r.type != CardType.illegalType) return r;

  r = _ifStraightPairs(cards, cardNum, jokerNum);
  if (r.type != CardType.illegalType) return r;

  r = _ifStraightTriples(cards, cardNum, jokerNum);
  if (r.type != CardType.illegalType) return r;

  r = _ifFlight(cards, cardNum, jokerNum);
  if (r.type != CardType.illegalType) return r;

  return (type: CardType.illegalType, keyCard: 0);
}

bool firstInputLegal(List<int> userInput) {
  final r = judgeAndTransformCards(userInput);
  return r.type != CardType.illegalType;
}

bool ifNotFirstInputLegal(List<int> userInput, List<int> lastPlayedCards) {
  final cardLen = userInput.length;
  final lastCardLen = lastPlayedCards.length;
  final typeCard = judgeAndTransformCards(userInput);
  if (typeCard.type == CardType.illegalType) return false;

  final lastResult = judgeAndTransformCards(lastPlayedCards);
  final lastTypeCard = lastResult.type;
  final lastKeyCard = lastResult.keyCard;
  final keyCard = typeCard.keyCard;

  int lastIfBomb = 0;
  if (lastTypeCard.value >= 1 && lastTypeCard.value <= 3) lastIfBomb = lastTypeCard.value;
  int ifBomb = 0;
  if (typeCard.type.value >= 1 && typeCard.type.value <= 3) ifBomb = typeCard.type.value;

  if (lastIfBomb != 0 && ifBomb == 0) return false;
  if (lastIfBomb == 0 && ifBomb != 0) return true;
  if (lastIfBomb != 0 && ifBomb != 0) {
    if ((lastIfBomb > ifBomb && cardLen < 9) || (lastIfBomb < ifBomb && lastCardLen > 8)) {
      return false;
    }
    if ((lastIfBomb > ifBomb && cardLen > 8) || (lastIfBomb < ifBomb && lastCardLen < 9)) {
      return true;
    }
    if (lastCardLen > cardLen) return false;
    if (lastCardLen < cardLen) return true;
    return keyCard > lastKeyCard;
  }

  if (lastCardLen != cardLen) return false;
  return keyCard > lastKeyCard;
}

({bool enough, int score}) ifEnoughCard(List<int> userInput, List<Card>? userCard) {
  final inputNum = _counter(userInput);
  if (userCard != null) {
    final cardNum = _counter(userCard.map((c) => c.value).toList());
    for (final e in inputNum.entries) {
      if ((cardNum[e.key] ?? 0) < e.value) return (enough: false, score: 0);
    }
  }
  final scores = (inputNum[5] ?? 0) * 5 + ((inputNum[10] ?? 0) + (inputNum[13] ?? 0)) * 10;
  return (enough: true, score: scores);
}

/// 验证用户出牌是否合法。userInput 为牌值列表；跳过用 [0]。
/// 返回 (是否合法, 分数)。
({bool legal, int score}) validateUserInput(
  List<int> userInput,
  List<Card> userCard,
  List<Card>? lastPlayedCards,
) {
  for (final x in userInput) {
    if (x < 0 || (userInput.length > 1 && x == 0)) return (legal: false, score: 0);
  }
  if (userInput.length == 1 && userInput[0] == 0) {
    return (legal: lastPlayedCards != null, score: 0);
  }

  final enoughResult = ifEnoughCard(userInput, userCard);
  if (!enoughResult.enough) return (legal: false, score: 0);

  final sortedInput = List<int>.from(userInput)..sort((a, b) => b.compareTo(a));
  if (lastPlayedCards == null) {
    return (legal: firstInputLegal(sortedInput), score: enoughResult.score);
  }
  final lastValues = lastPlayedCards.map((c) => c.value).toList()..sort((a, b) => b.compareTo(a));
  return (
    legal: ifNotFirstInputLegal(sortedInput, lastValues),
    score: enoughResult.score,
  );
}

/// 验证选中的牌（Card 列表）是否合法。
bool validateUserSelectedCards(
  List<Card> selectedCards,
  List<Card> userCards,
  List<Card>? lastPlayedCards,
) {
  final values = selectedCards.map((c) => c.value).toList();
  final r = validateUserInput(values, userCards, lastPlayedCards);
  return r.legal;
}
