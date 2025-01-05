import unittest
import os
import sys
import socket
import time
import threading
import queue

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from my_network import send_data_to_socket, recv_data_from_socket
from card import HEART_JACK

def start_server(host, port, server_socket, conn_queue):
    server_socket.bind((host, port))
    server_socket.listen(1)
    print("Server is listening on", host, port)
    conn, addr = server_socket.accept()
    print("Connection from", addr)
    conn_queue.put(conn)  # 将连接套接字放入队列

class TestNetwork(unittest.TestCase):
    def set_up(self, port: int):
        # 创建服务器套接字
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # 创建客户端套接字
        socket_a = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # 定义服务器地址和端口
        host = 'localhost'

        # 使用队列来传递连接套接字
        conn_queue = queue.Queue()

        # 启动服务器线程
        server_thread = threading.Thread(target=start_server, args=(host, port, server_socket, conn_queue))
        server_thread.daemon = True
        server_thread.start()

        # 给服务器一点时间来启动
        time.sleep(0.1)

        # 客户端连接到服务器
        socket_a.connect((host, port))

        conn = conn_queue.get()  # 从队列中获取连接套接字
        return server_socket, socket_a, conn

    def tear_down(self, server_socket, socket_a, conn):
        # 关闭套接字
        socket_a.close()
        conn.close()  # 关闭连接套接字
        server_socket.close()  # 关闭服务器套接字

    def test_send_int_to_socket(self):
        server_socket, socket_a, conn = self.set_up(54321)

        # 发送数据
        print("Sending data: 123")
        send_data_to_socket(123, socket_a)

        # 接收数据
        print("Receiving data...")
        received_data = recv_data_from_socket(conn)
        self.assertEqual(123, int(received_data))
        print("Received data:", received_data)

        # 关闭套接字
        self.tear_down(server_socket, socket_a, conn)
    
    def test_send_card_to_socket(self):
        server_socket, socket_a, conn = self.set_up(54322)

        # 发送数据
        print(f"Sending data: {HEART_JACK}")
        send_data_to_socket(HEART_JACK, socket_a)

        # 接收数据
        print("Receiving data...")
        received_data = recv_data_from_socket(conn)
        self.assertEqual(HEART_JACK.suit, received_data.suit)
        self.assertEqual(HEART_JACK.value, received_data.value)
        print("Received data:", received_data)

        # 关闭套接字
        self.tear_down(server_socket, socket_a, conn)

if __name__ == '__main__':
    unittest.main()