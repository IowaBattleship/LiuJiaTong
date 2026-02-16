import 'package:flutter_test/flutter_test.dart';
import 'package:liujiatong/core/models/card.dart';
import 'package:liujiatong/core/rules/playing_rules.dart';

void main() {
  group('playing_rules', () {
    test('单张合法', () {
      final r = judgeAndTransformCards([14]);
      expect(r.type, CardType.single);
      expect(r.keyCard, 14);
    });

    test('对子合法', () {
      final r = judgeAndTransformCards([14, 14]);
      expect(r.type, CardType.pair);
      expect(r.keyCard, 14);
    });

    test('三张合法', () {
      final r = judgeAndTransformCards([10, 10, 10]);
      expect(r.type, CardType.triple);
      expect(r.keyCard, 10);
    });

    test('非法牌型', () {
      final r = judgeAndTransformCards([3, 5, 7]);
      expect(r.type, CardType.illegalType);
    });

    test('firstInputLegal', () {
      expect(firstInputLegal([14]), true);
      expect(firstInputLegal([3, 5, 7]), false);
    });

    test('validateUserInput 首出单张', () {
      final hand = [Card(Suits.spade, 14)];
      final r = validateUserInput([14], hand, null);
      expect(r.legal, true);
      expect(r.score, 0);
    });

    test('validateUserInput 跳过', () {
      final r = validateUserInput([0], [], [Card(Suits.spade, 5)]);
      expect(r.legal, true);
      final r2 = validateUserInput([0], [], null);
      expect(r2.legal, false);
    });

    test('validateUserSelectedCards', () {
      final selected = [Card(Suits.spade, 14), Card(Suits.heart, 14)];
      final hand = [Card(Suits.spade, 14), Card(Suits.heart, 14), Card(Suits.club, 5)];
      expect(validateUserSelectedCards(selected, hand, null), true);
    });

    test('顺子 5 张合法', () {
      final cards = [11, 10, 9, 8, 7]; // J-10-9-8-7
      cards.sort((a, b) => b.compareTo(a));
      final r = judgeAndTransformCards(cards);
      expect(r.type, CardType.straight);
      expect(r.keyCard, 11);
    });

    test('普通炸弹 4 张', () {
      final r = judgeAndTransformCards([14, 14, 14, 14]);
      expect(r.type, CardType.normalBomb);
      expect(r.keyCard, 14);
    });

    test('ifEnoughCard 手牌不足返回 false', () {
      final hand = [Card(Suits.spade, 14)];
      final result = ifEnoughCard([14, 14], hand);
      expect(result.enough, false);
      expect(result.score, 0);
    });

    test('validateUserInput 返回正确分数', () {
      final hand = [
        Card(Suits.spade, 5),
        Card(Suits.heart, 5),
        Card(Suits.club, 10),
      ];
      final r = validateUserInput([5, 10], hand, null);
      expect(r.legal, false); // 两张不构成合法牌型
      final r2 = validateUserInput([5], hand, null);
      expect(r2.legal, true);
      expect(r2.score, 5);
    });
  });
}
