$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$env:N8N_USER_FOLDER = Join-Path $ProjectRoot ".n8n"
$WorkflowPath = Join-Path $ProjectRoot "workflows\n8n-trump-tariff-alert-starter.json"

& "$env:APPDATA\npm\n8n.cmd" import:workflow --input="$WorkflowPath"

