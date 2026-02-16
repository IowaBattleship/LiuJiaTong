import 'dart:convert';
import 'dart:io';

import 'package:liujiatong/core/models/config.dart';
import 'package:path_provider/path_provider.dart';

/// 配置持久化：读/写 LiuJiaTong.json（与 Python 格式一致）
class ConfigRepository {
  ConfigRepository({
    String? configFileName,
    String? basePath,
  })  : _configFileName = configFileName ?? 'LiuJiaTong.json',
        _basePath = basePath;

  final String _configFileName;
  final String? _basePath;

  Future<String> get _path async {
    if (_basePath != null) return '$_basePath/$_configFileName';
    final dir = await getApplicationDocumentsDirectory();
    return '${dir.path}/$_configFileName';
  }

  /// 加载配置，不存在或解析失败返回 null
  Future<Config?> load() async {
    try {
      final path = await _path;
      final file = File(path);
      if (!await file.exists()) return null;
      final content = await file.readAsString();
      final json = jsonDecode(content) as Map<String, dynamic>;
      return Config.fromJson(json);
    } catch (_) {
      return null;
    }
  }

  /// 保存配置
  Future<void> save(Config config) async {
    final path = await _path;
    final file = File(path);
    await file.writeAsString(
      const JsonEncoder.withIndent('  ').convert(config.toJson()),
      encoding: utf8,
    );
  }

  /// 删除配置文件
  Future<void> clear() async {
    try {
      final path = await _path;
      final file = File(path);
      if (await file.exists()) await file.delete();
    } catch (_) {}
  }

  /// 使用指定路径（便于测试或桌面端使用当前目录）
  static Future<Config?> loadFromPath(String path) async {
    try {
      final file = File(path);
      if (!await file.exists()) return null;
      final content = await file.readAsString();
      final json = jsonDecode(content) as Map<String, dynamic>;
      return Config.fromJson(json);
    } catch (_) {
      return null;
    }
  }

  static Future<void> saveToPath(Config config, String path) async {
    final file = File(path);
    await file.writeAsString(
      const JsonEncoder.withIndent('  ').convert(config.toJson()),
      encoding: utf8,
    );
  }
}
