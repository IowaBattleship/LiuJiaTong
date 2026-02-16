import 'package:flutter_test/flutter_test.dart';
import 'package:liujiatong/application/game_controller.dart';
import 'package:liujiatong/core/models/card.dart';
import 'package:liujiatong/core/models/config.dart';

void main() {
  group('GameController', () {
    test('初始状态', () {
      final config = Config(ip: '127.0.0.1', port: 8888, name: 'Test');
      final ctrl = GameController(config: config);
      expect(ctrl.clientPlayer, 0);
      expect(ctrl.clientCards, isEmpty);
      expect(ctrl.usersName.length, 6);
      expect(ctrl.gameOver, 0);
      expect(ctrl.isConnected, false);
    });

    test('getFieldInfo 返回正确结构', () {
      final config = Config(ip: 'a', port: 1, name: 'n');
      final ctrl = GameController(config: config);
      ctrl.clientCards = [Card(Suits.spade, 14)];
      ctrl.usersName = List.filled(6, '');
      ctrl.usersName[0] = 'Alice';
      ctrl.usersPlayedCards[1] = [Card(Suits.heart, 5)];
      ctrl.nowPlayer = 1;
      final info = ctrl.getFieldInfo();
      expect(info.clientCards.length, 1);
      expect(info.clientCards.first.value, 14);
      expect(info.userNames[0], 'Alice');
    });

    test('removeCards 从手牌中移除', () {
      final config = Config(ip: 'a', port: 1, name: 'n');
      final ctrl = GameController(config: config);
      final c1 = Card(Suits.spade, 5);
      final c2 = Card(Suits.heart, 5);
      ctrl.clientCards = [c1, c2, Card(Suits.club, 10)];
      ctrl.removeCards([c1]);
      expect(ctrl.clientCards.length, 2);
      expect(ctrl.clientCards.contains(c1), false);
      expect(ctrl.clientCards.contains(c2), true);
    });

    test('getLastPlayer 逆序找非空出牌', () {
      final config = Config(ip: 'a', port: 1, name: 'n');
      final ctrl = GameController(config: config);
      ctrl.usersPlayedCards = List.generate(6, (_) => []);
      ctrl.usersPlayedCards[3] = [Card(Suits.spade, 5)];
      ctrl.nowPlayer = 0;
      expect(ctrl.getLastPlayer(), 3);
    });

    test('startPlayingHeartbeat / stopPlayingHeartbeat 不抛错', () {
      final config = Config(ip: 'a', port: 1, name: 'n');
      final ctrl = GameController(config: config);
      ctrl.startPlayingHeartbeat();
      ctrl.stopPlayingHeartbeat();
      ctrl.startPlayingHeartbeat(interval: Duration(milliseconds: 100));
      ctrl.stopPlayingHeartbeat();
    });
  });
}
