import 'dart:convert';

import 'package:liujiatong/core/models/card.dart';

/// 将任意协议值转为 JSON 可序列化形式
dynamic toJsonSerializable(dynamic obj) {
  if (obj == null) return null;
  if (obj is bool || obj is int || obj is double) return obj;
  if (obj is String) return obj;
  if (obj is Card) return obj.toJson();
  if (obj is List) {
    return obj.map((e) => toJsonSerializable(e)).toList();
  }
  if (obj is Map) {
    return obj.map((k, v) => MapEntry(k, toJsonSerializable(v)));
  }
  return obj;
}

/// 将 JSON 解析结果转回 Dart 对象（含 Card、List<Card> 等）
dynamic fromJsonObject(dynamic obj) {
  if (obj == null) return null;
  if (obj is bool || obj is int || obj is double) return obj;
  if (obj is String) return obj;
  if (obj is List) {
    if (obj.length == 1 && obj[0] == 'F') return ['F'];
    return obj.map((e) => fromJsonObject(e)).toList();
  }
  if (obj is Map) {
    if (obj.keys.toSet().containsAll(['suit', 'value'])) {
      return Card.fromJson(Map<String, dynamic>.from(obj));
    }
    return obj.map((k, v) => MapEntry(k, fromJsonObject(v)));
  }
  return obj;
}

/// 编码一条协议消息为 UTF-8 字节
List<int> encodeMessage(dynamic value) {
  final serializable = toJsonSerializable(value);
  final jsonStr = jsonEncode(serializable);
  return utf8.encode(jsonStr);
}

/// 解码一条协议消息（UTF-8 字节 -> Dart 对象）
dynamic decodeMessage(List<int> bytes) {
  final jsonStr = utf8.decode(bytes);
  final parsed = jsonDecode(jsonStr);
  return fromJsonObject(parsed);
}
