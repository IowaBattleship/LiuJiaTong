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
│   ├── __main__.py            
│   ├── card_utils.py          # 牌面转换（str↔int、分数计算等）
│   ├── interface_cli.py       # CLI 界面回调
│   ├── terminal_printer.py    # 终端打印
│   └── terminal_utils.py      # 终端工具（颜色、确认、信号处理）
│
├── client/                    # 客户端抽象层
│   ├── gui.py                 # GUI 抽象：Flet/Kivy/Tkinter 统一入口
│   ├── interface.py           # 业务接口：等待大厅、牌局、游戏结束等
│   ├── playing_handler.py     # 出牌输入（CLI 输入 / GUI 队列 / 模拟模式）
|   └── client.py
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

## 十、client_dart 逐步实现顺序（边调试边迁移）

以下按「先协议、再领域、再数据层、再应用层、最后 UI」的原则，拆成可单独实现、可验证的小步，便于在 `client_dart` 目录下边做边联调。

### 阶段 0：环境与协议约定（先做再写 Dart）

| 步骤 | 任务 | 产出 | 如何验证 |
|------|------|------|----------|
| 0.1 | 在项目下创建 `client_dart` Flutter 工程（或纯 Dart 包 + 单独 Flutter app） | `client_dart/` 可运行空应用 | `flutter run` 能跑起来 |
| 0.2 | **服务端**：在 `network/my_network.py` 增加 JSON 协议分支（如按首字节/首条消息区分 pickle vs JSON），或新文件 `my_network_json.py`，保持「4 字节长度头 + body」不变，body 改为 `json.dumps`/`json.loads`；Card 用 `to_dict`/`from_dict`（与附录九一致） | 服务端支持 JSON 连接 | 用 Python 脚本仅调用 JSON 收发与现有服务端联调通过 |
| 0.3 | 把附录九的收发结构整理成 **协议文档**（JSON 字段名、类型、顺序、Card 格式），放在 `client_dart/docs/protocol.md` 或项目根目录 | 一份客户端/服务端共用的协议说明 | 服务端与 Dart 实现都按此文档实现 |

### 阶段 1：领域层（client_dart 内，不依赖网络）

| 步骤 | 任务 | 对应 Python | 如何验证 |
|------|------|--------------|----------|
| 1.1 | 实现 `Suits` 枚举、`Card` 类及 `fromJson`/`toJson`（与协议文档一致） | core/card.py | 单元测试：构造 Card、序列化/反序列化 JSON |
| 1.2 | 实现 `Config`（ip, port, name, cookie）及 `fromJson`/`toJson` | core/config.py | 单元测试：与现有 LiuJiaTong.json 格式兼容 |
| 1.3 | 实现 `FieldInfo`（或同名 DTO），字段与 client 当前使用的场面信息一致 | core/FieldInfo.py | 单元测试：从 JSON 构造、字段齐全 |
| 1.4 | 实现 `card_utils` 能力：牌面 str↔int、分数计算、`last_played` 等 | cli/card_utils.py | 单元测试：与 Python 用例对照 |
| 1.5 | 实现出牌规则：牌型判断、出牌合法性校验 | core/playingrules.py | 单元测试：若干牌型与非法出牌用例 |
| 1.6 | 实现自动出牌策略（可选，可后移） | core/auto_play/strategy.py | 单元测试：给定手牌与场面，输出合法出牌 |

### 阶段 2：数据层——协议与 Socket（可与服务端 JSON 联调）

| 步骤 | 任务 | 对应 Python | 如何验证 |
|------|------|--------------|----------|
| 2.1 | 实现「4 字节长度头（大端/小端与 Python struct 一致）+ body」的读写工具函数 | network/my_network.py | 单元测试：发/收固定字节，长度与 body 正确 |
| 2.2 | 实现协议层：将协议文档中的每种消息类型序列化为 JSON 字符串再写入 body；从 body 反序列化并解析为 Dart 对象（含 List&lt;Card&gt;） | - | 单元测试：用协议文档中的示例 JSON 往返 |
| 2.3 | 实现 TCP Socket 连接与断开（仅连接，不跑业务） | client.client connect/close | 真机/模拟器连接当前已支持 JSON 的服务端，能 connect 且无报错 |
| 2.4 | 实现「发送一条登录相关消息 + 接收一条响应」（例如：发送 cookie/用户名，接收 cookie 是否合法） | send_user_info / recv 首条 | 与现网服务端联调：Dart 发 JSON，服务端回 JSON，Dart 解析正确 |
| 2.5 | 实现配置持久化：读/写与 LiuJiaTong.json 同结构的本地配置 | core/config + dump | 写入后再读出，字段一致 |

### 阶段 3：应用层——主流程与状态（边接服务端边调）

| 步骤 | 任务 | 对应 Python | 如何验证 |
|------|------|--------------|----------|
| 3.1 | 实现完整「登录流程」：发 cookie/用户名、收 cookie 合法性、收新 cookie（若非法）、收恢复结果（若合法） | send_user_info + recv 多条 | 与现网服务端联调：新用户、带 cookie 恢复两种都走通 |
| 3.2 | 实现「等待大厅」：循环接收 users_name、users_error，直到 6 人满员 | recv_waiting_hall_info | 联调：大厅满员后能正确得到 6 个用户名 |
| 3.3 | 实现「场上信息」：收 is_player、users_name、client_player | recv_field_info | 联调：开局后 Dart 端 is_player/client_player 正确 |
| 3.4 | 实现「单轮牌局」：收 round_info（game_over、分数、牌数、出牌、手牌、now_score、now_player、head_master 等），解析为 FieldInfo/内部状态 | recv_round_info | 联调：收一轮数据，Dart 内状态与 Python 客户端一致 |
| 3.5 | 实现「出牌上报」：发 client_cards、users_played_cards[client_player]、now_score；以及「出牌心跳」：发 finished | send_player_info、send_playing_heartbeat | 联调：轮到 Dart 客户端出牌时，服务端能正确收到并推进对局 |
| 3.6 | 将上述步骤串成**主循环**：登录 → 大厅 → 场上信息 → 循环(收 round_info → 更新状态 → 若 game_over 退出 → 若轮到自己则收输入/自动出牌并发送) | client.run() | 与现网服务端完整打一局（可先用自动出牌或简单固定出牌） |
| 3.7 | 可选：心跳、断线重连、错误弹窗/日志 | - | 手动断网或停服务端，观察行为 |

### 阶段 4：表现层（Flutter UI）

| 步骤 | 任务 | 对应 Python | 如何验证 |
|------|------|--------------|----------|
| 4.1 | 登录/配置页：输入 IP、端口、用户名，保存到本地配置并触发连接 | gui_flet 登录 | 填完点连接能进主流程 |
| 4.2 | 等待大厅页：展示当前用户列表与错误信息，满 6 人后自动进入 | waiting_hall_interface | 大厅人数与名字正确 |
| 4.3 | 牌局主界面：手牌、各家出牌区、分数、当前出牌人、头科等（只读） | main_interface 展示部分 | 与 Python 客户端同局对比显示一致 |
| 4.4 | 出牌交互：选牌、确认/跳过、自动出牌开关，并调用应用层发送 | playing_handler + gui | 轮到自己时能选牌并成功发送 |
| 4.5 | 游戏结束页：展示结果（含「寻找战犯」等） | game_over_interface | 结束后显示正确 |
| 4.6 | 音效：出牌、得分等（用 audioplayers 等） | core/sound | 对应时机有声音 |

### 阶段 5：资源与多平台构建

| 步骤 | 任务 | 如何验证 |
|------|------|----------|
| 5.1 | 迁移牌面图、背景、字体、音效到 Flutter assets | 各平台能加载资源 |
| 5.2 | 配置 Android / iOS / Web / Desktop 构建与图标、启动图 | 各平台能打包并运行 |

### 建议的「边调试边迁移」节奏

1. **先完成 0.2 + 0.3**：服务端 JSON 与协议文档就绪后，Dart 侧始终按同一份协议实现，避免反复改。
2. **阶段 1 全部用单元测试验证**：不依赖服务端，方便随时跑。
3. **阶段 2 的 2.3～2.4 是第一次真联调**：建议用「仅登录」的 Dart 客户端对当前服务端，确认 4 字节头 + JSON body 无误。
4. **阶段 3 每完成 3.1～3.6 中的一步就联调一步**：例如先只做登录+大厅，再加场上信息，再加一轮 round，再加出牌，最后串成主循环。
5. **UI（阶段 4）在 3.6 主循环可用后再做**：可先用控制台/简单页面打印状态，主循环稳定后再替换为完整 Flutter 界面。

按上述顺序实现，可以做到：**协议可测、领域可测、网络与流程每步都可与现网服务端联调**，最终在 client_dart 中达到与当前 Python client 对等的跨平台客户端能力。

---

*文档版本：1.1 | 最后更新：2025-02-15*
