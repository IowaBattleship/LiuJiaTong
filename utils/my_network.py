import struct
from socketserver import ThreadingTCPServer
import pickle
from socket import socket
import logger

# 发送数据，数据组成是 header(4字节) + data
# header以c++的int类型发送，所以是4字节
def send_data_to_socket(data, socket: socket):
    logger.info(f"send_data_to_socket")
    # data = json.dumps(data).encode()
    data = pickle.dumps(data) # 11/03/2024: 使用pickle以支持自定义类的序列化
    header = struct.pack('i', len(data))
    socket.sendall(header)
    socket.sendall(data)

# 接收数据，数据组成是 header(4字节) + data
# header 为数据长度，header的最大值是4字节能表示的最大值即2^32-1
# 因此data中最多放置长为2^32-1=4294967295字节的数据
def recv_data_from_socket(socket: socket):
    logger.info(f"recv_data_from_socket")
    HEADER_LEN = 4
    header = socket.recv(HEADER_LEN)
    header = struct.unpack('i', header)[0]
    data = socket.recv(header)
    # data = json.loads(data.decode())
    data = pickle.loads(data) # 11/03/2024: 使用pickle以支持自定义类的序列化
    return data

class ReusableTCPServer(ThreadingTCPServer):
    allow_reuse_address = True
    allow_reuse_port = True