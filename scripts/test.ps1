# PowerShell脚本 - 从项目根目录启动客户端测试

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ip = "192.168.31.63"
$port = "8081"

# 循环从1到6，为每个用户启动一个 PowerShell 窗口（CLI 模式）
# 间隔启动，避免多进程同时初始化 logger 时产生文件占用冲突
# 若需用 GUI 客户端作为其中一席，请使用独立仓库：https://github.com/BoysBoysForward/LiuJiaTong-Client
for ($i = 1; $i -le 6; $i++) {
    Start-Process PowerShell -ArgumentList "-NoExit", "-Command", "python -m client --ip $ip --port $port --user-name user_$i" -WorkingDirectory $projectRoot
    Start-Sleep -Milliseconds 500
}