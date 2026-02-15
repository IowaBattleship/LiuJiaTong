# PowerShell script - start LiuJiaTong simulation test
# Run from project root, or cd to test directory and execute

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ip = "127.0.0.1"   # local simulation, change to 192.168.x.x for LAN
$port = "8081"

Write-Host "LiuJiaTong Simulation Test" -ForegroundColor Cyan
Write-Host "  1) Full simulation (server + 6 simulated clients, auto play until game ends)"
Write-Host "  2) Server only (start clients manually in other terminals)"
Write-Host ""
$choice = Read-Host "Please choose [1/2] (default 1)"

if ([string]::IsNullOrWhiteSpace($choice)) {
    $choice = "1"
}

if ($choice -ne "1" -and $choice -ne "2") {
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

if ($choice -eq "1") {
    Write-Host "Starting 6 simulated clients (auto play)..." -ForegroundColor Cyan

    for ($i = 1; $i -le 6; $i++) {
        $userName = "sim_user_$i"
        $clientCmd = "python -m client --ip $ip --port $port --user-name $userName --mode CLI --simulate"
        Start-Process PowerShell -ArgumentList "-NoExit", "-Command", $clientCmd -WorkingDirectory $projectRoot
        Start-Sleep -Milliseconds 500  # small delay to avoid logger file conflicts
    }

    Write-Host ""
    Write-Host "Full simulation started. Check the opened terminals for game progress." -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "Server-only mode started. Please start clients manually (with or without --simulate)." -ForegroundColor Green
}
