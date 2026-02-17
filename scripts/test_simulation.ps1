# PowerShell script - start LiuJiaTong simulation test
# Run from project root, or cd to test directory and execute

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ip = "192.168.31.63"   # local simulation, change to 192.168.x.x for LAN
$port = "8081"

Write-Host "LiuJiaTong Simulation Test" -ForegroundColor Cyan
Write-Host "  1) Full simulation (server + 6 simulated CLI clients, auto play until game ends)"
Write-Host "  2) Server only (start clients manually in other terminals)"
Write-Host "  3) Mixed: server + 5 simulated CLI clients (for testing with 1 Dart client)"
Write-Host ""
$choice = Read-Host "Please choose [1/2/3] (default 1)"

if ([string]::IsNullOrWhiteSpace($choice)) {
    $choice = "1"
}

if ($choice -ne "1" -and $choice -ne "2" -and $choice -ne "3") {
    Write-Host "Invalid choice, use default option 1 (full simulation)." -ForegroundColor Yellow
    $choice = "1"
}

Write-Host ""
Write-Host "Using IP: $ip, Port: $port" -ForegroundColor Green
Write-Host ""

# Start server in a new PowerShell window
$serverCmd = "python -m server --ip $ip --port $port"
Write-Host "Starting server..." -ForegroundColor Cyan
Start-Process PowerShell -ArgumentList "-NoExit", "-Command", $serverCmd -WorkingDirectory $projectRoot

if ($choice -eq "1" -or $choice -eq "3") {
    $clientCount = if ($choice -eq "1") { 6 } else { 5 }
    Write-Host "Starting $clientCount simulated CLI clients (auto play)..." -ForegroundColor Cyan

    for ($i = 1; $i -le $clientCount; $i++) {
        $userName = "sim_user_$i"
        $clientCmd = "python -m client --ip $ip --port $port --user-name $userName --simulate"
        Start-Process PowerShell -ArgumentList "-NoExit", "-Command", $clientCmd -WorkingDirectory $projectRoot
        Start-Sleep -Milliseconds 500  # small delay to avoid logger file conflicts
    }

    Write-Host ""
    if ($choice -eq "1") {
        Write-Host "Full simulation started (server + 6 simulated CLI clients)." -ForegroundColor Green
    } else {
        Write-Host "Mixed simulation started (server + 5 simulated CLI clients)." -ForegroundColor Green
        Write-Host ("Please start the Dart/Flutter client manually (connect to {0}:{1}) as the 6th player." -f $ip, $port) -ForegroundColor Yellow
    }
} else {
    Write-Host ""
    Write-Host "Server-only mode started. Please start clients manually (with or without --simulate)." -ForegroundColor Green
}
