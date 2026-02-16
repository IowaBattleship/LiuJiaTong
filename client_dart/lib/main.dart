import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:liujiatong/application/game_controller.dart';
import 'package:liujiatong/application/game_login.dart';
import 'package:liujiatong/core/models/config.dart';
import 'package:liujiatong/data/config/config_repository.dart';
import 'package:liujiatong/presentation/screens/game_screen.dart';
import 'package:liujiatong/presentation/screens/lobby_screen.dart';
import 'package:liujiatong/presentation/screens/login_screen.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await SystemChrome.setPreferredOrientations([
    DeviceOrientation.landscapeLeft,
    DeviceOrientation.landscapeRight,
  ]);
  runApp(const LiujiatongApp());
}

/// 六家统 Flutter 客户端入口
class LiujiatongApp extends StatelessWidget {
  const LiujiatongApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: '六家统',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple),
        useMaterial3: true,
        fontFamily: 'ZiTiFangSong',
      ),
      home: const _AppRoot(),
    );
  }
}

enum _Screen { login, lobby, game }

/// 根状态：加载配置 → 登录页 → 大厅 → 牌局（占位）
class _AppRoot extends StatefulWidget {
  const _AppRoot();

  @override
  State<_AppRoot> createState() => _AppRootState();
}

class _AppRootState extends State<_AppRoot> {
  final ConfigRepository _repo = ConfigRepository();
  Config? _config;
  bool _configLoaded = false;
  GameController? _controller;
  _Screen _screen = _Screen.login;
  bool _joinLoading = false;
  String? _joinError;

  @override
  void initState() {
    super.initState();
    _loadConfig();
  }

  Future<void> _loadConfig() async {
    final c = await _repo.load();
    if (!mounted) return;
    setState(() {
      _config = c;
      _configLoaded = true;
    });
  }

  Future<void> _onJoinRoom(Config config) async {
    setState(() {
      _joinLoading = true;
      _joinError = null;
    });
    try {
      final controller = GameController(config: config);
      await loginWithCookieRecovery(controller, _repo);
      if (!mounted) return;
      setState(() {
        _controller = controller;
        _screen = _Screen.lobby;
        _joinLoading = false;
        _joinError = null;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _joinLoading = false;
        _joinError = e is UnsupportedError ? e.message : e.toString();
      });
    }
  }

  void _onLogout() async {
    await _repo.clear();
    _controller?.close();
    if (!mounted) return;
    setState(() {
      _config = null;
      _controller = null;
      _screen = _Screen.login;
      _joinError = null;
    });
  }

  void _onEnterGame() {
    setState(() => _screen = _Screen.game);
  }

  @override
  Widget build(BuildContext context) {
    if (!_configLoaded) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }

    switch (_screen) {
      case _Screen.login:
        return LoginScreen(
          initialConfig: _config,
          joinLoading: _joinLoading,
          joinError: _joinError,
          onJoinRoom: _onJoinRoom,
          onLogout: _onLogout,
        );
      case _Screen.lobby:
        return _LobbyHost(
          controller: _controller!,
          onEnterGame: _onEnterGame,
          onBack: () async {
            await _controller?.close();
            if (!mounted) return;
            setState(() {
              _controller = null;
              _screen = _Screen.login;
            });
          },
        );
      case _Screen.game:
        return GameScreen(
          controller: _controller!,
          onExit: () async {
            await _controller?.close();
            if (!mounted) return;
            setState(() {
              _controller = null;
              _screen = _Screen.login;
            });
          },
        );
    }
  }
}

/// 大厅容器：启动 recvWaitingHallInfo，用回调刷新 LobbyScreen，满 6 人后 recvFieldInfo 并进入牌局
class _LobbyHost extends StatefulWidget {
  const _LobbyHost({
    required this.controller,
    required this.onEnterGame,
    required this.onBack,
  });

  final GameController controller;
  final VoidCallback onEnterGame;
  final VoidCallback onBack;

  @override
  State<_LobbyHost> createState() => _LobbyHostState();
}

class _LobbyHostState extends State<_LobbyHost> {
  List<String> _usersName = [];
  List<bool> _usersError = [];
  String? _error;

  @override
  void initState() {
    super.initState();
    _runWaitingHall();
  }

  Future<void> _runWaitingHall() async {
    try {
      await widget.controller.recvWaitingHallInfo((names, errors) {
        if (!mounted) return;
        setState(() {
          _usersName = names;
          _usersError = errors;
        });
      });
      await widget.controller.recvFieldInfo();
      if (!mounted) return;
      widget.onEnterGame();
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = e.toString());
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_error != null) {
      return Scaffold(
        appBar: AppBar(title: const Text('大厅')),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
                const SizedBox(height: 16),
                FilledButton(
                  onPressed: widget.onBack,
                  child: const Text('返回'),
                ),
              ],
            ),
          ),
        ),
      );
    }
    return Scaffold(
      body: LobbyScreen(
        usersName: _usersName,
        usersError: _usersError,
      ),
    );
  }
}

