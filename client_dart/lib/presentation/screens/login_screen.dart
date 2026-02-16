import 'package:flutter/material.dart';
import 'package:liujiatong/core/models/config.dart';

/// 登录/配置页：有配置时显示「加入房间」「退出登录」，无配置时显示输入表单
class LoginScreen extends StatefulWidget {
  const LoginScreen({
    super.key,
    this.initialConfig,
    this.joinLoading = false,
    this.joinError,
    required this.onJoinRoom,
    required this.onLogout,
  });

  final Config? initialConfig;
  final bool joinLoading;
  final String? joinError;
  final void Function(Config config) onJoinRoom;
  final VoidCallback onLogout;

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  Config? _config;
  final _ipController = TextEditingController();
  final _portController = TextEditingController();
  final _nameController = TextEditingController();
  String? _error;

  @override
  void initState() {
    super.initState();
    _config = widget.initialConfig;
    _syncControllersFromConfig();
  }

  @override
  void didUpdateWidget(LoginScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.initialConfig != widget.initialConfig) {
      _config = widget.initialConfig;
      _syncControllersFromConfig();
    }
  }

  void _syncControllersFromConfig() {
    if (_config != null) {
      _ipController.text = _config!.ip;
      _portController.text = _config!.port.toString();
      _nameController.text = _config!.name;
    }
  }

  @override
  void dispose() {
    _ipController.dispose();
    _portController.dispose();
    _nameController.dispose();
    super.dispose();
  }

  void _submitFromForm() {
    final ip = _ipController.text.trim();
    final portStr = _portController.text.trim();
    final name = _nameController.text.trim();
    if (ip.isEmpty || portStr.isEmpty || name.isEmpty) {
      setState(() => _error = '请填写服务器地址、端口和用户名');
      return;
    }
    int port;
    try {
      port = int.parse(portStr);
    } catch (_) {
      setState(() => _error = '端口请输入数字');
      return;
    }
    setState(() => _error = null);
    widget.onJoinRoom(Config(ip: ip, port: port, name: name));
  }

  void _joinRoom() {
    if (_config != null) {
      widget.onJoinRoom(_config!);
      return;
    }
    _submitFromForm();
  }

  bool get _loading => widget.joinLoading;
  String? get _displayError => widget.joinError ?? _error;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final hasConfig = _config != null;

    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 360),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    '六家统',
                    style: theme.textTheme.headlineMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 8),
                  if (hasConfig)
                    Text(
                      '欢迎回来',
                      style: theme.textTheme.titleMedium?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    )
                  else
                    Text(
                      '请输入服务器信息',
                      style: theme.textTheme.titleMedium?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                  const SizedBox(height: 24),
                  if (hasConfig) ...[
                    Text(
                      '服务器: ${_config!.ip}:${_config!.port}',
                      style: theme.textTheme.bodyLarge,
                    ),
                    Text(
                      '用户名: ${_config!.name}',
                      style: theme.textTheme.bodyLarge,
                    ),
                    const SizedBox(height: 32),
                    if (_displayError != null) ...[
                      Text(_displayError!, style: TextStyle(color: theme.colorScheme.error)),
                      const SizedBox(height: 16),
                    ],
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        FilledButton(
                          onPressed: _loading ? null : _joinRoom,
                          child: _loading
                              ? const SizedBox(
                                  width: 20,
                                  height: 20,
                                  child: CircularProgressIndicator(strokeWidth: 2),
                                )
                              : const Text('加入房间'),
                        ),
                        const SizedBox(width: 16),
                        OutlinedButton(
                          onPressed: _loading
                              ? null
                              : () {
                                  setState(() => _config = null);
                                  widget.onLogout();
                                },
                          child: const Text('退出登录'),
                        ),
                      ],
                    ),
                  ] else ...[
                    TextField(
                      controller: _ipController,
                      decoration: const InputDecoration(
                        labelText: '服务器地址',
                        hintText: '如 192.168.1.100',
                        border: OutlineInputBorder(),
                      ),
                      keyboardType: TextInputType.url,
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _portController,
                      decoration: const InputDecoration(
                        labelText: '端口',
                        hintText: '如 8888',
                        border: OutlineInputBorder(),
                      ),
                      keyboardType: TextInputType.number,
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _nameController,
                      decoration: const InputDecoration(
                        labelText: '用户名',
                        hintText: '请输入用户名',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    if (_displayError != null) ...[
                      const SizedBox(height: 12),
                      Text(_displayError!, style: TextStyle(color: theme.colorScheme.error)),
                    ],
                    const SizedBox(height: 24),
                    FilledButton(
                      onPressed: _submitFromForm,
                      child: const Text('确认连接'),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
