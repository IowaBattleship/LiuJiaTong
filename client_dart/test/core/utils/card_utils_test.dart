import 'package:flutter_test/flutter_test.dart';
import 'package:liujiatong/core/models/card.dart';
import 'package:liujiatong/core/utils/card_utils.dart';

void main() {
  group('card_utils', () {
    test('strToInt / intToStr 往返', () {
      expect(strToInt('5'), 5);
      expect(strToInt('B'), 10);
      expect(strToInt('J'), 11);
      expect(strToInt('A'), 14);
      expect(strToInt('2'), 15);
      expect(strToInt('0'), 16);
      expect(strToInt('1'), 17);
      expect(strToInt('F'), 0);
      expect(intToStr(10), 'B');
      expect(intToStr(0), 'F');
    });

    test('calculateScore', () {
      final cards = [
        Card(Suits.spade, 5),
        Card(Suits.heart, 10),
        Card(Suits.club, 13),
      ];
      expect(calculateScore(cards), 5 + 10 + 10);
    });

    test('getCardCount', () {
      final hand = [
        Card(Suits.spade, 5),
        Card(Suits.heart, 5),
        Card(Suits.club, 11),
      ];
      expect(getCardCount(hand, '5'), 2);
      expect(getCardCount(hand, 'J'), 1);
    });

    test('lastPlayed', () {
      final played = [
        <Card>[],
        [Card(Suits.spade, 5)],
        <Card>[],
        <Card>[],
        <Card>[],
        <Card>[],
      ];
      expect(lastPlayed(played, 2), 1);
      expect(lastPlayed(played, 0), 1);
    });

    test('headMasterInTeam', () {
      expect(headMasterInTeam(0, 0), true);
      expect(headMasterInTeam(0, 2), true);
      expect(headMasterInTeam(0, 1), false);
    });

    test('drawCards', () {
      final cards = [
        Card(Suits.heart, 5),
        Card(Suits.spade, 11),
        Card(Suits.club, 5),
      ];
      cards.sort((a, b) => a.compareTo(b));
      final drawn = drawCards(cards, ['5', 'J']);
      expect(drawn.length, 2);
      expect(drawn[0].value, 5);
      expect(drawn[1].value, 11);
    });

    test('calculateTeamScores 头科在我方', () {
      final usersCardsNum = List.filled(6, 0);
      final usersScores = [10, 20, 30, 40, 50, 60]; // 0,2,4 一队
      final scores = calculateTeamScores(0, 0, usersCardsNum, usersScores);
      expect(scores[0], 10 + 30 + 50);
      expect(scores[1], 20 + 40 + 60);
    });
  });
}
