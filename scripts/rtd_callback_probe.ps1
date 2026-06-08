$env:LIB = ""
Add-Type -IgnoreWarnings -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
using System.Runtime.CompilerServices;

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

    public RtdCallback()
    {
        HeartbeatInterval = -1;
    }

    public void UpdateNotify() { UpdateCount++; }
    public void Disconnect() { }
}
"@

$server = New-Object -ComObject 'RTDTrading.RTDServer'
$cb = New-Object RtdCallback

$result = [ordered]@{
    updated_at_iso = (Get-Date).ToString('s')
    symbol = 'WINQ26_F_0'
    field = 'ULT'
    status = 'init'
    callback_mode = 'dotnet'
    update_notify_count = 0
    steps = @()
}

Write-Output "DispatchOK=$($null -ne $server)"
Write-Output "Heartbeat=$($server.Heartbeat())"
try {
    $start = $server.ServerStart($cb)
    Write-Output "ServerStart=$start"
    Write-Output "UpdateCount=$($cb.UpdateCount)"
    $result.status = 'serverstart_ok'
    try {
        $value = $server.ConnectData(1, @('WINQ26_F_0','ULT'), $true)
        Write-Output "ConnectData=$value"
        $result.status = 'connectdata_ok'
        $result.connectdata = $value
        Start-Sleep -Milliseconds 500
        try {
            $topicCount = 0
            $refresh = $server.RefreshData([ref]$topicCount)
            Write-Output "RefreshTopicCount=$topicCount"
            Write-Output "RefreshData=$refresh"
            $result.refresh_topic_count = $topicCount
            $result.refreshdata = $refresh
        } catch {
            Write-Output "RefreshDataError=$($_.Exception.Message)"
            if ($_.Exception.InnerException) {
                Write-Output "RefreshDataInner=$($_.Exception.InnerException.Message)"
            }
        }
    } catch {
        Write-Output "ConnectDataError=$($_.Exception.Message)"
        if ($_.Exception.InnerException) {
            Write-Output "ConnectDataInner=$($_.Exception.InnerException.Message)"
        }
        $result.status = 'connectdata_error'
    }
} catch {
    Write-Output "ServerStartError=$($_.Exception.Message)"
    if ($_.Exception.InnerException) {
        Write-Output "ServerStartInner=$($_.Exception.InnerException.Message)"
    }
    $result.status = 'serverstart_error'
}

$result.update_notify_count = $cb.UpdateCount
$smokePath = Join-Path $PSScriptRoot '..\\data\\rtd\\smoke_test.json'
New-Item -ItemType Directory -Force -Path (Split-Path $smokePath) | Out-Null
$json = $result | ConvertTo-Json -Depth 8
[System.IO.File]::WriteAllText($smokePath, $json, (New-Object System.Text.UTF8Encoding($false)))
