# 测试说明

## 领域层单元测试（阶段 1）

| 模块 | 测试文件 | 覆盖内容 |
|------|----------|----------|
| Card / Suits | `core/models/card_test.dart` | 构造、equality、fromJson/toJson、displayStr、compareTo |
| Config | `core/models/config_test.dart` | fromJson/toJson、cookie 可空、equality、copyWith |
| FieldInfo | `core/models/field_info_test.dart` | 构造与字段 |
| playing_rules | `core/rules/playing_rules_test.dart` | 单张/对子/三张/顺子/炸弹、首出/跟牌、validateUserInput、分数、手牌不足 |
| card_utils | `core/utils/card_utils_test.dart` | strToInt/intToStr、分数、getCardCount、lastPlayed、队伍、drawCards、calculateTeamScores |
| auto_play/strategy | `core/auto_play/strategy_test.dart` | 空手牌、首出单张/对子、跟牌压过、无牌可出 |

## 数据层单元测试（阶段 2）

| 模块 | 测试文件 | 覆盖内容 |
|------|----------|----------|
| protocol | `data/network/protocol_test.dart` | encode/decode bool、int、string、null、Card、List&lt;Card&gt;、["F"] |
| config_repository | `data/config/config_repository_test.dart` | saveToPath/loadFromPath 往返、文件不存在、非法 JSON |

## 应用层测试（阶段 3）

| 模块 | 测试文件 | 覆盖内容 |
|------|----------|----------|
| game_controller | `application/game_controller_test.dart` | 初始状态、getFieldInfo、removeCards、getLastPlayer、心跳 |
| play_result | `application/play_result_test.dart` | PlayCards、PlaySkip |

运行全部测试：`flutter test`
