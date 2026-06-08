$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$configPath = Join-Path $root "config\profit_rtd_config.json"
$dataRoot = Join-Path $root "data\rtd"
$statePath = Join-Path $dataRoot "state.json"
$snapshotPath = Join-Path $dataRoot "snapshot.json"
$discoveryPath = Join-Path $dataRoot "discovery.json"
$smokePath = Join-Path $dataRoot "smoke_test.json"

New-Item -ItemType Directory -Force -Path $dataRoot | Out-Null

$cfg = Get-Content $configPath -Raw | ConvertFrom-Json
$progIds = @($cfg.candidate_prog_ids)
if (-not $progIds -or $progIds.Count -eq 0) {
    $progIds = @($cfg.prog_id)
}

$env:LIB = ""

Add-Type -TypeDefinition @"
using System;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;

[ComImport]
[TypeLibType((short)0x1040)]
[Guid("A43788C1-D91B-11D3-8F39-00C04F3651B8")]
[InterfaceType(ComInterfaceType.InterfaceIsDual)]
public interface IRTDUpdateEvent
{
    [MethodImpl(MethodImplOptions.InternalCall, MethodCodeType = MethodCodeType.Runtime), DispId(10), PreserveSig]
    void UpdateNotify();
    [DispId(11)]
    int HeartbeatInterval { [MethodImpl(MethodImplOptions.InternalCall, MethodCodeType = MethodCodeType.Runtime), DispId(11)] get; [param: In] [MethodImpl(MethodImplOptions.InternalCall, MethodCodeType = MethodCodeType.Runtime), DispId(11)] set; }
    [MethodImpl(MethodImplOptions.InternalCall, MethodCodeType = MethodCodeType.Runtime), DispId(12)]
    void Disconnect();
}

public class RtdCallback : IRTDUpdateEvent
{
    public int UpdateCount = 0;
    public int HeartbeatInterval { get; set; }
    public RtdCallback() { HeartbeatInterval = 2; }
    public void UpdateNotify() { UpdateCount++; }
    public void Disconnect() { }
}
"@

function Write-JsonFile([string]$Path, [object]$Payload) {
    $json = $Payload | ConvertTo-Json -Depth 12
    $dir = Split-Path -Parent $Path
    $tmp = Join-Path $dir ([System.IO.Path]::GetRandomFileName() + ".tmp")
    [System.IO.File]::WriteAllText($tmp, $json, (New-Object System.Text.UTF8Encoding($false)))
    Move-Item -LiteralPath $tmp -Destination $Path -Force
}

function NowTs {
    [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
}

function NowIso {
    (Get-Date).ToString('s')
}

function Normalize-Value($Value) {
    if ($null -eq $Value) { return $null }
    if ($Value -is [string]) {
        $t = $Value.Trim()
        if (-not $t) { return $null }
        if ($t.ToUpperInvariant() -in @('NONE','NULL','NAN','#N/A','ERRO','ERROR')) { return $null }
        $num = 0.0
        if ([double]::TryParse($t.Replace(',','.'), [ref]$num)) { return $num }
        return $t
    }
    return $Value
}

function Get-Prop($Obj, [string]$Name, $Default = $null) {
    try {
        if ($null -eq $Obj) { return $Default }
        $p = $Obj.PSObject.Properties[$Name]
        if ($null -eq $p) { return $Default }
        if ($null -eq $p.Value) { return $Default }
        return $p.Value
    } catch { return $Default }
}

$server = $null
$connected = $false
$lastError = ""
$callback = New-Object RtdCallback
$topicMap = @{}
$cache = @{}
$recentTicks = New-Object System.Collections.Generic.List[object]
$symbolStats = @{}
$priceHistory = @{}
$indicatorRobots = @{}
$timeframeState = @{}
$discovery = New-Object System.Collections.Generic.List[object]
$startedAt = [double](NowTs)
$totalUpdates = 0
$totalTicks = 0
$lastFlush = [double](NowTs)
$lastPlot = [double](NowTs)

function Get-TopicId([string]$symbol, [string]$field) {
    $key = "$symbol|$field"
    if (-not $topicMap.ContainsKey($key)) {
        $topicMap[$key] = [int]$cfg.topic_id_start + $topicMap.Count
    }
    return [int]$topicMap[$key]
}

function Write-State([string]$Status) {
    $payload = @{
        updated_at = (NowTs)
        updated_at_iso = (NowIso)
        status = $Status
        connected = $connected
        prog_id = $cfg.prog_id
        candidate_prog_ids = @($progIds)
        started_at = $startedAt
        last_error = $lastError
        symbols = @($cfg.symbols)
        fields = @($cfg.fields)
        topic_count = $topicMap.Count
        total_updates = $totalUpdates
        total_ticks = $totalTicks
        buffer_size = $recentTicks.Count
        chunk_buffer_size = $recentTicks.Count
        recent_parquet = (Join-Path $dataRoot "latest_ticks.parquet")
        plot_path = (Join-Path $dataRoot "flow_overview.png")
        symbol_stats = $symbolStats
        indicator_robots = $indicatorRobots
        timeframe_state = $timeframeState
    }
    Write-JsonFile $statePath $payload
}

function Write-Snapshot {
    $lastTicks = @($recentTicks | Select-Object -Last 120)
    $payload = @{
        updated_at = (NowTs)
        updated_at_iso = (NowIso)
        symbols = $symbolStats
        indicator_robots = $indicatorRobots
        timeframe_state = $timeframeState
        last_ticks = $lastTicks
        buffer_size = $recentTicks.Count
        total_ticks = $totalTicks
    }
    Write-JsonFile $snapshotPath $payload
}

function Write-Discovery([string]$Status) {
    $payload = @{
        updated_at = (NowTs)
        updated_at_iso = (NowIso)
        status = $Status
        connected = $connected
        prog_id = $cfg.prog_id
        valid_results = @($discovery.ToArray())
        query_error_count = 0
        query_errors = @()
    }
    Write-JsonFile $discoveryPath $payload
}

function Ensure-IndicatorRobot([string]$Symbol) {
    if (-not $indicatorRobots.ContainsKey($Symbol)) {
        $indicatorRobots[$Symbol] = [ordered]@{
            symbol = $Symbol
            trend = "aguardando"
            momentum = "aguardando"
            strength = 0
            score = 0
            price = $null
            ema_fast = $null
            ema_slow = $null
            last_update = 0
            notes = ""
        }
    }
    return $indicatorRobots[$Symbol]
}

function Ensure-TimeframeState([string]$Symbol) {
    if (-not $timeframeState.ContainsKey($Symbol)) {
        $timeframeState[$Symbol] = [ordered]@{
            symbol = $Symbol
            first_seen_ts = 0
            session_anchor = $null
            week_anchor = $null
            last_price = $null
            minute_closes = New-Object System.Collections.Generic.List[object]
            windows = [ordered]@{
                moment = [ordered]@{ label = "neutro"; pct = 0.0 }
                min15 = [ordered]@{ label = "neutro"; pct = 0.0 }
                day = [ordered]@{ label = "neutro"; pct = 0.0 }
                session = [ordered]@{ label = "neutro"; pct = 0.0 }
                week = [ordered]@{ label = "neutro"; pct = 0.0 }
            }
            updated_at = 0
        }
    }
    return $timeframeState[$Symbol]
}

function Get-WindowLabel([double]$Pct) {
    if ($Pct -ge 0.25) { return "alta forte" }
    if ($Pct -ge 0.05) { return "alta" }
    if ($Pct -le -0.25) { return "baixa forte" }
    if ($Pct -le -0.05) { return "baixa" }
    return "neutro"
}

function Get-WindowChangePct($Series, [int]$Minutes) {
    if ($null -eq $Series -or $Series.Count -lt 2) { return 0.0 }
    $lastPoint = $Series[$Series.Count - 1]
    $targetTs = [int64]$lastPoint.timestamp - ($Minutes * 60)
    $basePoint = $Series[0]
    for ($i = $Series.Count - 1; $i -ge 0; $i--) {
        if ([int64]$Series[$i].timestamp -le $targetTs) {
            $basePoint = $Series[$i]
            break
        }
    }
    $start = [double]$basePoint.value
    $end = [double]$lastPoint.value
    if ($start -eq 0) { return 0.0 }
    return [Math]::Round((($end - $start) / $start) * 100.0, 3)
}

function Update-TimeframeState([string]$Symbol, [double]$Price, [int64]$Timestamp) {
    $frame = Ensure-TimeframeState $Symbol
    if (-not $frame.first_seen_ts) {
        $frame.first_seen_ts = $Timestamp
    }
    if ($null -eq $frame.session_anchor) {
        $frame.session_anchor = $Price
    }
    if ($null -eq $frame.week_anchor) {
        $frame.week_anchor = $Price
    }
    $frame.last_price = $Price
    $frame.updated_at = $Timestamp

    $minuteBucket = $frame.minute_closes
    $minuteKey = [Math]::Floor($Timestamp / 60)
    if ($minuteBucket.Count -gt 0 -and [int64]$minuteBucket[$minuteBucket.Count - 1].minute_key -eq $minuteKey) {
        $minuteBucket[$minuteBucket.Count - 1].value = $Price
        $minuteBucket[$minuteBucket.Count - 1].timestamp = $Timestamp
    } else {
        $minuteBucket.Add([ordered]@{
            minute_key = $minuteKey
            timestamp = $Timestamp
            value = $Price
        })
    }
    while ($minuteBucket.Count -gt 960) {
        $minuteBucket.RemoveAt(0)
    }

    $momentumPct = 0.0
    if ($priceHistory.ContainsKey($Symbol)) {
        $m = Get-MomentumPct $priceHistory[$Symbol] 5
        if ($null -ne $m) { $momentumPct = [double]$m }
    }
    $min15Pct = Get-WindowChangePct $minuteBucket 15
    $sessionPct = 0.0
    if ($frame.session_anchor -ne 0 -and $null -ne $frame.session_anchor) {
        $sessionPct = [Math]::Round((($Price - [double]$frame.session_anchor) / [double]$frame.session_anchor) * 100.0, 3)
    }
    $weekPct = 0.0
    if ($frame.week_anchor -ne 0 -and $null -ne $frame.week_anchor) {
        $weekPct = [Math]::Round((($Price - [double]$frame.week_anchor) / [double]$frame.week_anchor) * 100.0, 3)
    }
    $dayPct = 0.0
    if ($symbolStats.ContainsKey($Symbol)) {
        $stat = $symbolStats[$Symbol]
        if ($null -ne $stat.day_open -and [double]$stat.day_open -ne 0) {
            $dayPct = [Math]::Round((($Price - [double]$stat.day_open) / [double]$stat.day_open) * 100.0, 3)
        } elseif ($null -ne $stat.last_daily_change) {
            $dayPct = [Math]::Round([double]$stat.last_daily_change, 3)
        }
    }

    $frame.windows.moment = [ordered]@{ label = (Get-WindowLabel $momentumPct); pct = $momentumPct }
    $frame.windows.min15 = [ordered]@{ label = (Get-WindowLabel $min15Pct); pct = $min15Pct }
    $frame.windows.day = [ordered]@{ label = (Get-WindowLabel $dayPct); pct = $dayPct }
    $frame.windows.session = [ordered]@{ label = (Get-WindowLabel $sessionPct); pct = $sessionPct }
    $frame.windows.week = [ordered]@{ label = (Get-WindowLabel $weekPct); pct = $weekPct }
}

function Trim-RecentTicks {
    $limit = [int](Get-Prop $cfg "rolling_tick_limit" 10000)
    while ($recentTicks.Count -gt $limit) {
        $recentTicks.RemoveAt(0)
    }
}

function Ensure-SymbolStat([string]$Symbol) {
    if (-not $symbolStats.ContainsKey($Symbol)) {
        $symbolStats[$Symbol] = [ordered]@{
            symbol = $Symbol
            last_price = $null
            last_bid = $null
            last_ask = $null
            last_volume = $null
            last_daily_change = $null
            day_open = $null
            day_high = $null
            day_low = $null
            trade_date = $null
            trade_time = $null
            expiry_date = $null
            updates = 0
            tick_frequency = 0.0
            last_update = 0.0
            direction_bias = "flat"
        }
    }
    return $symbolStats[$Symbol]
}

function Add-PricePoint([string]$Symbol, $Value, [int64]$Timestamp) {
    if ($null -eq $Value) { return }
    if (-not ($Value -is [double] -or $Value -is [int] -or $Value -is [decimal])) { return }
    if (-not $priceHistory.ContainsKey($Symbol)) {
        $priceHistory[$Symbol] = New-Object System.Collections.Generic.List[object]
    }
    $series = $priceHistory[$Symbol]
    $series.Add([ordered]@{
        timestamp = $Timestamp
        value = [double]$Value
    })
    while ($series.Count -gt 120) {
        $series.RemoveAt(0)
    }
}

function Get-EMA($Series, [int]$Period) {
    if ($null -eq $Series -or $Series.Count -lt 2) { return $null }
    $multiplier = 2.0 / ([double]$Period + 1.0)
    $ema = [double]$Series[0].value
    for ($i = 1; $i -lt $Series.Count; $i++) {
        $price = [double]$Series[$i].value
        $ema = (($price - $ema) * $multiplier) + $ema
    }
    return [Math]::Round($ema, 5)
}

function Get-MomentumPct($Series, [int]$Window = 5) {
    if ($null -eq $Series -or $Series.Count -lt 2) { return $null }
    $fromIndex = [Math]::Max(0, $Series.Count - 1 - $Window)
    $start = [double]$Series[$fromIndex].value
    $end = [double]$Series[$Series.Count - 1].value
    if ($start -eq 0) { return $null }
    return [Math]::Round((($end - $start) / $start) * 100.0, 3)
}

function Get-PriceTrendText([double]$Fast, [double]$Slow, $Momentum) {
    if ($null -eq $Fast -or $null -eq $Slow) { return "aguardando" }
    if ($Fast -gt $Slow * 1.00025 -and $Momentum -ge 0) { return "alta" }
    if ($Fast -lt $Slow * 0.99975 -and $Momentum -le 0) { return "baixa" }
    return "neutra"
}

function Update-IndicatorRobots([string]$Symbol, [double]$Price, [int64]$Timestamp) {
    Add-PricePoint $Symbol $Price $Timestamp
    $series = $priceHistory[$Symbol]
    if ($null -eq $series -or $series.Count -lt 2) {
        $robot = Ensure-IndicatorRobot $Symbol
        $robot.price = [Math]::Round($Price, 5)
        $robot.last_update = $Timestamp
        $robot.notes = "coleta inicial"
        return
    }

    $emaFast = Get-EMA $series 5
    $emaSlow = Get-EMA $series 13
    $momentum = Get-MomentumPct $series 5
    $price0 = [double]$series[$series.Count - 1].value
    $robot = Ensure-IndicatorRobot $Symbol
    $robot.price = [Math]::Round($price0, 5)
    $robot.ema_fast = $emaFast
    $robot.ema_slow = $emaSlow
    $robot.momentum = if ($null -ne $momentum) { [string]$momentum + "%" } else { "aguardando" }
    $robot.trend = Get-PriceTrendText $emaFast $emaSlow $momentum
    $robot.strength = if ($null -ne $emaFast -and $null -ne $emaSlow) {
        [int][Math]::Round([Math]::Abs($emaFast - $emaSlow) * 1000.0, 0)
    } else {
        0
    }
    $robot.score = if ($null -ne $momentum) {
        [int][Math]::Min(100, [Math]::Max(0, [Math]::Round([Math]::Abs($momentum) * 10.0, 0)))
    } else {
        0
    }
    $robot.last_update = $Timestamp
    $robot.notes = if ($robot.trend -eq "alta") {
        "preco acima da tendencia curta"
    } elseif ($robot.trend -eq "baixa") {
        "preco abaixo da tendencia curta"
    } else {
        "sem direcao forte"
    }
}

try {
    foreach ($progId in $progIds) {
        try {
            $server = New-Object -ComObject $progId
            $cfg.prog_id = $progId
            break
        } catch {
            $lastError = $_.Exception.Message
        }
    }
    if ($null -eq $server) { throw "Unable to connect to any RTD server id." }
    $connected = $true
    $start = $server.ServerStart($callback)
    if (-not $start) { throw "ServerStart returned 0" }
    Write-State "connected"
    Write-Discovery "connected"

    foreach ($symbol in @($cfg.symbols)) {
        foreach ($field in @($cfg.fields)) {
            try {
                $topicId = Get-TopicId $symbol $field
                $value = Normalize-Value $server.ConnectData($topicId, @($symbol, $field), $true)
                if ($null -ne $value) {
                    $discovery.Add([ordered]@{ symbol = $symbol; field = $field; value = $value })
                    $key = "$symbol|$field"
                    $cache[$key] = $value
                    $tick = [ordered]@{
                        symbol = $symbol
                        field = $field
                        value = $value
                        timestamp = (NowTs)
                        iso_time = (NowIso)
                        topic_id = $topicId
                    }
                    $recentTicks.Add($tick)
                    $totalUpdates++
                    $totalTicks++
                    Trim-RecentTicks
                    $stat = Ensure-SymbolStat $symbol
                    $stat.updates++
                    $stat.last_update = $tick.timestamp
                    if ($field -in @('ULT','LAST')) {
                        $prev = $stat.last_price
                        $stat.last_price = $value
                        if ($prev -is [double] -or $prev -is [int]) {
                            if ($value -gt $prev) { $stat.direction_bias = "up" }
                            elseif ($value -lt $prev) { $stat.direction_bias = "down" }
                            else { $stat.direction_bias = "flat" }
                        }
                    } elseif ($field -eq 'BID') {
                        $stat.last_bid = $value
                    } elseif ($field -eq 'ASK') {
                        $stat.last_ask = $value
                    } elseif ($field -eq 'VOLUME') {
                        $stat.last_volume = $value
                    } elseif ($field -eq 'ABE') {
                        $stat.day_open = $value
                    } elseif ($field -eq 'MAX') {
                        $stat.day_high = $value
                    } elseif ($field -eq 'MIN') {
                        $stat.day_low = $value
                    } elseif ($field -eq 'VAR') {
                        $stat.last_daily_change = $value
                    } elseif ($field -eq 'DAT') {
                        $stat.trade_date = $value
                    } elseif ($field -eq 'HOR') {
                        $stat.trade_time = $value
                    } elseif ($field -eq 'VEN') {
                        $stat.expiry_date = $value
                    }
                    if ($field -in @('ABE','VAR') -and $timeframeState.ContainsKey($symbol) -and $null -ne $stat.last_price) {
                        Update-TimeframeState $symbol ([double]$stat.last_price) $tick.timestamp
                    }
                    if ($field -in @('ULT','LAST') -and ($value -is [double] -or $value -is [int])) {
                        Update-IndicatorRobots $symbol ([double]$value) $tick.timestamp
                        Update-TimeframeState $symbol ([double]$value) $tick.timestamp
                    }
                    $elapsed = [Math]::Max(([double](NowTs) - $startedAt), 1.0)
                    $stat.tick_frequency = [Math]::Round(($stat.updates / $elapsed), 4)
                }
            } catch {
                $lastError = $_.Exception.Message
            }
        }
    }

    Write-Snapshot
    Write-State "streaming"
    Write-Discovery "streaming"
    $callback.UpdateNotify()

    while ($true) {
        foreach ($symbol in @($cfg.symbols)) {
            foreach ($field in @($cfg.fields)) {
                $topicId = Get-TopicId $symbol $field
                try {
                    $value = Normalize-Value $server.ConnectData($topicId, @($symbol, $field), $true)
                    if ($null -eq $value) { continue }
                    $key = "$symbol|$field"
                    if ($cache.ContainsKey($key) -and $cache[$key] -eq $value) { continue }
                    $cache[$key] = $value
                    $tick = [ordered]@{
                        symbol = $symbol
                        field = $field
                        value = $value
                        timestamp = (NowTs)
                        iso_time = (NowIso)
                        topic_id = $topicId
                    }
                    $recentTicks.Add($tick)
                    $totalUpdates++
                    $totalTicks++
                    Trim-RecentTicks
                    $stat = Ensure-SymbolStat $symbol
                    $stat.updates++
                    $stat.last_update = $tick.timestamp
                    if ($field -in @('ULT','LAST')) {
                        $prev = $stat.last_price
                        $stat.last_price = $value
                        if ($prev -is [double] -or $prev -is [int]) {
                            if ($value -gt $prev) { $stat.direction_bias = "up" }
                            elseif ($value -lt $prev) { $stat.direction_bias = "down" }
                            else { $stat.direction_bias = "flat" }
                        }
                    } elseif ($field -eq 'BID') {
                        $stat.last_bid = $value
                    } elseif ($field -eq 'ASK') {
                        $stat.last_ask = $value
                    } elseif ($field -eq 'VOLUME') {
                        $stat.last_volume = $value
                    } elseif ($field -eq 'ABE') {
                        $stat.day_open = $value
                    } elseif ($field -eq 'MAX') {
                        $stat.day_high = $value
                    } elseif ($field -eq 'MIN') {
                        $stat.day_low = $value
                    } elseif ($field -eq 'VAR') {
                        $stat.last_daily_change = $value
                    } elseif ($field -eq 'DAT') {
                        $stat.trade_date = $value
                    } elseif ($field -eq 'HOR') {
                        $stat.trade_time = $value
                    } elseif ($field -eq 'VEN') {
                        $stat.expiry_date = $value
                    }
                    if ($field -in @('ABE','VAR') -and $timeframeState.ContainsKey($symbol) -and $null -ne $stat.last_price) {
                        Update-TimeframeState $symbol ([double]$stat.last_price) $tick.timestamp
                    }
                    if ($field -in @('ULT','LAST') -and ($value -is [double] -or $value -is [int])) {
                        Update-IndicatorRobots $symbol ([double]$value) $tick.timestamp
                        Update-TimeframeState $symbol ([double]$value) $tick.timestamp
                    }
                    $elapsed = [Math]::Max(([double](NowTs) - $startedAt), 1.0)
                    $stat.tick_frequency = [Math]::Round(($stat.updates / $elapsed), 4)
                } catch {
                    $lastError = $_.Exception.Message
                }
            }
        }

        if ((NowTs) - $lastFlush -ge [double]$cfg.flush_interval_seconds) {
            Write-Snapshot
            Write-State "streaming"
            $lastFlush = NowTs
        }

        if ((NowTs) - $lastPlot -ge [double]$cfg.plot_interval_seconds) {
            $lastPlot = NowTs
        }

        Start-Sleep -Milliseconds ([int]$cfg.poll_interval_ms)
    }
} catch {
    $lastError = $_.Exception.Message
    Write-State "crashed"
    throw
}
