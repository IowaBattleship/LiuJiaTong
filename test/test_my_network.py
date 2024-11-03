import unittest
import os
import sys
import socket
import time
import threading

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.my_network import send_data_to_socket, recv_data_from_socket

def start_server(host, port, server_socket):
    server_socket.bind((host, port))
    server_socket.listen(1)
    print("Server is listening on", host, port)
    conn, addr = server_socket.accept()
    print("Connection from", addr)
    return conn

class TestNetwork(unittest.TestCase):
    def test_send_int_to_socket(self):
        # 创建 socket A 和 B
        socket_a = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket_b = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # 定义服务器地址和端口
        host = 'localhost'
        port = 9999

        # 启动服务器线程
        server_thread = threading.Thread(target=start_server, args=(host, port, socket_b))
        server_thread.daemon = True
        server_thread.start()

        # 给服务器一点时间来启动
        time.sleep(0.1)

        # 客户端连接到服务器
        socket_a.connect((host, port))

        # 发送数据
        print("Sending data: 123")
        send_data_to_socket(123, socket_a)

        # 接收数据
        print("Receiving data...")
        received_data = recv_data_from_socket(socket_b)
        self.assertEqual(123, int(received_data))
        print("Received data:", received_data)

        # 关闭 socket
        socket_a.close()
        socket_b.close()

if __name__ == '__main__':
    unittest.main()