$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$results = New-Object System.Collections.Generic.List[object]

function Add-Result {
  param(
    [string]$Name,
    [bool]$Ok,
    [string]$Detail
  )
  $results.Add([pscustomobject]@{
    Check = $Name
    Status = $(if ($Ok) { "ok" } else { "fail" })
    Detail = $Detail
  })
}

try {
  Get-ChildItem -Path (Join-Path $ProjectRoot 'workflows\*.json') | ForEach-Object {
    Get-Content -Raw $_.FullName | ConvertFrom-Json | Out-Null
  }
  Add-Result "workflow-json" $true "all workflow JSON files parsed"
} catch {
  Add-Result "workflow-json" $false $_.Exception.Message
}

try {
  Get-ChildItem -Path (Join-Path $ProjectRoot 'config\*.json') | ForEach-Object {
    Get-Content -Raw $_.FullName | ConvertFrom-Json | Out-Null
  }
  Add-Result "config-json" $true "all config JSON files parsed"
} catch {
  Add-Result "config-json" $false $_.Exception.Message
}

try {
  $health = Invoke-RestMethod -Uri "http://127.0.0.1:8787/healthz" -TimeoutSec 5
  Add-Result "local-service" ([bool]$health.ok) ("healthz=" + $health.ok)
} catch {
  Add-Result "local-service" $false $_.Exception.Message
}

try {
  $dashboard = (Invoke-WebRequest -Uri "http://127.0.0.1:8787/dashboard" -UseBasicParsing -TimeoutSec 10).Content
  $ok = $dashboard.Contains("Alert Dashboard") -and $dashboard.Contains("Brasil Local") -and $dashboard.Contains("Leitura WIN")
  Add-Result "dashboard" $ok "dashboard content check"
} catch {
  Add-Result "dashboard" $false $_.Exception.Message
}

try {
  $sources = Invoke-RestMethod -Uri "http://127.0.0.1:8787/api/source-health"
  $count = @($sources.sources).Count
  Add-Result "source-health" ($count -ge 7) ("sources=" + $count)
} catch {
  Add-Result "source-health" $false $_.Exception.Message
}

try {
  $rssConfig = Get-Content -Raw (Join-Path $ProjectRoot 'config\brazil_local_rss_app_urls.json') | ConvertFrom-Json
  $enabled = @($rssConfig.feeds | Where-Object { $_.enabled -and $_.rss_url })
  Add-Result "brazil-local-rss-config" $true ("enabled=" + $enabled.Count)
} catch {
  Add-Result "brazil-local-rss-config" $false $_.Exception.Message
}

$results | Format-Table -AutoSize

$failed = @($results | Where-Object { $_.Status -eq 'fail' })
if ($failed.Count -gt 0) {
  exit 1
}
