import 'package:flutter_test/flutter_test.dart';
import 'package:liujiatong/core/models/config.dart';

void main() {
  group('Config', () {
    test('fromJson / toJson 与 LiuJiaTong.json 格式一致', () {
      final json = {
        'ip': '127.0.0.1',
        'port': 8888,
        'name': 'Alice',
        'cookie': 'abc123',
      };
      final config = Config.fromJson(json);
      expect(config.ip, '127.0.0.1');
      expect(config.port, 8888);
      expect(config.name, 'Alice');
      expect(config.cookie, 'abc123');
      expect(config.toJson(), json);
    });

    test('cookie 可为 null', () {
      final json = {'ip': '192.168.1.1', 'port': 9999, 'name': 'Bob'};
      final config = Config.fromJson(json);
      expect(config.cookie, null);
      expect(config.toJson()['cookie'], null);
    });

    test('port 可为 JSON 中的数字字符串', () {
      final json = {
        'ip': 'localhost',
        'port': '8080', // 某些 JSON 可能序列化为字符串
        'name': 'Test',
      };
      final config = Config.fromJson(json);
      expect(config.port, 8080);
    });

    test('equality 只比较 ip port name（与 Python 一致）', () {
      final c1 = Config(ip: 'a', port: 1, name: 'n', cookie: 'x');
      final c2 = Config(ip: 'a', port: 1, name: 'n', cookie: 'y');
      expect(c1 == c2, true);
      expect(c1.hashCode, c2.hashCode);
    });

    test('copyWith 更新 cookie', () {
      final c = Config(ip: 'a', port: 1, name: 'n', cookie: 'old');
      final c2 = c.copyWith(cookie: 'new');
      expect(c2.cookie, 'new');
      expect(c2.ip, 'a');
    });
  });
}
