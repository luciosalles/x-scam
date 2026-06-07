$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$DbPath = Join-Path $ProjectRoot "data\\alerts.sqlite"
$Port = 8787

$existing = Get-CimInstance Win32_Process | Where-Object {
  $_.Name -eq "python.exe" -and $_.CommandLine -like "*alert_dedupe_service.py*"
} | Select-Object -First 1

if (-not $existing) {
  Start-Process -FilePath "python" -ArgumentList @(
    (Join-Path $ProjectRoot "scripts\\alert_dedupe_service.py"),
    $DbPath,
    $Port
  ) -WorkingDirectory $ProjectRoot -WindowStyle Hidden
  Start-Sleep -Seconds 2
}

try {
  (Invoke-WebRequest -Uri "http://127.0.0.1:$Port/healthz" -UseBasicParsing -TimeoutSec 5).Content
} catch {
  throw "Alert dedupe service did not start correctly."
}
