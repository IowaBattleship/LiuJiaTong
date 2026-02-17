"""
JSON 协议网络模块：与 my_network.py 接口兼容，使用 JSON 替代 pickle。
供 Dart/Flutter 客户端与 Python 服务端联调使用。

使用方式：在 game_handler 中改为
    from network.my_network_json import send_data_to_socket, recv_data_from_socket
"""
import json
import struct
from socket import socket
from socketserver import ThreadingTCPServer

try:
    from core.card import Card
    from core.card import Suits
except ImportError:
    Card = None
    Suits = None

class ReusableTCPServer(ThreadingTCPServer):
    allow_reuse_address = True
    allow_reuse_port = True


def _to_json_serializable(obj):
    """将 Python 对象转换为 JSON 可序列化形式。"""
    if obj is None:
        return None
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, int):
        return obj
    if isinstance(obj, str):
        return obj
    if hasattr(obj, 'to_dict') and callable(getattr(obj, 'to_dict')):
        # Card 等有 to_dict 方法的对象
        return obj.to_dict()
    if isinstance(obj, list):
        return [_to_json_serializable(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _to_json_serializable(v) for k, v in obj.items()}
    return obj


def _from_json_object(obj):
    """将 JSON 解析后的对象转换回 Python 原生对象（含 Card）。"""
    if obj is None:
        return None
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, int):
        return obj
    if isinstance(obj, str):
        return obj
    if isinstance(obj, list):
        # 特殊：["F"] 表示跳过，保持为 ['F']
        if obj == ["F"]:
            return ["F"]
        return [_from_json_object(item) for item in obj]
    if isinstance(obj, dict):
        # 若为 Card 格式：{"suit": "...", "value": N}
        if set(obj.keys()) == {"suit", "value"} and Card is not None:
            return Card.from_dict(obj)
        return {k: _from_json_object(v) for k, v in obj.items()}
    return obj


def send_data_to_socket(data, sock: socket) -> None:
    """
    发送数据，格式：4 字节长度头（小端 int）+ JSON 编码的 body。
    与 my_network.py 中 send_data_to_socket 接口一致，可直接替换。
    """
    serializable = _to_json_serializable(data)
    body = json.dumps(serializable, ensure_ascii=False).encode("utf-8")
    header = struct.pack("<i", len(body))  # 小端序，与 Python struct 'i' 在 x86 上一致
    sock.sendall(header)
    sock.sendall(body)


def recv_data_from_socket(sock: socket):
    """
    接收数据，格式：先读 4 字节得长度，再读 body 并 JSON 解析。
    自动将 Card 格式的 dict 转回 Card 对象。
    与 my_network.py 中 recv_data_from_socket 接口一致，可直接替换。
    """
    HEADER_LEN = 4
    header_bytes = sock.recv(HEADER_LEN)
    if len(header_bytes) < HEADER_LEN:
        raise ConnectionError(f"Connection closed: expected {HEADER_LEN} header bytes, got {len(header_bytes)}")
    body_len = struct.unpack("<i", header_bytes)[0]
    if body_len < 0 or body_len > 1024 * 1024 * 10:  # 最大 10MB
        raise ValueError(f"Invalid body length: {body_len}")

    body_bytes = b""
    while len(body_bytes) < body_len:
        chunk = sock.recv(body_len - len(body_bytes))
        if not chunk:
            raise ConnectionError("Connection closed while reading body")
        body_bytes += chunk

    parsed = json.loads(body_bytes.decode("utf-8"))
    return _from_json_object(parsed)
