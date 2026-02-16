import 'package:flutter_test/flutter_test.dart';
import 'package:liujiatong/core/models/card.dart';
import 'package:liujiatong/data/network/protocol.dart';

void main() {
  group('protocol', () {
    test('encode/decode bool', () {
      expect(decodeMessage(encodeMessage(true)), true);
      expect(decodeMessage(encodeMessage(false)), false);
    });

    test('encode/decode int', () {
      expect(decodeMessage(encodeMessage(42)), 42);
    });

    test('encode/decode string', () {
      expect(decodeMessage(encodeMessage('hello')), 'hello');
    });

    test('encode/decode null', () {
      expect(decodeMessage(encodeMessage(null)), null);
    });

    test('encode/decode Card', () {
      final card = Card(Suits.spade, 14);
      final bytes = encodeMessage(card);
      final decoded = decodeMessage(bytes);
      expect(decoded, isA<Card>());
      expect((decoded as Card).suit, Suits.spade);
      expect(decoded.value, 14);
    });

    test('encode/decode List<Card>', () {
      final cards = [
        Card(Suits.spade, 14),
        Card(Suits.heart, 15),
      ];
      final decoded = decodeMessage(encodeMessage(cards)) as List;
      expect(decoded.length, 2);
      expect(decoded[0], isA<Card>());
      expect((decoded[0] as Card).value, 14);
    });

    test('encode/decode 跳过 ["F"]', () {
      final skip = ['F'];
      final decoded = decodeMessage(encodeMessage(skip));
      expect(decoded, ['F']);
    });

    test('List of Cards 与 ["F"] 区分', () {
      final cards = [Card(Suits.spade, 14)];
      final decoded = decodeMessage(encodeMessage(cards));
      expect(decoded, isA<List>());
      expect(decoded[0], isA<Card>());
      expect(decoded, isNot(equals(['F'])));
    });
  });
}
