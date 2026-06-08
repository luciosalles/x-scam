$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$powershell = "powershell"
$script = Join-Path $root "scripts\profit_rtd_stream.ps1"

Write-Host "Starting Profit RTD stream..."
& $powershell -NoProfile -ExecutionPolicy Bypass -File $script
