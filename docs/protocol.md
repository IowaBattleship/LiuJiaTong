# 六家统 客户端-服务端通信协议

本文档描述 Dart/Flutter 客户端与 Python 服务端之间的 TCP 应用层协议，供前后端分别演进时对照。

---

## 1. 连接与帧格式

- **传输层**：TCP，客户端主动连接服务端 `ip:port`。
- **编码**：UTF-8。
- **单条消息格式**：**4 字节长度头（小端序 signed int32）+ JSON body**。
  - 长度头表示 body 的字节数（不含头）。
  - body 为一条 JSON 值的 UTF-8 编码；复合类型（数组、对象）内可嵌套 Card 等约定格式。

实现参考：
- 服务端：`network/my_network_json.py`（`send_data_to_socket` / `recv_data_from_socket`）。
- 客户端：`client_dart/lib/data/network/`（`ProtocolSocket`、`encodeMessage` / `decodeMessage`）。

---

## 2. 通用数据类型

### 2.1 Card（扑克牌）

用于手牌、出牌等，JSON 对象：

| 字段   | 类型   | 说明 |
|--------|--------|------|
| `suit` | string | 花色：`"Spade"` \| `"Heart"` \| `"Club"` \| `"Diamond"` \| `""`（空串表示大小王无花色） |
| `value`| int    | 牌面：3~10 数字，11=J，12=Q，13=K，14=A，15=2，16=小王，17=大王 |

示例：`{"suit": "Spade", "value": 14}` 表示黑桃 A。

### 2.2 过牌（Skip）

某玩家本轮不出牌时，其「本轮出牌」用长度为 1 的数组且唯一元素为字符串 `"F"` 表示，即 **`["F"]`**。其他情况为该玩家本轮打出的 `Card` 数组。

---

## 3. 客户端配置（仅本地使用）

客户端配置文件名约定为 **`LiuJiaTong.json`**，与连接相关的字段用于连接服务端，不通过本协议传输。格式约定如下（前后端若读写同一格式可互认）：

| 字段    | 类型   | 说明 |
|---------|--------|------|
| `ip`    | string | 服务端地址 |
| `port`  | int    | 服务端端口 |
| `name`  | string | 用户昵称 |
| `cookie`| string \| null | 可选，断线重连用服务端下发的 cookie |

---

## 4. 消息顺序与内容

以下均为「每条消息」对应一个 **4 字节头 + 一条 JSON**，按顺序收发；同一阶段内可能循环（如大厅）或多次往返（如每轮出牌）。

### 4.1 连接建立后：登录 / 用户信息

**客户端 → 服务端**

1. **if_has_cookie**（boolean）  
   - `true`：表示带 cookie 尝试恢复；下一条为 cookie 字符串。  
   - `false`：表示无 cookie 或本次不用 cookie；不再发 cookie，服务端按新用户处理。

2. 若 `if_has_cookie === true`：**cookie**（string）。

3. 若服务端回复 cookie 不合法或未带 cookie，客户端再发：**user_name**（string），即昵称。

**服务端 → 客户端**

1. **if_valid_cookie**（boolean）  
   - `true`：cookie 有效，进入恢复流程；下一条为 `if_recovery`。  
   - `false`：cookie 无效或未提供，按新用户；客户端需再发 `user_name`，然后服务端回复新用户结果。

2. 若 `if_valid_cookie === true`：**if_recovery**（boolean）  
   - `true`：恢复成功，本连接沿用该玩家身份，登录阶段结束。  
   - `false`：该位已被占用（例如另一客户端仍在玩），连接会被服务端关闭。

3. 若 `if_valid_cookie === false` 且客户端已发 `user_name`：  
   - 若房间未满（新玩家）：**new_cookie**（string），客户端应保存用于断线重连。  
   - 若房间已满（旁观者）：**new_cookie**（null），表示无 cookie。

此后进入「等待大厅」阶段。

---

### 4.2 等待大厅（直至满 6 人）

**服务端 → 客户端**（循环，直至 `users_name.length >= 6`）

1. **users_name**（array of string）  
   当前已在房间的玩家昵称列表（按位对应 0~5，不足 6 个时列表长度 &lt; 6）。
2. **users_error**（array of boolean）  
   与 `users_name` 同下标，表示该位玩家是否处于错误/断线状态。

客户端根据这两条更新大厅 UI；当 `users_name.length >= 6` 时退出循环，进入下一阶段。

---

### 4.3 场信息（开局时一次）

**服务端 → 客户端**

1. **is_player**（boolean）  
   - `true`：本连接为玩家（可出牌）。  
   - `false`：本连接为旁观者（只收轮次信息，不出牌）。
2. **users_name**（array of string）  
   长度为 6，按出牌顺序的玩家昵称。
3. **client_player**（int）  
   本连接对应的座位号 0~5（玩家或旁观者视角对应的座位）。

---

### 4.4 轮次信息（每轮一次，由服务端推送）

**服务端 → 客户端**

1. **game_over**（int）  
   - `0`：未结束。  
   - 非 0：游戏结束（具体取值表示哪方双统等，见服务端约定）。
2. **users_score**（array of int）  
   长度为 6，各座位当前总得分。
3. **users_cards_num**（array of int）  
   长度为 6，各座位当前手牌数。
4. **users_played_cards**（array of array）  
   长度为 6；每个元素为该座位本轮已出的牌：要么 `["F"]`（过），要么 Card 对象数组。
5. 若 **game_over !== 0**：**users_cards**（array of array of Card）  
   长度为 6，各座位剩余手牌（用于结算展示）。
6. **client_cards**（array of Card）  
   本连接对应座位的当前手牌（仅玩家有意义）。
7. **now_score**（int）  
   当前轮尚未归属的分数。
8. **now_player**（int）  
   当前该出牌的座位号 0~5。
9. **head_master**（int）  
   头科座位号，未有时为 -1。

若 **game_over !== 0**，客户端据此结算并结束；否则若本连接是玩家且 **now_player === client_player**，则进入「出牌与心跳」阶段。

---

### 4.5 出牌与心跳（仅当轮到自己出牌时）

**客户端 → 服务端**

- 在思考/选牌期间，客户端**周期性**发送心跳（建议约 1 秒一次）：**finished**（boolean）`false`，表示尚未完成出牌。
- 确定出牌或过牌后，发送一次 **finished**（boolean）`true`，表示本轮出牌已提交；随后紧接三条消息：

1. **client_cards_after**（array of Card）  
   出牌后本座位的剩余手牌。
2. **played_this_round**（array）  
   本轮所出牌：过牌为 `["F"]`，否则为 Card 对象数组。
3. **now_score_after**（int）  
   本轮出牌后、尚未归属的分数（即本轮打出的分加在 `now_score` 上后的值）。

服务端据此更新状态，并在下一轮通过「轮次信息」再次推送。

---

## 5. 版本与变更

- 本文档与当前 Python 服务端（`server/game_handler.py`）及 Dart 客户端（`client_dart/lib/application/game_controller.dart`）实现一致。
- 若后续修改消息顺序、字段或 Card/Config 格式，请同步更新：
  - 服务端：`network/my_network_json.py`、`server/game_handler.py`、`core/card.py` 等；
  - 客户端：`client_dart` 内 protocol、models、game_controller 等；
  - 本文档（建议在文末增加简短变更记录）。
