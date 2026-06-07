$ErrorActionPreference = "Stop"

$env:N8N_USER_FOLDER = $env:USERPROFILE

& "$env:APPDATA\npm\n8n.cmd" start
