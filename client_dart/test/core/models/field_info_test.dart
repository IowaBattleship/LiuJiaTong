import 'package:flutter_test/flutter_test.dart';
import 'package:liujiatong/core/models/card.dart';
import 'package:liujiatong/core/models/field_info.dart';

void main() {
  test('FieldInfo 构造与字段', () {
    final info = FieldInfo(
      startFlag: true,
      isPlayer: true,
      clientId: 0,
      clientCards: [Card(Suits.spade, 5)],
      userNames: List.filled(6, ''),
      userScores: List.filled(6, 0),
      usersCardsNum: List.filled(6, 0),
      usersCards: List.generate(6, (_) => []),
      usersPlayedCards: List.generate(6, (_) => []),
      headMaster: -1,
      nowScore: 0,
      nowPlayer: 0,
      lastPlayer: 0,
      hisNowScore: 0,
      hisLastPlayer: null,
    );
    expect(info.startFlag, true);
    expect(info.clientCards.length, 1);
    expect(info.userNames.length, 6);
  });
}
