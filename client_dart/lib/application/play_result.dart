import 'package:liujiatong/core/models/card.dart';

/// 出牌结果（供主循环回调返回）
sealed class PlayResult {}

/// 出牌
class PlayCards extends PlayResult {
  PlayCards(this.cards, this.score);
  final List<Card> cards;
  final int score;
}

/// 跳过
class PlaySkip extends PlayResult {
  PlaySkip();
}
