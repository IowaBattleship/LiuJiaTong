import 'package:flutter_test/flutter_test.dart';
import 'package:liujiatong/core/models/card.dart';

void main() {
  group('Card', () {
    test('构造与 equality', () {
      final c1 = Card(Suits.spade, 14);
      final c2 = Card(Suits.spade, 14);
      final c3 = Card(Suits.heart, 14);
      expect(c1 == c2, true);
      expect(c1 == c3, false);
      expect(c1 == 14, true);
    });

    test('fromJson / toJson 往返', () {
      final json = {'suit': 'Spade', 'value': 14};
      final card = Card.fromJson(json);
      expect(card.suit, Suits.spade);
      expect(card.value, 14);
      expect(card.toJson(), json);
    });

    test('大小王 suit 为空', () {
      final json = {'suit': '', 'value': 16};
      final card = Card.fromJson(json);
      expect(card.suit, Suits.empty);
      expect(card.value, 16);
      expect(card.toJson()['suit'], '');
    });

    test('displayStr 与 Python 一致', () {
      expect(Card(Suits.spade, 10).displayStr, 'B');
      expect(Card(Suits.heart, 11).displayStr, 'J');
      expect(Card(Suits.club, 12).displayStr, 'Q');
      expect(Card(Suits.diamond, 13).displayStr, 'K');
      expect(Card(Suits.spade, 14).displayStr, 'A');
      expect(Card(Suits.heart, 15).displayStr, '2');
      expect(Card(Suits.empty, 16).displayStr, '0');
      expect(Card(Suits.empty, 17).displayStr, '1');
      expect(Card(Suits.spade, 5).displayStr, '5');
    });

    test('compareTo 排序', () {
      final cards = [
        Card(Suits.spade, 14),
        Card(Suits.heart, 3),
        Card(Suits.club, 11),
      ];
      cards.sort();
      expect(cards.map((c) => c.value).toList(), [3, 11, 14]);
    });
  });
}
