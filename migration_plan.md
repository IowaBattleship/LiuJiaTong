# 六家统客户端：Python 到 Dart (Flutter) 迁移规划

> 本文档旨在梳理现有项目结构、分析迁移步骤，并结合架构优化建议，帮助建立清晰的迁移任务清单。**不涉及实际操作**，仅作为规划参考。

---

## 一、现有项目结构总览

### 1.1 项目简介

- **项目名称**：六家统（LiuJiaTong）
- **类型**：六人扑克类游戏客户端
- **当前技术栈**：Python 3.x
- **运行模式**：
  - **Flet**：桌面端主用 UI（`flet run` / `flet build`）
  - **Kivy**：移动端 UI（`buildozer android` 打包，排除 Flet/Tkinter）
  - **Tkinter**：备选桌面 UI
  - **CLI**：命令行模式

### 1.2 目录结构与模块职责

```
LiuJiaTong/
├── main.py                    # 应用入口：Flet 或 Buildozer(Kivy) 二选一
├── buildozer.spec             # Android 打包配置
│
├── cli/                       # 命令行 / 客户端核心
│   ├── __main__.py            # Client 类：游戏主循环、网络收发、状态管理
│   ├── card_utils.py          # 牌面转换（str↔int、分数计算等）
│   ├── interface_cli.py       # CLI 界面回调
│   ├── terminal_printer.py    # 终端打印
│   └── terminal_utils.py      # 终端工具（颜色、确认、信号处理）
│
├── client/                    # 客户端抽象层
│   ├── gui.py                 # GUI 抽象：Flet/Kivy/Tkinter 统一入口
│   ├── interface.py           # 业务接口：等待大厅、牌局、游戏结束等
│   └── playing_handler.py     # 出牌输入（CLI 输入 / GUI 队列 / 模拟模式）
│
├── core/                      # 核心领域逻辑
│   ├── card.py                # 扑克牌模型 (Suits, Card)
│   ├── config.py              # 配置模型 (ip, port, name, cookie)
│   ├── FieldInfo.py           # 牌局信息 DTO
│   ├── logger.py              # 日志初始化
│   ├── playingrules.py        # 出牌规则校验（牌型判断、合法性）
│   ├── sound/                 # 音效播放（平台调用 afplay/aplay/powershell）
│   └── auto_play/             # 自动出牌策略
│       └── strategy.py
│
├── network/
│   └── my_network.py          # TCP 收发：4 字节长度头 + pickle 序列化
│
├── gui_flet/                  # Flet UI（桌面，buildozer 排除）
│   ├── main.py
│   └── gui_flet.py
├── gui_kivy/                  # Kivy UI（Android 打包用）
│   └── gui_kivy.py
├── gui_tkinter/               # Tkinter UI（buildozer 排除）
│   └── gui_tkinter.py
│
├── core/assets/               # 牌面图片、背景图等
├── core/fonts/                # 字体文件
├── core/sound/*.wav           # 音效文件
│
├── server/                    # 服务端（本次迁移不涉及）
└── test/                      # 单元测试
```

### 1.3 关键依赖

| 模块 | 依赖 | 说明 |
|------|------|------|
| 网络 | `socket`, `struct`, `pickle` | 自定义 TCP 协议，**pickle 为 Python 专用** |
| 桌面 (Flet) | `flet` | 跨平台 UI |
| 移动 (Kivy) | `kivy`, `pyjnius` | 仅 buildozer 打包时使用 |
| 桌面 (Tkinter) | `tkinter` | 系统自带 |
| 音效 | `subprocess`, `platform` | 调用系统命令 afplay/aplay/powershell |

---

## 二、迁移目标与范围

### 2.1 迁移目标

- **语言**：Python → Dart
- **UI 框架**：Flutter（一套代码覆盖 Android、iOS、Web、Windows、macOS、Linux）
- **打包方式**：由 buildozer 改为 Flutter 原生构建

### 2.2 迁移范围

- ✅ **客户端全部**：网络、配置、牌局逻辑、UI、音效
- ❌ **服务端**：保持 Python，但需配合协议调整（见下文）

---

## 三、架构与协议关键点

### 3.1 网络协议现状

当前协议：

- **格式**：`[4 字节长度头 (C int)] + [pickle 序列化数据]`
- **问题**：pickle 为 Python 专属，Dart 无法直接兼容
- **解决方案**：
  - **方案 A（推荐）**：客户端与服务端统一改为 **JSON** 序列化
  - **方案 B**：服务端增加「协议适配层」，同时支持 pickle 与 JSON（按请求类型切换）
  - **方案 C**：使用 Protocol Buffers / MessagePack 等跨语言格式

### 3.2 当前客户端运行流程（简要）

```
1. 加载配置（LiuJiaTong.json）或用户输入
2. 连接服务器 → 发送 cookie / 用户名
3. 等待大厅（6 人满员）
4. 接收场上信息（is_player, users_name, client_player）
5. 主循环：
   - recv_round_info（牌局状态）
   - 更新 UI（FieldInfo）
   - 若轮到自己 → playing() 获取出牌 → send_player_info
   - 若 game_over → 显示结果并退出
```

### 3.3 现有架构存在的问题

1. **UI 分散**：三套 UI（Flet/Kivy/Tkinter）逻辑相似但实现不同
2. **阻塞式网络**：主循环中 `recv_data_from_socket` 为阻塞调用
3. **全局状态**：Client 类承载大量状态，职责过重
4. **平台耦合**：音效、终端等强依赖操作系统

---

## 四、Dart/Flutter 目标架构建议

### 4.1 整体分层

```
┌─────────────────────────────────────────────────────────────┐
│  Presentation (UI)                                          │
│  - 等待大厅、牌局、游戏结束等页面                              │
│  - 使用 Provider / Riverpod / Bloc 做状态管理                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Application (用例 / 业务流程)                                │
│  - 连接、登录、等待、出牌、结束等流程                           │
│  - 协调 Domain 与 Data                                       │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────────┐     ┌─────────────────────────────┐
│  Domain (领域)           │     │  Data (数据)                 │
│  - Card, Suits           │     │  - 网络层 (Socket/JSON)      │
│  - Config, FieldInfo     │     │  - 配置持久化                │
│  - 出牌规则 (playingrules) │    │  - 日志                      │
│  - 自动出牌策略           │     └─────────────────────────────┘
└─────────────────────────┘
```

### 4.2 目录建议（Dart 项目）

```
lib/
├── main.dart
├── app.dart
│
├── core/                     # 领域核心
│   ├── models/
│   │   ├── card.dart
│   │   ├── config.dart
│   │   └── field_info.dart
│   ├── rules/
│   │   └── playing_rules.dart
│   └── auto_play/
│       └── strategy.dart
│
├── data/                     # 数据层
│   ├── network/
│   │   ├── socket_client.dart
│   │   └── protocol.dart     # JSON 序列化/反序列化
│   ├── config/
│   │   └── config_repository.dart
│   └── logger.dart
│
├── application/              # 业务逻辑
│   ├── game_controller.dart
│   └── game_state.dart
│
├── presentation/
│   ├── screens/
│   │   ├── lobby_screen.dart
│   │   ├── game_screen.dart
│   │   └── result_screen.dart
│   ├── widgets/              # 牌面、玩家信息等
│   └── providers/
│
└── services/
    └── sound_service.dart
```

### 4.3 技术选型建议

| 功能 | 推荐方案 | 说明 |
|------|----------|------|
| 状态管理 | Riverpod 或 Bloc | 适合网络驱动、多状态切换 |
| 网络 | `dart:io` Socket 或 `web_socket_channel` | 若未来考虑 WebSocket 可提前抽象 |
| 序列化 | `dart:convert` JSON | 与 Python 服务端需约定字段格式 |
| 音效 | `audioplayers` | 跨平台统一 |
| 配置持久化 | `shared_preferences` 或 本地 JSON 文件 | 与现有 LiuJiaTong.json 语义一致 |

---

## 五、迁移步骤规划

### 阶段 0：前置准备（不写代码）

| 序号 | 任务 | 产出 |
|------|------|------|
| 0.1 | 确认迁移范围：仅客户端，服务端是否一并调整协议 | 决策记录 |
| 0.2 | 确定协议方案（JSON / Protobuf / 其他） | 协议文档 |
| 0.3 | 梳理服务端收发数据结构，写出 JSON Schema 或等价文档 | 协议规范 |
| 0.4 | 搭建 Flutter 工程骨架，配置多平台（Android/iOS/Web/Desktop） | 可运行空项目 |

### 阶段 1：领域层迁移（纯逻辑，无 UI/网络）

| 序号 | 任务 | 对应现有模块 | 复杂度 |
|------|------|--------------|--------|
| 1.1 | 迁移 `Card`、`Suits` | core/card.py | 低 |
| 1.2 | 迁移 `Config` | core/config.py | 低 |
| 1.3 | 迁移 `FieldInfo` | core/FieldInfo.py | 低 |
| 1.4 | 迁移 `playingrules`（牌型判断、合法性） | core/playingrules.py | 中 |
| 1.5 | 迁移 `card_utils`（str↔int、分数计算等） | cli/card_utils.py | 低 |
| 1.6 | 迁移 `auto_play/strategy` | core/auto_play/strategy.py | 中 |
| 1.7 | 为领域层编写单元测试 | - | 中 |

### 阶段 2：数据层迁移

| 序号 | 任务 | 对应现有模块 | 复杂度 |
|------|------|--------------|--------|
| 2.1 | 实现 JSON 协议（序列化/反序列化） | network/my_network.py（逻辑替换） | 中 |
| 2.2 | 实现 Socket 收发（4 字节头 + JSON body） | network/my_network.py | 中 |
| 2.3 | 实现配置持久化（读/写 LiuJiaTong.json） | core/config.py | 低 |
| 2.4 | 实现日志模块 | core/logger.py | 低 |
| 2.5 | **若服务端尚未改协议**：实现协议适配或等待服务端支持 JSON | - | 高 |

### 阶段 3：应用层 / 游戏控制

| 序号 | 任务 | 对应现有模块 | 复杂度 |
|------|------|--------------|--------|
| 3.1 | 抽象 GameController（连接、收发、状态更新） | cli/__main__.py 中 Client | 高 |
| 3.2 | 将阻塞式循环改为 Stream / Future 驱动 | - | 中 |
| 3.3 | 实现心跳、断线重连逻辑 | cli/__main__.py | 中 |
| 3.4 | 实现 cookie 恢复流程 | cli/__main__.py | 低 |

### 阶段 4：表现层（UI）

| 序号 | 任务 | 对应现有模块 | 复杂度 |
|------|------|--------------|--------|
| 4.1 | 登录/配置页（IP、端口、用户名） | gui_flet / gui_kivy 登录部分 | 中 |
| 4.2 | 等待大厅页 | gui_flet / gui_kivy | 中 |
| 4.3 | 牌局主界面（手牌、出牌区、玩家信息、分数） | gui_flet / gui_kivy | 高 |
| 4.4 | 出牌交互（选牌、跳过、自动出牌） | client/playing_handler + gui | 中 |
| 4.5 | 游戏结束页 | gui_flet / gui_kivy | 低 |
| 4.6 | 音效服务集成 | core/sound | 低 |

### 阶段 5：资源与构建

| 序号 | 任务 | 对应现有 | 复杂度 |
|------|------|----------|--------|
| 5.1 | 迁移 `core/assets`（牌面图、背景）至 Flutter `assets/` | core/assets/ | 低 |
| 5.2 | 迁移 `core/fonts` 至 `fonts/` | core/fonts/ | 低 |
| 5.3 | 迁移 `core/sound/*.wav` 至 `assets/sounds/` | core/sound/*.wav | 低 |
| 5.4 | 配置 `pubspec.yaml` 资源引用 | - | 低 |
| 5.5 | 配置 Android / iOS / Web / Desktop 构建 | 替代 buildozer.spec | 中 |
| 5.6 | 图标、启动图、应用名等 | buildozer.spec | 低 |

### 阶段 6：联调与发布

| 序号 | 任务 | 说明 |
|------|------|------|
| 6.1 | 与 Python 服务端联调（协议、流程、边界情况） | 需服务端支持新协议 |
| 6.2 | 各平台真机/模拟器测试 | Android、iOS、Desktop、Web |
| 6.3 | 性能与稳定性验证 | 长对局、断线重连 |
| 6.4 | 打包发布（APK、IPA、Web、桌面安装包） | 按目标平台配置 |

---

## 六、风险与注意事项

### 6.1 协议兼容

- **pickle → JSON**：服务端必须同步修改或提供适配，否则无法联通
- 建议优先完成协议文档与两端示例，再推进业务逻辑迁移

### 6.2 平台差异

- 音效：原实现依赖 `afplay` / `aplay` / PowerShell，Dart 需使用 `audioplayers` 等跨平台方案
- 配置文件路径：移动端与桌面端存储路径不同，需统一抽象

### 6.3 弃用能力

- **CLI 模式**：Dart 可做，但优先级低，可延后或仅在 Debug 保留
- **模拟/自动出牌**：需迁移 `auto_play` 及 `is_simulation_mode` 逻辑

---

## 七、工作量粗估（仅供排期参考）

| 阶段 | 预估人天 | 说明 |
|------|----------|------|
| 阶段 0 | 1–2 | 协议设计、环境准备 |
| 阶段 1 | 3–5 | 领域逻辑迁移与测试 |
| 阶段 2 | 3–5 | 网络与数据层（含协议改造） |
| 阶段 3 | 4–6 | 游戏控制与异步重构 |
| 阶段 4 | 6–10 | UI 完整实现 |
| 阶段 5 | 1–2 | 资源与构建 |
| 阶段 6 | 3–5 | 联调与发布 |
| **合计** | **21–35** | 视熟悉程度与需求变更浮动 |

---

## 八、建议执行顺序

1. **先协议、再领域**：确定并实现 JSON 协议，保证客户端能与服务端通信
2. **领域可独立验证**：领域层无依赖，可先迁移并通过测试
3. **数据层紧跟**：网络与配置完成后，即可打通端到端联调
4. **UI 最后**：在可运行的主循环基础上，逐步替换为 Flutter 界面

---

## 九、附录：协议数据结构参考（需与服务端确认）

以下为根据现有 Python 代码推断的收发结构，**实际迁移前需与服务端共同确认**：

### 发送（客户端 → 服务端）

- 登录：`bool`（是否用 cookie）+ 可选 `str`（cookie 或用户名）
- 出牌：`List<Card>`（手牌）、`List<Card>`（本回合出牌）、`int`（当前分数）
- 心跳：`bool`（是否已完成出牌）

### 接收（服务端 → 客户端）

- 等待大厅：`List<String>`（用户名单）、`List<?>`（错误信息）
- 场上信息：`bool`（是否玩家）、`List<String>`（用户名单）、`int`（client_player）
- 牌局信息：`int`（game_over）、`List<int>`（分数）、`List<int>`（手牌数）、`List<List<Card>>`（出牌）、可选 `List<List<Card>>`（全部手牌，game_over 时）、`List<Card>`（当前手牌）、`int`（now_score）、`int`（now_player）、`int`（head_master）

**Card 的 JSON 表示建议**：`{"suit": "Spade"|"Heart"|"Club"|"Diamond"|"", "value": 3..17}`

---

*文档版本：1.0 | 最后更新：2025-02-15*
