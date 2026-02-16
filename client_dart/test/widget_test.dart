// 表现层 widget 测试：登录页、大厅页

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:liujiatong/presentation/screens/login_screen.dart';
import 'package:liujiatong/presentation/screens/lobby_screen.dart';

void main() {
  testWidgets('登录页无配置时展示表单', (WidgetTester tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: LoginScreen(
          initialConfig: null,
          onJoinRoom: (_) {},
          onLogout: () {},
        ),
      ),
    );

    expect(find.text('六家统'), findsWidgets);
    expect(find.text('确认连接'), findsOneWidget);
    expect(find.byType(TextField), findsWidgets);
  });

  testWidgets('大厅页展示人数与名单', (WidgetTester tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: LobbyScreen(
          usersName: ['Alice', 'Bob'],
          usersError: [false, false],
        ),
      ),
    );

    expect(find.text('六家统'), findsWidgets);
    expect(find.text('等待游戏开始…'), findsOneWidget);
    expect(find.text('2 / 6 人'), findsOneWidget);
  });
}
