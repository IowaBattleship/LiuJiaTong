# 温岭六家统

本仓库为「温岭六家统」游戏的**服务端**与**命令行（CLI）客户端**实现。六家统流行于台州温岭一带，六人游戏、四副牌共 216 张，三人一队为独家庄。

本仓库同时作为协议与逻辑核心，**支持第三方 GUI 客户端**接入；GUI 客户端项目与使用说明见另一仓库：
**[GUI 客户端仓库](https://github.com/BoysBoysForward/LiuJiaTong-Client)**

---

## 仓库内容概览

- **服务端**：多房间、多对局，可持续运行，支持断线重连（cookie）。
- **CLI 客户端**：在终端中连接服务端进行游戏，支持音效与基础交互。
- **核心与协议**：牌型规则、网络协议等，可供 GUI 或其他客户端复用。

---

## 环境要求

- **Python**：>= 3.9
- **Windows**：建议安装 `pypiwin32`（用于 Ctrl+C 等信号处理），首次运行时会提示安装。
- **终端**：需支持 ANSI 转义（彩色与闪烁等）。
  - **Windows**：建议使用 [Windows Terminal](https://apps.microsoft.com/store/detail/windows-terminal/9N0DX20HK701)，旧版 Cmd/PowerShell 可能不支持 ANSI。
  - **Linux / macOS**：一般终端即可；macOS 下若需闪烁效果，可在终端设置中开启「Blinking text」。
- **音效（可选）**：CLI 客户端会检查本机是否具备播放能力（Windows 使用 `winsound`，macOS 需 `afplay`，Linux 需 `aplay`）。若环境不满足，启动时会报错并退出，可按提示安装相应工具。

---

## 如何使用

在项目根目录下执行（确保已安装 Python 3.9+）。

### 启动服务端

```bash
# 默认监听 0.0.0.0:8080
python -m server

# 指定 IP 与端口
python -m server --ip 0.0.0.0 --port 8081

# 禁用每局随机重排玩家顺序（-s/--static）
python -m server --port 8080 -s
```

### 启动 CLI 客户端

```bash
# 使用配置文件中的 ip、port、用户名（如 LiuJiaTong.json）
python -m client

# 命令行指定连接信息
python -m client --ip 127.0.0.1 --port 8080 --user-name 玩家名

# 同机多开：禁用本地 cookie，避免互相覆盖（-n/--no-cookie）
python -m client -n

# 模拟模式：自动出牌/过牌，无需输入（-s/--simulate）
python -m client -s
```

客户端支持断线重连：本地会保存服务端下发的 cookie，再次启动时可在提示下恢复对局。

---

## 项目结构

```
LiuJiaTong/
├── core/           # 核心逻辑：牌型、规则、网络帧、音效、自动出牌策略等
├── common/         # 公共层：终端输出、牌面字符串/分数等 server 与 client 共用
├── server/         # 服务端：对局管理、玩家与观战、状态机等
├── client/         # CLI 客户端：连接、对局处理、界面与输入
├── scripts/        # 测试与脚本（如 pytest）
└── docs/           # 文档（协议、重构说明等）
```

- 协议与数据类型约定见 **`docs/protocol.md`**。

---

## 其他说明

- **多平台**：可在 Windows / Linux / macOS 上运行服务端与 CLI 客户端，注意终端与音效环境要求见上文。
- **贡献**：欢迎提交 Issue 与 Pull Request。
- **GUI 客户端**：本仓库仅包含服务端与 CLI；若需图形界面，请使用支持同一协议的 GUI 客户端，详见另一仓库。
