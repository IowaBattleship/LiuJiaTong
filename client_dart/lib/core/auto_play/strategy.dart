import 'package:liujiatong/core/models/card.dart';
import 'package:liujiatong/core/models/field_info.dart';
import 'package:liujiatong/core/rules/playing_rules.dart';

/// 按点数分组手牌，value -> [Card,...]
Map<int, List<Card>> _groupByValue(List<Card> cards) {
  final byValue = <int, List<Card>>{};
  for (final c in cards) {
    byValue.putIfAbsent(c.value, () => []).add(c);
  }
  return byValue;
}

/// 在已排序的候选点数中找到若干连续段
List<List<int>> _findConsecutiveSegments(List<int> candidates) {
  final segments = <List<int>>[];
  if (candidates.isEmpty) return segments;
  var cur = <int>[candidates.first];
  for (var i = 1; i < candidates.length; i++) {
    final v = candidates[i];
    if (v == cur.last + 1) {
      cur.add(v);
    } else {
      segments.add(cur);
      cur = [v];
    }
  }
  segments.add(cur);
  return segments;
}

Iterable<List<Card>> _generateSingles(
  Map<int, List<Card>> byValue,
  List<int> valuesSorted,
) sync* {
  for (final v in valuesSorted) {
    yield [byValue[v]!.first];
  }
}

Iterable<List<Card>> _generatePairs(
  Map<int, List<Card>> byValue,
  List<int> valuesSorted,
) sync* {
  for (final v in valuesSorted) {
    if (byValue[v]!.length >= 2) yield byValue[v]!.take(2).toList();
  }
}

Iterable<List<Card>> _generateTriples(
  Map<int, List<Card>> byValue,
  List<int> valuesSorted,
) sync* {
  for (final v in valuesSorted) {
    if (byValue[v]!.length >= 3) yield byValue[v]!.take(3).toList();
  }
}

/// 只考虑不含大小王、不使用大小王补牌的顺子
Iterable<List<Card>> _generateStraights(Map<int, List<Card>> byValue) sync* {
  final cardVals = byValue.keys.where((v) => v >= 3 && v <= 14).toList()..sort();
  final segs = _findConsecutiveSegments(cardVals);
  for (final seg in segs) {
    if (seg.length < 5) continue;
    for (var length = 5; length <= seg.length; length++) {
      for (var i = 0; i <= seg.length - length; i++) {
        final sub = seg.sublist(i, i + length);
        yield sub.map((v) => byValue[v]!.first).toList();
      }
    }
  }
}

Iterable<List<Card>> _generateStraightPairs(Map<int, List<Card>> byValue) sync* {
  final vals = byValue.keys
      .where((v) => byValue[v]!.length >= 2 && v >= 3 && v <= 14)
      .toList()
    ..sort();
  final segs = _findConsecutiveSegments(vals);
  for (final seg in segs) {
    if (seg.length < 2) continue;
    for (var length = 2; length <= seg.length; length++) {
      for (var i = 0; i <= seg.length - length; i++) {
        final sub = seg.sublist(i, i + length);
        final combo = <Card>[];
        for (final v in sub) {
          combo.addAll(byValue[v]!.take(2));
        }
        yield combo;
      }
    }
  }
}

Iterable<List<Card>> _generateStraightTriples(
  Map<int, List<Card>> byValue,
) sync* {
  final vals = byValue.keys
      .where((v) => byValue[v]!.length >= 3 && v >= 3 && v <= 14)
      .toList()
    ..sort();
  final segs = _findConsecutiveSegments(vals);
  for (final seg in segs) {
    if (seg.length < 2) continue;
    for (var length = 2; length <= seg.length; length++) {
      for (var i = 0; i <= seg.length - length; i++) {
        final sub = seg.sublist(i, i + length);
        final combo = List<Card>.from([]);
        for (final v in sub) {
          combo.addAll(byValue[v]!.take(3));
        }
        yield combo;
      }
    }
  }
}

/// 简单三带二：AAA + BB
Iterable<List<Card>> _generateTriplePairs(
  Map<int, List<Card>> byValue,
  List<int> valuesSorted,
) sync* {
  final triplesVals = valuesSorted.where((v) => byValue[v]!.length >= 3).toList();
  final pairsVals = valuesSorted.where((v) => byValue[v]!.length >= 2).toList();
  for (final tv in triplesVals) {
    for (final pv in pairsVals) {
      if (pv == tv) continue;
      yield [...byValue[tv]!.take(3), ...byValue[pv]!.take(2)];
    }
  }
}

/// 简单飞机：若干连续三张 + 若干对子（数量与三张组数相同）
Iterable<List<Card>> _generateFlights(
  Map<int, List<Card>> byValue,
  List<int> valuesSorted,
) sync* {
  final tripleVals = byValue.keys
      .where((v) => byValue[v]!.length >= 3 && v >= 3 && v <= 14)
      .toList()
    ..sort();
  final segs = _findConsecutiveSegments(tripleVals);
  final pairVals = valuesSorted.where((v) => byValue[v]!.length >= 2).toList();
  for (final seg in segs) {
    if (seg.length < 2) continue;
    for (var length = 2; length <= seg.length; length++) {
      for (var i = 0; i <= seg.length - length; i++) {
        final body = seg.sublist(i, i + length);
        final needPairs = length;
        final candidatePairVals = pairVals.where((v) => !body.contains(v)).toList();
        if (candidatePairVals.length < needPairs) continue;
        final usedPairs = candidatePairVals.take(needPairs).toList();
        final combo = <Card>[];
        for (final v in body) {
          combo.addAll(byValue[v]!.take(3));
        }
        for (final v in usedPairs) {
          combo.addAll(byValue[v]!.take(2));
        }
        yield combo;
      }
    }
  }
}

Iterable<List<Card>> _generateBombs(
  Map<int, List<Card>> byValue,
  List<int> valuesSorted,
) sync* {
  for (final v in valuesSorted) {
    if (byValue[v]!.length >= 4) yield byValue[v]!.take(4).toList();
  }
}

/// 根据当前手牌和场面，选一手「尽量小但可出」的牌。
///
/// 策略（按优先级从低到高依次尝试）：
/// 单张、对子、三张、顺子、连对、连三张、三带二、飞机、炸弹。
/// 若无可出牌则返回 null。
List<Card>? autoSelectCards(FieldInfo info) {
  final hand = List<Card>.from(info.clientCards);
  if (hand.isEmpty) return null;

  final byValue = _groupByValue(hand);
  final valuesSorted = byValue.keys.toList()..sort();

  final lastPlayed = info.lastPlayer != info.clientId
      ? info.usersPlayedCards[info.lastPlayer]
      : null;

  final generators = <Iterable<List<Card>> Function()>[
    () => _generateSingles(byValue, valuesSorted),
    () => _generatePairs(byValue, valuesSorted),
    () => _generateTriples(byValue, valuesSorted),
    () => _generateStraights(byValue),
    () => _generateStraightPairs(byValue),
    () => _generateStraightTriples(byValue),
    () => _generateTriplePairs(byValue, valuesSorted),
    () => _generateFlights(byValue, valuesSorted),
    () => _generateBombs(byValue, valuesSorted),
  ];

  for (final gen in generators) {
    for (final combo in gen()) {
      if (validateUserSelectedCards(
        combo,
        info.clientCards,
        (lastPlayed == null || lastPlayed.isEmpty) ? null : lastPlayed,
      )) {
        return combo;
      }
    }
  }
  return null;
}
