// 桌面/移动端使用 dart:io 的 TCP；Web 使用占位实现并抛出明确错误。
export 'socket_client_stub.dart'
    if (dart.library.io) 'socket_client_io.dart';
