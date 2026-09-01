# ゲーム窓(または エディタ窓)をそのまま PNG に撮る。
#   HUD は ImGui 経由なので dx12_screenshot* には【写らない】。HUD を見るにはこれを使う。
#
#   pwsh -File docs/shot.ps1 -Title DX12Engine -Out out.png
param(
    [string]$Title = "DX12Engine",
    [string]$Out   = "shot.png"
)

Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class W {
    [DllImport("user32.dll")] public static extern bool GetClientRect(IntPtr h, out R r);
    [DllImport("user32.dll")] public static extern bool ClientToScreen(IntPtr h, ref P p);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    public struct R { public int L, T, Rt, B; }
    public struct P { public int X, Y; }
}
"@

$proc = Get-Process | Where-Object { $_.MainWindowTitle -like "*$Title*" } | Select-Object -First 1
if (-not $proc) { Write-Error "窓が見つからない: *$Title*"; exit 1 }
$h = $proc.MainWindowHandle

[W]::SetForegroundWindow($h) | Out-Null
Start-Sleep -Milliseconds 250

$r = New-Object W+R
[W]::GetClientRect($h, [ref]$r) | Out-Null
$p = New-Object W+P
[W]::ClientToScreen($h, [ref]$p) | Out-Null

$w = $r.Rt - $r.L
$hh = $r.B - $r.T
if ($w -le 0 -or $hh -le 0) { Write-Error "クライアント領域が 0"; exit 1 }

$bmp = New-Object System.Drawing.Bitmap $w, $hh
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($p.X, $p.Y, 0, 0, $bmp.Size)
$full = [System.IO.Path]::GetFullPath((Join-Path (Get-Location) $Out))
$bmp.Save($full, [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $bmp.Dispose()
Write-Host "wrote $full ($w x $hh)"
