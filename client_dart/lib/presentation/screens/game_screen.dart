import 'dart:async';

import 'package:flutter/material.dart';
import 'package:liujiatong/application/play_result.dart';
import 'package:liujiatong/core/auto_play/strategy.dart';
import 'package:liujiatong/core/models/card.dart' as card_model;
import 'package:liujiatong/core/models/field_info.dart';
import 'package:liujiatong/core/rules/playing_rules.dart' as rules;
import 'package:liujiatong/core/utils/card_utils.dart'
    show backgroundImageAssetPath, calculateScore, calculateTeamScores, cardImageAssetPath;
import 'package:liujiatong/application/game_controller.dart';
import 'package:liujiatong/data/sound/sound_service.dart';

// 与 gui_flet 一致的玩家位置偏移：上1、右上下2、左上下2、下自己
const int _posTop = 3, _posSe = 1, _posNe = 2, _posNw = 4, _posSw = 5;

/// 布局参数（随窗口尺寸缩放，与 gui_flet LayoutParams 对应）
class _GameLayoutParams {
  _GameLayoutParams(double width, double height)
      : _h = height,
        scaleX = width / 1440,
        scaleY = height / 810,
        scale = ((width / 1440) < (height / 810) ? (width / 1440) : (height / 810)).clamp(0.5, 1.5),
        verticalMargin = 20 * (height / 810),
        cardWidth = 71 * (((width / 1440) < (height / 810) ? (width / 1440) : (height / 810)).clamp(0.5, 1.5)),
        cardHeight = 100 * (((width / 1440) < (height / 810) ? (width / 1440) : (height / 810)).clamp(0.5, 1.5)),
        cardSpacing = 20 * (((width / 1440) < (height / 810) ? (width / 1440) : (height / 810)).clamp(0.5, 1.5)),
        playedCardSpacing = 30 * (((width / 1440) < (height / 810) ? (width / 1440) : (height / 810)).clamp(0.5, 1.5)),
        horizontalCardMargin = 160 * (width / 1440),
        infoSectionWidth = 155 * (((width / 1440) < (height / 810) ? (width / 1440) : (height / 810)).clamp(0.5, 1.5)),
        infoSectionHeight = 68 * (((width / 1440) < (height / 810) ? (width / 1440) : (height / 810)).clamp(0.5, 1.5)),
        bottomMargin = 20 * (height / 810);

  final double _h;
  final double scaleX;
  final double scaleY;
  final double scale;
  final double verticalMargin;
  final double cardWidth;
  final double cardHeight;
  final double cardSpacing;
  final double playedCardSpacing;
  final double horizontalCardMargin;
  final double infoSectionWidth;
  final double infoSectionHeight;
  final double bottomMargin;

  double get bottomCardY => _h - bottomMargin - cardHeight;
  double get topCardY => verticalMargin;
  // 自己已出牌行：位于自己手牌之上，留出比原来更紧凑的间距
  double get myPlayedCardsY => bottomCardY - cardHeight - 20 * scaleY;
  // 顶部已出牌行：紧贴在顶部手牌之下，而不是与左右上玩家同一行
  double get topPlayedCardsY => topCardY + cardHeight + 20 * scaleY;
  double get horizontalInfoMargin => 20 * scaleX;
  double get horizontalCardMarginSide => horizontalInfoMargin + infoSectionWidth + 20 * scaleX;
  double get horizontalInfoSectionMargin => 180 * scaleX;
  double get topCenter => topCardY + cardHeight / 2;
  double get bottomCenter => bottomCardY + cardHeight / 2;
  double get bandGap => (bottomCenter - topCenter - cardHeight * 3) / 3;
  double get upperCardY => topCardY + bandGap + cardHeight;
  double get lowerCardY => upperCardY + bandGap + cardHeight;
  double get infoSectionOffset => cardHeight / 2 - infoSectionHeight / 2;
  double get upperInfoSectionY => upperCardY + infoSectionOffset;
  double get lowerInfoSectionY => lowerCardY + infoSectionOffset;
  double get bottomInfoSectionY => _h - bottomMargin - infoSectionHeight - infoSectionOffset;
  double get topInfoSectionY => topCardY + infoSectionOffset;
  double get buttonRightMargin => 30 * scaleX;
  double get buttonBottomMargin => 40 * scaleY;
  double get buttonSpacing => 55 * scaleY;
  double get scoreAnchorX => 50 * scaleX;
  double get fontSize => (20 * scale).clamp(12, 28);
  double get avatarSize => 36 * scale;
}

int _centeredRowStart(_GameLayoutParams layout, int cardCount, double width) {
  final total = layout.cardWidth + layout.cardSpacing * (cardCount > 0 ? cardCount - 1 : 0);
  return ((width - total) / 2).round();
}

String _truncateName(String name, int maxLen) {
  if (name.length <= maxLen) return name;
  return '${name.substring(0, maxLen - 1)}…';
}

/// 牌局主界面：环形布局（上1/左2/右2/下自己），参考 gui_flet
class GameScreen extends StatefulWidget {
  const GameScreen({
    super.key,
    required this.controller,
    required this.onExit,
  });

  final GameController controller;
  final VoidCallback onExit;

  @override
  State<GameScreen> createState() => _GameScreenState();
}

class _GameScreenState extends State<GameScreen> {
  FieldInfo? _info;
  final List<bool> _selected = [];
  bool _autoPlayEnabled = false;
  Completer<PlayResult>? _turnCompleter;
  _GameOverResult? _gameOver;

  /// 是否轮到我出牌（含首出：不依赖 startFlag，首出时也可选牌）
  bool get _isMyTurn =>
      _info != null &&
      _info!.isPlayer &&
      _info!.nowPlayer == _info!.clientId &&
      _info!.clientCards.isNotEmpty;

  /// 是否可以点跳过（首出时不能跳过）
  bool get _canSkip {
    if (_info == null || !_isMyTurn) return false;
    final last = _info!.lastPlayer;
    if (last < 0 || last >= _info!.usersPlayedCards.length) return false;
    return _info!.usersPlayedCards[last].isNotEmpty;
  }

  @override
  void initState() {
    super.initState();
    _runLoop();
  }

  Future<void> _runLoop() async {
    try {
      await widget.controller.runGameLoop(
        onRound: (info) {
          _playRoundSound(info);
          if (!mounted) return;
          setState(() {
            _info = info;
            if (_selected.length != info.clientCards.length) {
              _selected.clear();
              _selected.addAll(List.filled(info.clientCards.length, false));
            }
          });
        },
        onMyTurn: (info) async {
          if (_autoPlayEnabled) {
            final selected = autoSelectCards(info);
            if (selected != null) {
              return PlayCards(selected, calculateScore(selected));
            }
            return PlaySkip();
          }
          final c = Completer<PlayResult>();
          if (!mounted) return c.future;
          setState(() => _turnCompleter = c);
          return c.future;
        },
        onGameOver: (clientPlayer, gameOverCode) {
          SoundService.instance.play('clap');
          if (!mounted) return;
          setState(() => _gameOver = _GameOverResult(clientPlayer, gameOverCode));
        },
        useAutoPlay: false,
      );
    } catch (_) {
      if (!mounted) return;
      setState(() => _gameOver = _GameOverResult.error());
    }
  }

  void _onCardTap(int index) {
    // 手牌始终允许选中/取消，只要有场面信息和索引合法
    if (_info == null) return;
    if (index < 0 || index >= _selected.length) return;
    setState(() => _selected[index] = !_selected[index]);
  }

  void _onReset() {
    setState(() {
      for (var i = 0; i < _selected.length; i++) _selected[i] = false;
    });
  }

  void _onConfirm() {
    if (_info == null || _turnCompleter == null || _turnCompleter!.isCompleted) return;
    final selected = <card_model.Card>[];
    for (var i = 0; i < _info!.clientCards.length && i < _selected.length; i++) {
      if (_selected[i]) selected.add(_info!.clientCards[i]);
    }
    List<card_model.Card>? lastPlayed;
    if (_info!.lastPlayer != _info!.clientId && _info!.lastPlayer >= 0) {
      lastPlayed = _info!.usersPlayedCards[_info!.lastPlayer];
    }
    if (selected.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('请选牌或点击跳过')),
      );
      return;
    }
    if (!rules.validateUserSelectedCards(selected, _info!.clientCards, lastPlayed)) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('牌型不合法')),
      );
      return;
    }
    _turnCompleter!.complete(PlayCards(selected, calculateScore(selected)));
    setState(() {
      _turnCompleter = null;
      for (var i = 0; i < _selected.length; i++) _selected[i] = false;
    });
  }

  void _onSkip() {
    if (_info == null || _turnCompleter == null || _turnCompleter!.isCompleted) return;
    List<card_model.Card>? lastPlayedSkip;
    if (_info!.lastPlayer != _info!.clientId && _info!.lastPlayer >= 0) {
      lastPlayedSkip = _info!.usersPlayedCards[_info!.lastPlayer];
    }
    if (lastPlayedSkip == null || lastPlayedSkip.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('首出不能跳过')),
      );
      return;
    }
    _turnCompleter!.complete(PlaySkip());
    setState(() {
      _turnCompleter = null;
      for (var i = 0; i < _selected.length; i++) _selected[i] = false;
    });
  }

  void _onToggleAutoPlay() {
    final next = !_autoPlayEnabled;

    // 打开托管时，如果当前正轮到我且有未完成的回合，立刻执行一次自动出牌/跳过
    if (next && _info != null && _isMyTurn && _turnCompleter != null && !_turnCompleter!.isCompleted) {
      final info = _info!;
      final selected = autoSelectCards(info);
      PlayResult result;
      if (selected != null) {
        result = PlayCards(selected, calculateScore(selected));
      } else {
        // 托管逻辑：如果没有可出的牌，则直接跳过（与 Python 客户端一致，由服务端负责规则校验）
        result = PlaySkip();
      }
      _turnCompleter!.complete(result);
      setState(() {
        _autoPlayEnabled = next;
        _turnCompleter = null;
        for (var i = 0; i < _selected.length; i++) _selected[i] = false;
      });
    } else {
      setState(() => _autoPlayEnabled = next);
    }
  }

  void _playRoundSound(FieldInfo info) {
    final sound = SoundService.instance;
    if (!info.startFlag) {
      sound.playMultiple(['start', 'open']);
      return;
    }
    final last = info.lastPlayer;
    final now = info.nowPlayer;
    final hisLast = info.hisLastPlayer;
    final hisScore = info.hisNowScore;
    if (last == now && hisScore > 0) {
      sound.play('fen');
      return;
    }
    if (last == hisLast) {
      sound.play('pass');
      return;
    }
    final played = info.usersPlayedCards[last];
    if (played.isEmpty) return;
    final values = played.map((c) => c.value).toList()..sort((a, b) => b.compareTo(a));
    final r = rules.judgeAndTransformCards(values);
    if (r.type == rules.CardType.illegalType) return;
    final bombs = [
      rules.CardType.redJokerBomb,
      rules.CardType.blackJokerBomb,
      rules.CardType.normalBomb,
    ];
    if (bombs.contains(r.type)) {
      if (played.length >= 7) {
        sound.play('bomb3');
      } else if (played.length >= 5) {
        sound.play('bomb2');
      } else {
        sound.play('bomb1');
      }
    } else {
      if (played.length >= 5) {
        sound.play('throw2');
      } else {
        sound.play('throw1');
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_gameOver != null) {
      return _GameOverOverlay(
        result: _gameOver!,
        onExit: widget.onExit,
      );
    }
    final info = _info;
    if (info == null) {
      return const Scaffold(
        backgroundColor: Color(0xFF0d1820),
        body: Center(child: CircularProgressIndicator(color: Colors.white70)),
      );
    }

    final size = MediaQuery.sizeOf(context);
    final layout = _GameLayoutParams(size.width, size.height);
    const bgColor = Color(0xFF0d1820);
    const textColor = Color(0xFFe8e8e8);

    final padding = MediaQuery.paddingOf(context);

    return Scaffold(
      backgroundColor: bgColor,
      body: Stack(
        fit: StackFit.expand,
        children: [
          // 1. 顶部玩家（1 人）
          Positioned(
            top: 0,
            left: 0,
            right: 0,
            child: _buildTopPlayer(info, layout, size.width, textColor),
          ),
          // 2. 左侧两名玩家（上、下）
          _buildLeftPlayers(info, layout, textColor),
          // 3. 右侧两名玩家（上、下）
          _buildRightPlayers(info, layout, textColor),
          // 4. 顶部玩家本回合已出牌
          _buildPlayedCards(info, layout, size.width),
          // 5. 自己本回合已出牌（中央偏下）
          _buildMyPlayedRow(info, layout, size.width),
          // 6. 底部自己：信息卡 + 手牌
          _buildBottomSelf(info, layout, size.width, textColor),
          // 7. 右上比分面板
          _buildScorePanel(info, layout, size, textColor),
          // 8. 右下按钮（重置/确定/托管/跳过）
          _buildActionButtons(layout),
          // 9. 左上角退出按钮（替代 AppBar）
          Positioned(
            top: padding.top + 8 * layout.scaleY,
            left: 8 * layout.scaleX,
            child: TextButton(
              style: TextButton.styleFrom(
                foregroundColor: textColor,
                padding: EdgeInsets.symmetric(
                  horizontal: 12 * layout.scaleX,
                  vertical: 4 * layout.scaleY,
                ),
                backgroundColor: const Color(0x55000000),
                minimumSize: Size.zero,
                tapTargetSize: MaterialTapTargetSize.shrinkWrap,
              ),
              onPressed: widget.onExit,
              child: const Text('退出'),
            ),
          ),
        ],
      ),
    );
  }

  /// 玩家信息卡内容（仅 Container，不包 Positioned，用于放入 Column 等）
  Widget _buildPlayerInfoCardContent(
    String name,
    int cardsNum,
    int score,
    _GameLayoutParams layout,
    Color textColor,
  ) {
    final displayName = _truncateName(name.isEmpty ? '?' : name, 8);
    final initial = displayName.isNotEmpty ? displayName[0] : '?';
    return Container(
      width: layout.infoSectionWidth,
      height: layout.infoSectionHeight,
      padding: EdgeInsets.all(8 * layout.scale),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(14),
        gradient: const LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [Color(0xFF0f2035), Color(0xFF1e3a52)],
        ),
        border: Border.all(color: const Color(0xFF3d5a80)),
      ),
      child: Row(
        children: [
          Container(
            width: layout.avatarSize,
            height: layout.avatarSize,
            decoration: const BoxDecoration(
              color: Color(0xFF2d4a6f),
              shape: BoxShape.circle,
            ),
            alignment: Alignment.center,
            child: Text(
              initial,
              style: TextStyle(
                color: textColor,
                fontSize: layout.fontSize,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: FittedBox(
              alignment: Alignment.centerLeft,
              fit: BoxFit.scaleDown,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    displayName,
                    style: TextStyle(color: textColor, fontSize: layout.fontSize * 0.9),
                    overflow: TextOverflow.ellipsis,
                  ),
                  Text(
                    '剩${cardsNum}张',
                    style: TextStyle(color: textColor, fontSize: layout.fontSize * 0.8),
                  ),
                ],
              ),
            ),
          ),
          Text(
            '$score',
            style: TextStyle(
              color: const Color(0xFFffd700),
              fontSize: layout.fontSize * 0.9,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }

  /// 带定位的玩家信息卡（仅用于 Stack 内）
  Widget _buildPlayerInfoCard(
    String name,
    int cardsNum,
    int score,
    double x,
    double y,
    _GameLayoutParams layout,
    bool alignLeft,
    Color textColor,
  ) {
    return Positioned(
      left: alignLeft ? x : null,
      right: alignLeft ? null : x,
      top: y,
      child: _buildPlayerInfoCardContent(name, cardsNum, score, layout, textColor),
    );
  }

  Widget _buildTopPlayer(FieldInfo info, _GameLayoutParams layout, double width, Color textColor) {
    final cid = info.clientId;
    final topId = (cid + _posTop) % 6;
    final name = info.userNames[topId];
    final cardsNum = info.usersCardsNum[topId];
    final score = info.userScores[topId];
    // 顶部区域高度：手牌贴顶（topCardY）+ 牌高
    final topSectionHeight = layout.topCardY + layout.cardHeight;
    // info 与手牌中心水平对齐：top = topCardY + (牌高 - info高) / 2
    final topInfoY = layout.topCardY + (layout.cardHeight - layout.infoSectionHeight) / 2;

    return SizedBox(
      height: topSectionHeight,
      child: Stack(
        clipBehavior: Clip.none,
        children: [
          // 手牌贴近窗口顶部
          Positioned(
            top: layout.topCardY,
            left: 0,
            right: 0,
            child: Center(
              child: SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: _buildOverlappingCardRow(
                  cardCount: cardsNum.clamp(0, 36),
                  cardHeight: layout.cardHeight,
                  cardWidth: layout.cardWidth,
                  cardSpacing: layout.cardSpacing,
                  assetPath: backgroundImageAssetPath,
                ),
              ),
            ),
          ),
          // info 在手牌左侧，与手牌中心水平对齐
          Positioned(
            left: layout.horizontalInfoSectionMargin,
            top: topInfoY,
            child: _buildPlayerInfoCardContent(name, cardsNum, score, layout, textColor),
          ),
        ],
      ),
    );
  }

  /// 从左往右依次叠加的牌行（与 gui_flet 一致：每张牌 left = i * cardSpacing，牌宽 cardWidth，形成重叠）
  Widget _buildOverlappingCardRow({
    required int cardCount,
    required double cardHeight,
    required double cardWidth,
    required double cardSpacing,
    required String assetPath,
  }) {
    if (cardCount <= 0) return const SizedBox.shrink();
    final totalWidth = cardWidth + (cardCount - 1) * cardSpacing;
    return SizedBox(
      width: totalWidth,
      height: cardHeight,
      child: Stack(
        clipBehavior: Clip.none,
        children: List.generate(cardCount, (i) => Positioned(
          left: i * cardSpacing,
          top: 0,
          child: Image.asset(
            assetPath,
            width: cardWidth,
            height: cardHeight,
            fit: BoxFit.contain,
          ),
        )),
      ),
    );
  }

  /// 已出牌叠放行（多张牌从左往右叠放，与手牌一致）。
  /// 约定：列表中索引越大，牌越靠右，且绘制在上层（覆盖左侧牌）。
  Widget _buildOverlappingPlayedRow(
    List<card_model.Card> cards,
    _GameLayoutParams layout,
  ) {
    if (cards.isEmpty) return const SizedBox.shrink();
    final totalWidth = layout.cardWidth + (cards.length - 1) * layout.cardSpacing;
    return SizedBox(
      width: totalWidth,
      height: layout.cardHeight,
      child: Stack(
        clipBehavior: Clip.none,
        children: List.generate(cards.length, (i) {
          return Positioned(
            left: i * layout.cardSpacing,
            top: 0,
            child: Image.asset(
              cardImageAssetPath(cards[i]),
              width: layout.cardWidth,
              height: layout.cardHeight,
              fit: BoxFit.contain,
              errorBuilder: (_, __, ___) => Text(
                cards[i].displayStr,
                style: const TextStyle(color: Colors.white, fontSize: 10),
              ),
            ),
          );
        }),
      ),
    );
  }

  Widget _buildLeftPlayers(FieldInfo info, _GameLayoutParams layout, Color textColor) {
    final cid = info.clientId;
    final nwId = (cid + _posNw) % 6;
    final swId = (cid + _posSw) % 6;
    return Stack(
      children: [
        _buildPlayerInfoCard(
          info.userNames[nwId],
          info.usersCardsNum[nwId],
          info.userScores[nwId],
          layout.horizontalInfoMargin,
          layout.upperInfoSectionY,
          layout,
          true,
          textColor,
        ),
        _buildPlayerInfoCard(
          info.userNames[swId],
          info.usersCardsNum[swId],
          info.userScores[swId],
          layout.horizontalInfoMargin,
          layout.lowerInfoSectionY,
          layout,
          true,
          textColor,
        ),
        // 左侧牌背 + 已出牌
        _buildSideCardBack(layout.horizontalCardMarginSide, layout.upperCardY, true, layout),
        _buildSideCardBack(layout.horizontalCardMarginSide, layout.lowerCardY, true, layout),
        _buildSidePlayedCards(info, (cid + _posNw) % 6, layout.upperCardY, layout, true),
        _buildSidePlayedCards(info, (cid + _posSw) % 6, layout.lowerCardY, layout, true),
      ],
    );
  }

  Widget _buildRightPlayers(FieldInfo info, _GameLayoutParams layout, Color textColor) {
    final cid = info.clientId;
    final neId = (cid + _posNe) % 6;
    final seId = (cid + _posSe) % 6;
    return Stack(
      children: [
        _buildPlayerInfoCard(
          info.userNames[neId],
          info.usersCardsNum[neId],
          info.userScores[neId],
          layout.horizontalInfoMargin,
          layout.upperInfoSectionY,
          layout,
          false,
          textColor,
        ),
        _buildPlayerInfoCard(
          info.userNames[seId],
          info.usersCardsNum[seId],
          info.userScores[seId],
          layout.horizontalInfoMargin,
          layout.lowerInfoSectionY,
          layout,
          false,
          textColor,
        ),
        _buildSideCardBack(layout.horizontalCardMarginSide, layout.upperCardY, false, layout),
        _buildSideCardBack(layout.horizontalCardMarginSide, layout.lowerCardY, false, layout),
        _buildSidePlayedCards(info, (cid + _posNe) % 6, layout.upperCardY, layout, false),
        _buildSidePlayedCards(info, (cid + _posSe) % 6, layout.lowerCardY, layout, false),
      ],
    );
  }

  Widget _buildSideCardBack(double x, double y, bool isLeft, _GameLayoutParams layout) {
    return Positioned(
      left: isLeft ? x : null,
      right: isLeft ? null : x,
      top: y,
      child: Image.asset(
        backgroundImageAssetPath,
        height: layout.cardHeight,
        fit: BoxFit.fitHeight,
      ),
    );
  }

  Widget _buildSidePlayedCards(FieldInfo info, int userId, double cy, _GameLayoutParams layout, bool isLeft) {
    final played = info.usersPlayedCards[userId];
    if (played.isEmpty) return const SizedBox.shrink();
    final startOffset = layout.cardWidth + layout.playedCardSpacing;
    return Positioned(
      left: isLeft ? layout.horizontalCardMarginSide + startOffset : null,
      right: isLeft ? null : layout.horizontalCardMarginSide + startOffset,
      top: cy,
      child: _buildOverlappingPlayedRow(played, layout),
    );
  }

  Widget _buildBottomSelf(FieldInfo info, _GameLayoutParams layout, double width, Color textColor) {
    final cid = info.clientId;
    final height = MediaQuery.sizeOf(context).height;
    // 与顶部对称：手牌底边距窗口底部 = verticalMargin（与顶部手牌距顶一致），再加安全区
    final cardRowBottom = layout.verticalMargin + MediaQuery.paddingOf(context).bottom;
    // info 与手牌中心水平对齐：与顶部对称，按实际手牌位置计算，并整体略微上移让底部区域更紧凑
    final bottomInfoY = height - cardRowBottom - layout.cardHeight / 2 - layout.infoSectionHeight / 2;
    final n = info.clientCards.length;
    return Stack(
      children: [
        _buildPlayerInfoCard(
          info.userNames[cid],
          info.usersCardsNum[cid],
          info.userScores[cid],
          layout.horizontalInfoSectionMargin,
          bottomInfoY,
          layout,
          true,
          textColor,
        ),
        // 手牌在 info section 右侧，中心水平对齐
        Positioned(
          left: layout.horizontalInfoSectionMargin + layout.infoSectionWidth + 20 * layout.scaleX,
          right: 120,
          top: bottomInfoY + (layout.infoSectionHeight - layout.cardHeight) / 2,
          height: layout.cardHeight,
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                if (n > 0) _buildBottomHandCards(info.clientCards, layout),
              ],
            ),
          ),
        ),
      ],
    );
  }

  /// 底部玩家手牌：叠放展示，可点击选牌，选中上浮
  Widget _buildBottomHandCards(List<card_model.Card> cards, _GameLayoutParams layout) {
    if (cards.isEmpty) return const SizedBox.shrink();
    final totalWidth = layout.cardWidth + (cards.length - 1) * layout.cardSpacing;
    return SizedBox(
      width: totalWidth,
      height: layout.cardHeight,
      child: Stack(
        clipBehavior: Clip.none,
        children: List.generate(cards.length, (i) {
          final card = cards[i];
          final selected = i < _selected.length && _selected[i];
          return Positioned(
            left: i * layout.cardSpacing,
            top: selected ? -20 : 0,
            child: GestureDetector(
              onTap: () => _onCardTap(i),
              child: Image.asset(
                cardImageAssetPath(card),
                width: layout.cardWidth,
                height: layout.cardHeight,
                fit: BoxFit.contain,
                errorBuilder: (_, __, ___) => Text(card.displayStr, style: const TextStyle(color: Colors.white)),
              ),
            ),
          );
        }),
      ),
    );
  }

  Widget _buildMyPlayedRow(FieldInfo info, _GameLayoutParams layout, double width) {
    final played = info.usersPlayedCards[info.clientId];
    if (played.isEmpty) return const SizedBox.shrink();
    final startX = _centeredRowStart(layout, played.length, width);
    return Positioned(
      left: startX.toDouble(),
      top: layout.myPlayedCardsY,
      child: _buildOverlappingPlayedRow(played, layout),
    );
  }

  Widget _buildPlayedCards(FieldInfo info, _GameLayoutParams layout, double width) {
    final cid = info.clientId;
    final topId = (cid + _posTop) % 6;
    final topPlayed = info.usersPlayedCards[topId];
    if (topPlayed.isEmpty) return const SizedBox.shrink();
    final startX = _centeredRowStart(layout, topPlayed.length, width);
    return Positioned(
      left: startX.toDouble(),
      right: 0,
      top: layout.topPlayedCardsY,
      child: _buildOverlappingPlayedRow(topPlayed, layout),
    );
  }

  Widget _buildScorePanel(FieldInfo info, _GameLayoutParams layout, Size size, Color textColor) {
    final teamScores = calculateTeamScores(
      info.headMaster,
      info.clientId,
      info.usersCardsNum,
      info.userScores,
    );
    final nowPlayerName = info.nowPlayer >= 0 && info.nowPlayer < info.userNames.length
        ? _truncateName(info.userNames[info.nowPlayer], 6)
        : '-';
    final headMasterName = info.headMaster >= 0 && info.headMaster < info.userNames.length
        ? _truncateName(info.userNames[info.headMaster], 6)
        : '无';
    final panelW = 200.0 * layout.scaleX;
    final panelH = 200.0 * layout.scaleY;
    var top = layout.verticalMargin;
    final scoreBottom = top + panelH;
    final playerTop = layout.upperInfoSectionY;
    final playerBottom = playerTop + layout.infoSectionHeight;
    if (scoreBottom > playerTop) {
      final candidate = playerBottom + 10 * layout.scaleY;
      final maxTop = (size.height - panelH - 10 * layout.scaleY).clamp(0, size.height);
      top = candidate < maxTop ? candidate : top;
    }

    return Positioned(
      right: layout.scoreAnchorX,
      top: top,
      child: Container(
        width: panelW,
        constraints: BoxConstraints(maxHeight: panelH),
        padding: EdgeInsets.all(14 * layout.scale),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          gradient: const LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [Color(0xFF0d1820), Color(0xFF1e3a52)],
          ),
        ),
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '——比分面板——',
                style: TextStyle(
                  color: textColor,
                  fontSize: (layout.fontSize * 0.65).clamp(11, 15),
                  fontWeight: FontWeight.bold,
                ),
              ),
              SizedBox(height: 6 * layout.scale),
              _scoreRow('己方得分', '${teamScores[0]}', textColor, layout, true),
              _scoreRow('对方得分', '${teamScores[1]}', textColor, layout, true),
              _scoreRow('场上分数', '${info.nowScore}', textColor, layout, true),
              _scoreRow('当前出牌', nowPlayerName, textColor, layout, false),
              _scoreRow('头科', headMasterName, textColor, layout, false),
            ],
          ),
        ),
      ),
    );
  }

  Widget _scoreRow(String label, String value, Color textColor, _GameLayoutParams layout, bool boldValue) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: TextStyle(color: const Color(0xFFa0a0a0), fontSize: layout.fontSize * 0.65)),
        Text(
          value,
          style: TextStyle(
            color: const Color(0xFFffd700),
            fontSize: boldValue ? 26 : layout.fontSize * 0.65,
            fontWeight: boldValue ? FontWeight.bold : null,
          ),
        ),
      ],
    );
  }

  Widget _buildActionButtons(_GameLayoutParams layout) {
    const labels = ['重置', '确定', '托管', '跳过'];
    final handlers = [_onReset, _onConfirm, _onToggleAutoPlay, _onSkip];
    // 重置：只要有手牌就可以随时清空选择
    final canReset = _info != null && _info!.clientCards.isNotEmpty;
    // 确认：只有轮到我、且当前有等待完成的回合时才可点击
    final canConfirm = _turnCompleter != null && !(_turnCompleter?.isCompleted ?? true);
    const spacing = 8.0;
    return Positioned(
      right: layout.buttonRightMargin,
      bottom: layout.buttonBottomMargin,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              _actionBtn(0, labels[0], handlers[0], canReset, layout),
              SizedBox(width: spacing),
              _actionBtn(1, labels[1], handlers[1], canConfirm, layout),
            ],
          ),
          SizedBox(height: spacing),
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              // 托管按钮始终可用，用于随时开启/关闭托管
              _actionBtn(2, _autoPlayEnabled ? '取消托管' : labels[2], handlers[2], true, layout),
              SizedBox(width: spacing),
              _actionBtn(3, labels[3], handlers[3], _canSkip, layout),
            ],
          ),
        ],
      ),
    );
  }

  Widget _actionBtn(int i, String label, VoidCallback handler, bool enabled, _GameLayoutParams layout) {
    return SizedBox(
      width: 72,
      child: FilledButton(
        onPressed: enabled ? handler : null,
        child: Text(label, style: TextStyle(fontSize: layout.fontSize * 0.7)),
      ),
    );
  }
}

class _GameOverResult {
  _GameOverResult(this.clientPlayer, this.gameOverCode) : isError = false;
  _GameOverResult.error() : clientPlayer = 0, gameOverCode = 0, isError = true;

  final int clientPlayer;
  final int gameOverCode;
  final bool isError;

  bool get weWon {
    if (isError) return false;
    return (clientPlayer + 1) % 2 == (gameOverCode + 2) % 2;
  }

  bool get doubleWin => !isError && gameOverCode < 0;
}

class _GameOverOverlay extends StatelessWidget {
  const _GameOverOverlay({required this.result, required this.onExit});

  final _GameOverResult result;
  final VoidCallback onExit;

  @override
  Widget build(BuildContext context) {
    String message;
    if (result.isError) {
      message = '对局异常结束';
    } else if (result.weWon) {
      message = '你的队伍获得了胜利';
      if (result.doubleWin) message += '，并成功双统';
    } else {
      message = '你的队伍未能取得胜利';
      if (result.doubleWin) message += '，并被对方双统';
    }
    return Scaffold(
      backgroundColor: const Color(0xFF0d1820),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Text(
                '游戏结束',
                style: TextStyle(color: Colors.white, fontSize: 24),
              ),
              const SizedBox(height: 16),
              Text(
                message,
                style: const TextStyle(color: Colors.white70, fontSize: 16),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 32),
              FilledButton(
                onPressed: onExit,
                child: const Text('返回'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
