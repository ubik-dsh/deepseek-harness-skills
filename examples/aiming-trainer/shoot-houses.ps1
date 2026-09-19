# Launch the houses arena, let it play, screenshot, stop.
param(
    [string]$Title = "Houses: chaser vs hider",
    [string]$Script = "arena_houses.py",
    [string]$Out = "$env:TEMP\houses.png",
    [int]$WarmupSeconds = 14,
    [string]$Arguments = "--windowed --speed 3"
)

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Shot2 {
    [StructLayout(LayoutKind.Sequential)]
    public struct RECT { public int Left, Top, Right, Bottom; }
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
}
"@

$proc = Start-Process -FilePath "python" -ArgumentList "$Script $Arguments" -PassThru -WorkingDirectory $PSScriptRoot
Write-Host "started pid $($proc.Id), warming up ${WarmupSeconds}s"
Start-Sleep -Seconds $WarmupSeconds

$window = $null
for ($i = 0; $i -lt 25; $i++) {
    # A prefix match, not equality: under --rl the title becomes
    # "Houses: chaser vs hider [RL]", and an exact comparison found nothing.
    $window = Get-Process -Name python -ErrorAction SilentlyContinue |
              Where-Object { $_.MainWindowTitle -like "$Title*" } | Select-Object -First 1
    if ($window) { break }
    Start-Sleep -Milliseconds 400
}
if (-not $window) {
    Write-Host "no window titled '$Title'"
    Get-Process -Name python -ErrorAction SilentlyContinue | Stop-Process -Force
    exit 1
}

$handle = $window.MainWindowHandle
[void][Shot2]::SetForegroundWindow($handle)
Start-Sleep -Milliseconds 700
$rect = New-Object Shot2+RECT
[void][Shot2]::GetWindowRect($handle, [ref]$rect)
$w = $rect.Right - $rect.Left
$h = $rect.Bottom - $rect.Top
Write-Host "window ${w}x${h}"

$bmp = New-Object System.Drawing.Bitmap $w, $h
$gfx = [System.Drawing.Graphics]::FromImage($bmp)
$gfx.CopyFromScreen($rect.Left, $rect.Top, 0, 0, (New-Object System.Drawing.Size $w, $h))
$bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
$gfx.Dispose(); $bmp.Dispose()
Write-Host "saved $Out"

Start-Sleep -Seconds 5
Get-Process -Name python -ErrorAction SilentlyContinue | Stop-Process -Force
Write-Host "stopped"
