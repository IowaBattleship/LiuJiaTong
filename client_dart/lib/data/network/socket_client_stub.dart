/// Web 平台占位：dart:io 的 Socket 在浏览器中不可用，connect 会抛出明确异常。
class ProtocolSocket {
  ProtocolSocket._();
  Future<void> send(dynamic value) async =>
      throw UnsupportedError('Web 不支持 TCP');
  Future<dynamic> recv() async =>
      throw UnsupportedError('Web 不支持 TCP');
  void close() {}
  bool get isClosed => true;
}

Future<ProtocolSocket> connect(String host, int port) async {
  throw UnsupportedError(
    'TCP 连接在 Web 平台不可用。请使用 Windows / macOS / Android / iOS 或桌面端运行本应用。',
  );
}
