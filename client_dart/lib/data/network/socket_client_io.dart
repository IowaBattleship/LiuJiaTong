import 'dart:async';
import 'dart:io';

import 'package:liujiatong/data/network/protocol.dart';

/// 4 字节长度头（小端序 int32）+ JSON body 的 TCP 收发（仅 dart:io 平台）
class ProtocolSocket {
  ProtocolSocket(this._socket) {
    _buffer = [];
    _socket.listen(
      (chunk) {
        _buffer.addAll(chunk);
        _maybeCompleteRecv();
      },
      onError: (e) => _recvCompleter?.completeError(e),
      onDone: () {
        if (!(_recvCompleter?.isCompleted ?? true)) {
          _recvCompleter?.completeError(
            SocketException('Connection closed'),
          );
        }
      },
      cancelOnError: false,
    );
  }

  final Socket _socket;
  late List<int> _buffer;
  Completer<List<int>>? _recvCompleter;
  int? _recvTarget;

  void _maybeCompleteRecv() {
    if (_recvTarget != null &&
        _recvCompleter != null &&
        !_recvCompleter!.isCompleted &&
        _buffer.length >= _recvTarget!) {
      final n = _recvTarget!;
      final result = List<int>.from(_buffer.take(n));
      _buffer = _buffer.sublist(n);
      _recvTarget = null;
      _recvCompleter!.complete(result);
    }
  }

  Future<void> send(dynamic value) async {
    final body = encodeMessage(value);
    final header = _intToLittleEndianBytes(body.length);
    _socket.add([...header, ...body]);
    await _socket.flush();
  }

  Future<dynamic> recv() async {
    final headerBytes = await _readExactly(4);
    final length = _littleEndianBytesToInt(headerBytes);
    if (length < 0 || length > 10 * 1024 * 1024) {
      throw FormatException('Invalid message length: $length');
    }
    final bodyBytes = await _readExactly(length);
    return decodeMessage(bodyBytes);
  }

  Future<List<int>> _readExactly(int n) async {
    if (_buffer.length >= n) {
      final result = List<int>.from(_buffer.take(n));
      _buffer = _buffer.sublist(n);
      return result;
    }
    _recvTarget = n;
    _recvCompleter = Completer<List<int>>();
    return _recvCompleter!.future;
  }

  bool _closed = false;

  void close() {
    if (!_closed) {
      _closed = true;
      _socket.destroy();
    }
  }

  bool get isClosed => _closed;

  static List<int> _intToLittleEndianBytes(int value) {
    return [
      value & 0xff,
      (value >> 8) & 0xff,
      (value >> 16) & 0xff,
      (value >> 24) & 0xff,
    ];
  }

  static int _littleEndianBytesToInt(List<int> bytes) {
    assert(bytes.length >= 4);
    return bytes[0] |
        (bytes[1] << 8) |
        (bytes[2] << 16) |
        (bytes[3] << 24);
  }
}

Future<ProtocolSocket> connect(String host, int port) async {
  final socket = await Socket.connect(host, port);
  return ProtocolSocket(socket);
}
