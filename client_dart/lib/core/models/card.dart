/// 扑克牌花色
enum Suits {
  spade('Spade'),   // 黑桃
  heart('Heart'),   // 红心
  club('Club'),     // 梅花
  diamond('Diamond'), // 方块
  empty('');        // 空，大小王没有花色

  const Suits(this.value);
  final String value;

  static Suits fromString(String s) {
    return Suits.values.firstWhere(
      (e) => e.value == s,
      orElse: () => Suits.empty,
    );
  }
}

/// 扑克牌模型
///
/// 牌面 value: 3~10 数字牌, 11 J, 12 Q, 13 K, 14 A, 15 2, 16 小王, 17 大王
class Card implements Comparable<Card> {
  Card(this.suit, this.value);

  final Suits suit;
  final int value;

  /// 从 JSON 反序列化（与 protocol.md 一致）
  factory Card.fromJson(Map<String, dynamic> json) {
    return Card(
      Suits.fromString(json['suit'] as String? ?? ''),
      json['value'] as int,
    );
  }

  /// 序列化为 JSON（与 protocol.md 一致）
  Map<String, dynamic> toJson() => {'suit': suit.value, 'value': value};

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    if (other is Card) return value == other.value && suit == other.suit;
    if (other is int) return value == other;
    return false;
  }

  @override
  int get hashCode => Object.hash(suit, value);

  @override
  int compareTo(Card other) => value.compareTo(other.value);

  @override
  String toString() => '${suit.value}_$displayStr';

  /// CLI 显示用：3~9 数字，10->B, 11->J, 12->Q, 13->K, 14->A, 15->2, 16->0(小王), 17->1(大王)
  String get displayStr {
    switch (value) {
      case 10:
        return 'B';
      case 11:
        return 'J';
      case 12:
        return 'Q';
      case 13:
        return 'K';
      case 14:
        return 'A';
      case 15:
        return '2';
      case 16:
        return '0';
      case 17:
        return '1';
      default:
        return value.toString();
    }
  }
}
