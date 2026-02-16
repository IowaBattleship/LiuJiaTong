/// 配置文件文件名（与 Python LiuJiaTong.json 一致）
const String configFileName = 'LiuJiaTong.json';

/// 客户端配置模型
class Config {
  Config({
    required this.ip,
    required this.port,
    required this.name,
    this.cookie,
  });

  final String ip;
  final int port;
  final String name;
  final String? cookie; // 用于断线重连

  /// 从 JSON 反序列化（与 LiuJiaTong.json 格式一致）
  factory Config.fromJson(Map<String, dynamic> json) {
    return Config(
      ip: json['ip'] as String,
      port: json['port'] is int ? json['port'] : int.parse(json['port'].toString()),
      name: json['name'] as String,
      cookie: json['cookie'] as String?,
    );
  }

  /// 序列化为 JSON
  Map<String, dynamic> toJson() => {
        'ip': ip,
        'port': port,
        'name': name,
        'cookie': cookie,
      };

  /// 拷贝并更新字段（用于 updateCookie 等）
  Config copyWith({
    String? ip,
    int? port,
    String? name,
    String? cookie,
  }) {
    return Config(
      ip: ip ?? this.ip,
      port: port ?? this.port,
      name: name ?? this.name,
      cookie: cookie ?? this.cookie,
    );
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is Config &&
        ip == other.ip &&
        port == other.port &&
        name == other.name;
  }

  @override
  int get hashCode => Object.hash(ip, port, name);
}
