# Start the WH80 bridge (and the L-Connect proxy, if enabled in settings) at login, hidden.
#   Install:  powershell -ExecutionPolicy Bypass -File wh80\install_autostart.ps1
#   Remove:   powershell -ExecutionPolicy Bypass -File wh80\install_autostart.ps1 -Remove
param([switch]$Remove)

$lnk = Join-Path ([Environment]::GetFolderPath('Startup')) 'WH80 RGB bridge.lnk'
if ($Remove) {
    Remove-Item $lnk -ErrorAction SilentlyContinue
    Write-Host "Removed $lnk"
    return
}

$pythonw = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
if (-not $pythonw) { throw "pythonw.exe not found on PATH. Install Python 3.10+ from python.org." }
$script = Join-Path $PSScriptRoot 'wh80_services.pyw'

$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut($lnk)
$s.TargetPath = $pythonw
$s.Arguments = "`"$script`""
$s.WorkingDirectory = $PSScriptRoot
$s.WindowStyle = 7
$s.Description = 'NuPhy WH80 RGB bridge for OpenRGB'
$s.Save()
Write-Host "Installed: $lnk"
Write-Host "Start it now without logging out:  & `"$pythonw`" `"$script`""
