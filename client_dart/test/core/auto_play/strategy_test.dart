import 'package:flutter_test/flutter_test.dart';
import 'package:liujiatong/core/auto_play/strategy.dart';
import 'package:liujiatong/core/models/card.dart';
import 'package:liujiatong/core/models/field_info.dart';

FieldInfo _minimalInfo({
  required List<Card> clientCards,
  int clientId = 0,
  int lastPlayer = 0,
  List<Card>? lastPlayedCards,
}) {
  final played = List.generate(6, (_) => <Card>[]);
  if (lastPlayedCards != null && lastPlayer < 6) {
    played[lastPlayer] = lastPlayedCards;
  }
  return FieldInfo(
    startFlag: true,
    isPlayer: true,
    clientId: clientId,
    clientCards: clientCards,
    userNames: List.filled(6, ''),
    userScores: List.filled(6, 0),
    usersCardsNum: List.filled(6, 0),
    usersCards: List.generate(6, (_) => []),
    usersPlayedCards: played,
    headMaster: -1,
    nowScore: 0,
    nowPlayer: clientId,
    lastPlayer: lastPlayer,
    hisNowScore: 0,
    hisLastPlayer: null,
  );
}

void main() {
  group('autoSelectCards', () {
    test('手牌为空返回 null', () {
      final info = _minimalInfo(clientCards: []);
      expect(autoSelectCards(info), isNull);
    });

    test('首出选最小单张', () {
      final hand = [
        Card(Suits.spade, 14),
        Card(Suits.heart, 3),
        Card(Suits.club, 5),
      ];
      final info = _minimalInfo(clientCards: hand);
      final out = autoSelectCards(info);
      expect(out, isNotNull);
      expect(out!.length, 1);
      expect(out.first.value, 3);
    });

    test('首出优先出最小单张（策略先尝试单张）', () {
      final hand = [
        Card(Suits.spade, 5),
        Card(Suits.heart, 5),
        Card(Suits.club, 3),
      ];
      final info = _minimalInfo(clientCards: hand);
      final out = autoSelectCards(info);
      expect(out, isNotNull);
      expect(out!.length, 1);
      expect(out.first.value, 3);
    });

    test('跟牌：上家出单张 A，选最小能压过的单张', () {
      final hand = [
        Card(Suits.spade, 14), // A
        Card(Suits.heart, 15), // 2
      ];
      final lastPlayed = [Card(Suits.club, 14)];
      final info = _minimalInfo(
        clientCards: hand,
        lastPlayer: 1,
        lastPlayedCards: lastPlayed,
      );
      final out = autoSelectCards(info);
      expect(out, isNotNull);
      expect(out!.length, 1);
      expect(out.first.value, 15);
    });

    test('跟牌：无牌可出时返回 null', () {
      final hand = [Card(Suits.spade, 3)];
      final lastPlayed = [Card(Suits.heart, 15)]; // 2
      final info = _minimalInfo(
        clientCards: hand,
        lastPlayer: 1,
        lastPlayedCards: lastPlayed,
      );
      final out = autoSelectCards(info);
      expect(out, isNull);
    });

    test('首出仅有两张相同牌时策略先出单张', () {
      final hand = [
        Card(Suits.spade, 7),
        Card(Suits.heart, 7),
      ];
      final info = _minimalInfo(clientCards: hand);
      final out = autoSelectCards(info);
      expect(out, isNotNull);
      expect(out!.length, 1);
      expect(out.first.value, 7);
    });
  });
}
