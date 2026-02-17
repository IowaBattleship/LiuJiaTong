#!/bin/bash

# 定义主机IP和端口
IP="192.168.31.214"
PORT="8080"

# 使用gnome-terminal或者xterm来打开新的终端窗口
# 根据您的系统安装的终端模拟器，您可能需要更换这里的命令
TERM="gnome-terminal" # 或者使用 "xterm"

# 循环从1到6，为每个用户启动一个终端
for i in {1..6}
do
    $TERM -- bash -c "python ./client --ip $IP --port $PORT --user-name user_$i; exec bash"
done