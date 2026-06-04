$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$env:N8N_USER_FOLDER = Join-Path $ProjectRoot ".n8n"

& "$env:APPDATA\npm\n8n.cmd" start

