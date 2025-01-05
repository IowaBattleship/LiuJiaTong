# PowerShell脚本

$ip = "192.168.31.214"
$port = "8080"

# 循环从1到5, 为每个用户启动一个PowerShell窗口
for ($i = 1; $i -le 5; $i++) {
    Start-Process PowerShell -ArgumentList "-NoExit", "-Command", "python ./client --ip $ip --port $port --user-name user_$i"
}

# 最后一个用户用于测试GUI模式
Start-Process PowerShell -ArgumentList "-NoExit", "-Command", "python ./client --ip $ip --port $port --user-name user_6 --mode CLI"