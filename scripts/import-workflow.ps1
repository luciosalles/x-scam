$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$env:N8N_USER_FOLDER = $env:USERPROFILE

$WorkflowPaths = @(
  "workflows\n8n-telegram-smoke-test.json",
  "workflows\n8n-trump-tariff-alert-starter.json",
  "workflows\n8n-market-reaction-engine-starter.json",
  "workflows\n8n-brazil-local-alert-starter.json",
  "workflows\n8n-bcb-direct-macro-starter.json"
)

foreach ($RelativePath in $WorkflowPaths) {
  $WorkflowPath = Join-Path $ProjectRoot $RelativePath
  & "$env:APPDATA\npm\n8n.cmd" import:workflow --input="$WorkflowPath"
}
