import 'package:liujiatong/core/models/card.dart';

/// 牌局场面信息 DTO（与 client 使用的场面信息一致）
class FieldInfo {
  FieldInfo({
    required this.startFlag,
    required this.isPlayer,
    required this.clientId,
    required this.clientCards,
    required this.userNames,
    required this.userScores,
    required this.usersCardsNum,
    required this.usersCards,
    required this.usersPlayedCards,
    required this.headMaster,
    required this.nowScore,
    required this.nowPlayer,
    required this.lastPlayer,
    required this.hisNowScore,
    required this.hisLastPlayer,
  });

  final bool startFlag;
  final bool isPlayer;
  final int clientId;
  final List<Card> clientCards;
  final List<String> userNames;
  final List<int> userScores;
  final List<int> usersCardsNum;
  final List<List<Card>> usersCards;
  final List<List<Card>> usersPlayedCards;
  final int headMaster;
  final int nowScore;
  final int nowPlayer;
  final int lastPlayer;
  final int hisNowScore;
  final int? hisLastPlayer;
}
