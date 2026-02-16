import 'dart:async';

import 'package:liujiatong/application/play_result.dart';
import 'package:liujiatong/core/auto_play/strategy.dart';
import 'package:liujiatong/core/models/card.dart';
import 'package:liujiatong/core/models/config.dart';
import 'package:liujiatong/core/models/field_info.dart';
import 'package:liujiatong/core/utils/card_utils.dart';
import 'package:liujiatong/data/network/socket_client.dart' as net;

/// 游戏控制器：连接、收发、状态更新
///
/// 对应 Python client.Client，使用 Future 驱动（非阻塞）。
class GameController {
  GameController({
    required this.config,
    this.noCookie = false,
  });

  final Config config;
  final bool noCookie;

  net.ProtocolSocket? _socket;
  Timer? _heartbeatTimer;

  // --- 游戏状态 ---
  int clientPlayer = 0;
  List<Card> clientCards = [];
  List<List<Card>> usersCards = List.generate(6, (_) => []);
  bool isPlayer = false;
  List<String> usersName = List.filled(6, '');
  int gameOver = 0;
  int nowScore = 0;
  int nowPlayer = 0;
  List<int> usersCardsNum = List.filled(6, 0);
  List<int> usersScore = List.filled(6, 0);
  List<List<Object>> usersPlayedCards = List.generate(6, (_) => []);
  int headMaster = -1;
  int hisNowScore = 0;
  int? hisLastPlayer;
  bool isStart = false;

  Config get currentConfig => config;

  bool get isConnected => _socket != null && !_socket!.isClosed;

  /// 连接服务器
  Future<void> connect(String host, int port) async {
    await close();
    _socket = await net.connect(host, port);
  }

  /// 连接服务器，失败时重试
  Future<void> connectWithRetry(
    String host,
    int port, {
    int maxRetries = 10,
    Duration retryDelay = const Duration(seconds: 1),
  }) async {
    await close();
    Exception? lastError;
    for (var i = 0; i < maxRetries; i++) {
      try {
        _socket = await net.connect(host, port);
        return;
      } catch (e) {
        lastError = e is Exception ? e : Exception(e.toString());
        if (i < maxRetries - 1) {
          await Future<void>.delayed(retryDelay);
        }
      }
    }
    throw lastError ?? Exception('连接失败');
  }

  /// 关闭连接
  Future<void> close() async {
    stopPlayingHeartbeat();
    _socket?.close();
    _socket = null;
  }

  /// 开始出牌心跳（轮到自己出牌等待输入时调用，约每 1 秒发送一次 finished=false）
  void startPlayingHeartbeat({Duration interval = const Duration(seconds: 1)}) {
    stopPlayingHeartbeat();
    _heartbeatTimer = Timer.periodic(interval, (_) async {
      try {
        await sendPlayingHeartbeat(false);
      } catch (_) {}
    });
  }

  /// 停止出牌心跳
  void stopPlayingHeartbeat() {
    _heartbeatTimer?.cancel();
    _heartbeatTimer = null;
  }

  /// 发送登录/用户信息，接收 cookie 合法性等
  /// 返回更新后的 Config（若 cookie 不合法会收到新 cookie 并更新）
  Future<Config> sendUserInfo() async {
    final sock = _requireSocket();

    if (noCookie) {
      await sock.send(false);
    } else if (config.cookie != null) {
      await sock.send(true);
      await sock.send(config.cookie!);
    } else {
      await sock.send(false);
    }

    final ifValidCookie = await sock.recv() as bool;
    if (ifValidCookie) {
      final ifRecovery = await sock.recv() as bool;
      if (!ifRecovery) {
        throw Exception('恢复失败，是否有客户端还在运行？');
      }
      return config;
    }

    await sock.send(config.name);
    final newCookie = await sock.recv();
    return config.copyWith(cookie: newCookie as String?);
  }

  /// 接收等待大厅信息，循环直到 6 人满员
  /// onUpdate: (usersName, usersError) 每次收到时回调
  Future<void> recvWaitingHallInfo(
    void Function(List<String> usersName, List<bool> usersError) onUpdate,
  ) async {
    final sock = _requireSocket();
    while (true) {
      final usersNameRaw = await sock.recv() as List;
      final usersErrorRaw = await sock.recv() as List;
      final names = usersNameRaw.map((e) => e.toString()).toList();
      final errors = usersErrorRaw.map((e) => e == true).toList();
      onUpdate(names, errors);
      if (names.length >= 6) {
        usersName = List.filled(6, '');
        for (var i = 0; i < names.length && i < 6; i++) {
          usersName[i] = names[i];
        }
        break;
      }
    }
  }

  /// 接收场上信息（开局时）
  Future<void> recvFieldInfo() async {
    final sock = _requireSocket();
    isPlayer = await sock.recv() as bool;
    final names = await sock.recv() as List;
    clientPlayer = await sock.recv() as int;
    usersName = List.filled(6, '');
    for (var i = 0; i < names.length && i < 6; i++) {
      usersName[i] = names[i].toString();
    }
  }

  /// 接收牌局信息（每轮），更新内部状态
  Future<void> recvRoundInfo() async {
    final sock = _requireSocket();
    gameOver = await sock.recv() as int;
    usersScore = (await sock.recv() as List).cast<int>();
    if (usersScore.length < 6) usersScore = List.filled(6, 0)..setAll(0, usersScore);
    usersCardsNum = (await sock.recv() as List).cast<int>();
    if (usersCardsNum.length < 6) usersCardsNum = List.filled(6, 0)..setAll(0, usersCardsNum);

    final playedRaw = await sock.recv() as List;
    usersPlayedCards = List.generate(6, (_) => []);
    for (var i = 0; i < playedRaw.length && i < 6; i++) {
      final inner = playedRaw[i] as List;
      if (inner.length == 1 && inner[0] == 'F') {
        usersPlayedCards[i] = ['F'];
      } else {
        usersPlayedCards[i] = inner.cast<Card>();
      }
    }

    if (gameOver != 0) {
      final cardsRaw = await sock.recv() as List;
      usersCards = List.generate(6, (_) => []);
      for (var i = 0; i < cardsRaw.length && i < 6; i++) {
        usersCards[i] = (cardsRaw[i] as List).cast<Card>();
      }
    }

    final myCards = await sock.recv() as List;
    clientCards = myCards.cast<Card>();
    nowScore = await sock.recv() as int;
    nowPlayer = await sock.recv() as int;
    headMaster = await sock.recv() as int;
  }

  /// 发送出牌内容
  Future<void> sendPlayerInfo(
    List<Card> clientCardsAfter,
    List<Object> playedThisRound,
    int nowScoreAfter,
  ) async {
    final sock = _requireSocket();
    await sock.send(clientCardsAfter);
    await sock.send(playedThisRound);
    await sock.send(nowScoreAfter);
  }

  /// 发送出牌心跳
  Future<void> sendPlayingHeartbeat(bool finished) async {
    final sock = _requireSocket();
    await sock.send(finished);
  }

  /// 获取当前场面的 FieldInfo（供 UI 或自动出牌使用）
  FieldInfo getFieldInfo() {
    final lastPlayer = lastPlayed(usersPlayedCards, nowPlayer);
    return FieldInfo(
      startFlag: isStart,
      isPlayer: isPlayer,
      clientId: clientPlayer,
      clientCards: clientCards,
      userNames: usersName,
      userScores: usersScore,
      usersCardsNum: usersCardsNum,
      usersCards: usersCards,
      usersPlayedCards: usersPlayedCards.map((p) {
        if (p.length == 1 && p[0] == 'F') return <Card>[];
        return p.cast<Card>();
      }).toList(),
      headMaster: headMaster,
      nowScore: nowScore,
      nowPlayer: nowPlayer,
      lastPlayer: lastPlayer,
      hisNowScore: hisNowScore,
      hisLastPlayer: hisLastPlayer,
    );
  }

  /// 上一位出牌人
  int getLastPlayer() => lastPlayed(usersPlayedCards, nowPlayer);

  /// 更新历史状态（每轮 UI 展示后调用）
  void updateHistory(int lastPlayer) {
    hisNowScore = nowScore;
    hisLastPlayer = lastPlayer != nowPlayer ? lastPlayer : null;
    isStart = true;
  }

  /// 移除手牌（出牌后本地更新）
  void removeCards(List<Card> cards) {
    for (final card in cards) {
      for (var i = 0; i < clientCards.length; i++) {
        if (clientCards[i] == card) {
          clientCards.removeAt(i);
          break;
        }
      }
    }
  }

  /// 主循环（Future 驱动，非阻塞）
  ///
  /// - [onRound] 每轮收到牌局信息后回调
  /// - [onMyTurn] 轮到自己出牌时回调，返回出牌结果（期间自动发送心跳）
  /// - [onGameOver] 游戏结束时回调
  /// - [useAutoPlay] 为 true 时自动出牌，忽略 onMyTurn
  Future<void> runGameLoop({
    required void Function(FieldInfo info) onRound,
    required Future<PlayResult> Function(FieldInfo info) onMyTurn,
    required void Function(int clientPlayer, int gameOverCode) onGameOver,
    bool useAutoPlay = false,
  }) async {
    while (true) {
      await recvRoundInfo();
      final info = getFieldInfo();
      final lastPlayer = getLastPlayer();
      if (lastPlayer == nowPlayer && lastPlayer != hisLastPlayer) {
        hisLastPlayer = lastPlayer;
      }
      onRound(info);
      updateHistory(lastPlayer);

      if (gameOver != 0) {
        onGameOver(clientPlayer, gameOver);
        return;
      }

      if (isPlayer && clientPlayer == nowPlayer) {
        PlayResult result;
        if (useAutoPlay) {
          final selected = autoSelectCards(info);
          result = selected != null
              ? PlayCards(selected, calculateScore(selected))
              : PlaySkip();
        } else {
          startPlayingHeartbeat();
          try {
            result = await onMyTurn(info);
          } finally {
            stopPlayingHeartbeat();
          }
        }
        await sendPlayingHeartbeat(true);

        late List<Object> played;
        late int newScore;
        switch (result) {
          case PlayCards(:final cards, :final score):
            played = List<Object>.from(cards);
            played.sort((a, b) => (a as Card).compareTo(b as Card));
            usersPlayedCards[clientPlayer] = played;
            removeCards(cards);
            newScore = nowScore + score;
            nowScore = newScore;
          case PlaySkip():
            played = ['F'];
            usersPlayedCards[clientPlayer] = played;
            newScore = nowScore;
        }
        await sendPlayerInfo(
          List<Card>.from(clientCards),
          played,
          newScore,
        );
      }
    }
  }

  net.ProtocolSocket _requireSocket() {
    final s = _socket;
    if (s == null || s.isClosed) {
      throw StateError('未连接或连接已关闭');
    }
    return s;
  }
}
