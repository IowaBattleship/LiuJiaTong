# 六家统 Flutter 客户端

六家统（LiuJiaTong）的 Flutter 客户端，一套代码支持 Android、iOS、Web、Windows、macOS、Linux。

## 环境要求

- [Flutter SDK](https://docs.flutter.dev/get-started/install)（含对应平台工具链）
- **Windows 桌面**：需安装 [Visual Studio](https://visualstudio.microsoft.com/) 并勾选「使用 C++ 的桌面开发」
- **macOS 桌面**：Xcode 命令行工具
- **Linux 桌面**：clang、GTK 等（见 [Flutter 文档](https://docs.flutter.dev/get-started/install/linux)）

## 运行

```bash
cd client_dart
flutter pub get
flutter run
```

默认会选择当前可用的设备。指定平台：

```bash
# Web（Chrome）
flutter run -d chrome

# Windows 桌面
flutter run -d windows

# Android 模拟器/真机
flutter run -d android

# iOS 模拟器（仅 macOS）
flutter run -d ios

# macOS 桌面（仅 macOS）
flutter run -d macos

# Linux 桌面
flutter run -d linux
```

查看已连接设备：`flutter devices`

## 项目结构

- `lib/` — Dart 应用代码（入口 `main.dart`）
- `docs/` — 协议等文档（如 `protocol.md`）
- `test/` — 单元/Widget 测试

协议与迁移步骤见仓库根目录 `migration_plan.md` 及本目录 `docs/protocol.md`。
