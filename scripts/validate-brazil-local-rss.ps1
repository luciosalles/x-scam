$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$ConfigPath = Join-Path $ProjectRoot "config\brazil_local_rss_app_urls.json"

if (-not (Test-Path $ConfigPath)) {
  throw "Missing config file: $ConfigPath"
}

$config = Get-Content -Raw $ConfigPath | ConvertFrom-Json
$feeds = @($config.feeds)

$results = foreach ($feed in $feeds) {
  $rssUrl = [string]$feed.rss_url
  $enabled = [bool]$feed.enabled

  if (-not $enabled -or -not $rssUrl.StartsWith("http")) {
    [pscustomobject]@{
      Source = $feed.source_id
      Enabled = $enabled
      Status = "not_configured"
      Http = ""
      Detail = "rss_url empty or disabled"
    }
    continue
  }

  try {
    $response = Invoke-WebRequest -Uri $rssUrl -UseBasicParsing -TimeoutSec 12
    $body = [string]$response.Content
    $looksLikeFeed = $body -match "<rss|<feed|<item|<entry"
    [pscustomobject]@{
      Source = $feed.source_id
      Enabled = $enabled
      Status = $(if ($looksLikeFeed) { "ok" } else { "bad_content" })
      Http = $response.StatusCode
      Detail = $(if ($looksLikeFeed) { "RSS content detected" } else { "Response did not look like RSS/Atom" })
    }
  } catch {
    [pscustomobject]@{
      Source = $feed.source_id
      Enabled = $enabled
      Status = "error"
      Http = ""
      Detail = $_.Exception.Message
    }
  }
}

$results | Format-Table -AutoSize

$bad = @($results | Where-Object { $_.Enabled -and $_.Status -ne "ok" })
if ($bad.Count -gt 0) {
  exit 1
}
