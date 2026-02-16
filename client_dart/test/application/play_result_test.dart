import 'package:flutter_test/flutter_test.dart';
import 'package:liujiatong/application/play_result.dart';
import 'package:liujiatong/core/models/card.dart';

void main() {
  group('PlayResult', () {
    test('PlayCards', () {
      final cards = [Card(Suits.spade, 14), Card(Suits.heart, 14)];
      final r = PlayCards(cards, 0);
      expect(r.cards.length, 2);
      expect(r.score, 0);
    });

    test('PlaySkip', () {
      final r = PlaySkip();
      expect(r, isA<PlaySkip>());
    });
  });
}
