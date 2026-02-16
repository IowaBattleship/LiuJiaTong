import 'package:liujiatong/application/game_controller.dart';
import 'package:liujiatong/core/models/config.dart';
import 'package:liujiatong/data/config/config_repository.dart';

/// 登录并持久化 cookie（cookie 恢复流程）
///
/// 1. 连接（含重试）
/// 2. 发送用户信息（含 cookie 恢复）
/// 3. 将更新后的 config 保存到 repo
/// 返回更新后的 Config（含新 cookie）
Future<Config> loginWithCookieRecovery(
  GameController controller,
  ConfigRepository repo, {
  int maxRetries = 10,
}) async {
  await controller.connectWithRetry(
    controller.config.ip,
    controller.config.port,
    maxRetries: maxRetries,
  );
  final updatedConfig = await controller.sendUserInfo();
  await repo.save(updatedConfig);
  return updatedConfig;
}
