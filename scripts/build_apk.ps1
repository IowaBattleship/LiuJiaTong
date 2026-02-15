# Flet APK 构建脚本 - 解决 Windows WinError 267 及模板路径问题
# 用法：在项目根目录执行 .\scripts\build_apk.ps1

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path $PSScriptRoot -Parent
$TemplateDir = Join-Path $ProjectRoot "flet-build-template"

if (-not (Test-Path $TemplateDir)) {
    Write-Host "错误: flet-build-template 不存在。请先运行:" -ForegroundColor Red
    Write-Host "  1. 使用 VPN 后执行: git clone https://github.com/flet-dev/flet-build-template.git flet-build-template" -ForegroundColor White
    Write-Host "  2. 或手动下载 https://github.com/flet-dev/flet-build-template/archive/refs/heads/main.zip" -ForegroundColor White
    Write-Host "     解压后将 flet-build-template-main 重命名为 flet-build-template，放到项目根目录" -ForegroundColor White
    exit 1
}

# 使用绝对路径传递模板，避免 Windows 相对路径导致 WinError 267
$TemplatePath = [System.IO.Path]::GetFullPath($TemplateDir)
Write-Host "使用模板: $TemplatePath" -ForegroundColor Cyan

Push-Location $ProjectRoot
try {
    # --clear-cache 强制重新创建 build/flutter，避免 cwd 指向不存在目录
    flet build apk --template "$TemplatePath" --clear-cache
} finally {
    Pop-Location
}
