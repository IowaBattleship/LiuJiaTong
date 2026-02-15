# PowerShell脚本 - 从项目根目录启动客户端测试

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ip = "192.168.31.63"
$port = "8081"

# 循环从1到5，为每个用户启动一个PowerShell窗口（CLI 模式）
# 间隔启动，避免多进程同时初始化 logger 时产生文件占用冲突
for ($i = 1; $i -le 5; $i++) {
    Start-Process PowerShell -ArgumentList "-NoExit", "-Command", "python -m client --ip $ip --port $port --user-name user_$i" -WorkingDirectory $projectRoot
    Start-Sleep -Milliseconds 500
}

# 最后一个用户用于测试 Flet GUI 模式（client/src/main.py 入口，含开始界面）
Start-Sleep -Milliseconds 500
Start-Process PowerShell -ArgumentList "-NoExit", "-Command", "python -m client --ip $ip --port $port --user-name Redhat --mode GUI_KIVY" -WorkingDirectory $projectRoot