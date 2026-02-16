import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:liujiatong/core/models/config.dart';
import 'package:liujiatong/data/config/config_repository.dart';

void main() {
  group('ConfigRepository', () {
    late String tempDir;

    setUp(() {
      tempDir = Directory.systemTemp.createTempSync().path;
    });

    tearDown(() {
      try {
        Directory(tempDir).deleteSync(recursive: true);
      } catch (_) {}
    });

    test('saveToPath / loadFromPath 往返', () async {
      final config = Config(
        ip: '127.0.0.1',
        port: 8888,
        name: 'Test',
        cookie: 'abc123',
      );
      final path = '$tempDir/test_config.json';
      await ConfigRepository.saveToPath(config, path);
      final loaded = await ConfigRepository.loadFromPath(path);
      expect(loaded, isNotNull);
      expect(loaded!.ip, config.ip);
      expect(loaded.port, config.port);
      expect(loaded.name, config.name);
      expect(loaded.cookie, config.cookie);
    });

    test('loadFromPath 文件不存在返回 null', () async {
      final loaded = await ConfigRepository.loadFromPath('$tempDir/nonexistent.json');
      expect(loaded, isNull);
    });

    test('loadFromPath 非法 JSON 返回 null', () async {
      final path = '$tempDir/bad.json';
      await File(path).writeAsString('{ invalid }');
      final loaded = await ConfigRepository.loadFromPath(path);
      expect(loaded, isNull);
    });
  });
}
