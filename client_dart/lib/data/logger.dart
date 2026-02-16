import 'dart:io';

import 'package:path_provider/path_provider.dart';

/// 简易文件日志（与 Python core/logger 类似）
class AppLogger {
  AppLogger._();

  static AppLogger? _instance;

  static AppLogger get instance {
    _instance ??= AppLogger._();
    return _instance!;
  }

  IOSink? _sink;
  String? _logPath;

  /// 初始化日志：写入 {name}_{时间戳}.log
  Future<void> init(String name) async {
    await close();
    final dir = await getApplicationDocumentsDirectory();
    final logDir = '${dir.path}/log';
    final logDirFile = Directory(logDir);
    if (!await logDirFile.exists()) await logDirFile.create(recursive: true);

    final timestamp = DateTime.now().toIso8601String().replaceAll(':', '-');
    _logPath = '$logDir/${name}_$timestamp.log';
    _sink = File(_logPath!).openWrite(mode: FileMode.write);
  }

  void info(String message) {
    final line = '${DateTime.now().toIso8601String()} - INFO - $message\n';
    _sink?.write(line);
    _sink?.flush();
  }

  void error(String message) {
    final line = '${DateTime.now().toIso8601String()} - ERROR - $message\n';
    _sink?.write(line);
    _sink?.flush();
  }

  String? get logPath => _logPath;

  Future<void> close() async {
    await _sink?.flush();
    await _sink?.close();
    _sink = null;
    _logPath = null;
  }
}
