import 'package:flutter/material.dart';

/// 等待大厅页：展示当前大厅用户名单与错误信息，满 6 人后由外部进入下一流程
class LobbyScreen extends StatelessWidget {
  const LobbyScreen({
    super.key,
    required this.usersName,
    required this.usersError,
  });

  final List<String> usersName;
  final List<bool> usersError;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final count = usersName.length;

    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  '六家统',
                  style: theme.textTheme.headlineMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 24),
                Text(
                  count >= 6 ? '人已满，即将开始…' : '等待游戏开始…',
                  style: theme.textTheme.titleMedium?.copyWith(
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  '$count / 6 人',
                  style: theme.textTheme.bodyLarge,
                ),
                const SizedBox(height: 32),
                if (usersName.isNotEmpty)
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            '当前房间',
                            style: theme.textTheme.titleSmall,
                          ),
                          const SizedBox(height: 8),
                          ...List.generate(usersName.length, (i) {
                            final name = usersName[i];
                            final hasError = i < usersError.length && usersError[i];
                            return Padding(
                              padding: const EdgeInsets.symmetric(vertical: 4),
                              child: Row(
                                children: [
                                  Icon(
                                    hasError ? Icons.warning_amber : Icons.person,
                                    size: 20,
                                    color: hasError
                                        ? theme.colorScheme.error
                                        : theme.colorScheme.primary,
                                  ),
                                  const SizedBox(width: 8),
                                  Expanded(
                                    child: Text(
                                      name.isEmpty ? '(空)' : name,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                  ),
                                  if (hasError)
                                    Text(
                                      '异常',
                                      style: theme.textTheme.bodySmall?.copyWith(
                                        color: theme.colorScheme.error,
                                      ),
                                    ),
                                ],
                              ),
                            );
                          }),
                        ],
                      ),
                    ),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
