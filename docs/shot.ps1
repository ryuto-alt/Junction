# ゲーム窓(または エディタ窓)をそのまま PNG に撮る。
#   HUD は ImGui 経由なので dx12_screenshot* には【写らない】。HUD を見るにはこれを使う。
#
#   pwsh -File docs/shot.ps1 -Out out.png
#
# ★窓のタイトルは "DX12 Engine - <プロジェクト名>"。間の空白を落とすと見つからない。
# ★既定は PrintWindow(PW_RENDERFULLCONTENT)。他のアプリの窓が手前に重なっていても、
#   その窓【自身】の中身が撮れる。CopyFromScreen は画面をそのまま写すので、
#   前面に別の窓があると そいつが写ってしまう(osu! が被って気づいた)。
#   D3D12 のスワップチェーンは PrintWindow で真っ黒になることがあるので、
#   結果がほぼ単色なら自動で CopyFromScreen へ落ちる。-Screen で最初から後者にできる。
param(
    [string]$Title  = "DX12 Engine",
    [string]$Out    = "shot.png",
    [switch]$Screen
)

Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class W {
    [DllImport("user32.dll")] public static extern bool GetClientRect(IntPtr h, out R r);
    [DllImport("user32.dll")] public static extern bool ClientToScreen(IntPtr h, ref P p);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern int  PrintWindow(IntPtr h, IntPtr dc, uint flags);
    public struct R { public int L, T, Rt, B; }
    public struct P { public int X, Y; }
}
"@

$proc = Get-Process | Where-Object { $_.MainWindowTitle -like "*$Title*" } | Select-Object -First 1
if (-not $proc) { Write-Error "窓が見つからない: *$Title*"; exit 1 }
$h = $proc.MainWindowHandle

$r = New-Object W+R
[W]::GetClientRect($h, [ref]$r) | Out-Null
$w  = $r.Rt - $r.L
$hh = $r.B  - $r.T
if ($w -le 0 -or $hh -le 0) { Write-Error "クライアント領域が 0"; exit 1 }

# ---- 撮る ----
$bmp = New-Object System.Drawing.Bitmap $w, $hh
$g   = [System.Drawing.Graphics]::FromImage($bmp)
$ok  = $false

if (-not $Screen) {
    $dc = $g.GetHdc()
    # 2 = PW_RENDERFULLCONTENT (DirectComposition の窓もこれで中身が出る)
    $ok = ([W]::PrintWindow($h, $dc, 2) -ne 0)
    $g.ReleaseHdc($dc)

    if ($ok) {
        # 真っ黒(= スワップチェーンが取れなかった)なら諦めて画面から撮る。
        # 端から少しだけ拾って判定する。全画素見ると遅い
        $sum = 0
        for ($y = 0; $y -lt $hh; $y += 97) {
            for ($x = 0; $x -lt $w; $x += 89) {
                $c = $bmp.GetPixel($x, $y); $sum += $c.R + $c.G + $c.B
            }
        }
        if ($sum -lt 100) { $ok = $false; Write-Host "PrintWindow が真っ黒 → 画面から撮り直す" }
    }
}

if (-not $ok) {
    [W]::SetForegroundWindow($h) | Out-Null
    Start-Sleep -Milliseconds 300
    $p = New-Object W+P
    [W]::ClientToScreen($h, [ref]$p) | Out-Null
    $g.CopyFromScreen($p.X, $p.Y, 0, 0, $bmp.Size)
}

# ★Join-Path は絶対パスを渡されても左側を足してしまう。絶対かどうかで分ける
$full = if ([System.IO.Path]::IsPathRooted($Out)) { $Out }
        else { [System.IO.Path]::GetFullPath((Join-Path (Get-Location) $Out)) }
$bmp.Save($full, [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $bmp.Dispose()
Write-Host "wrote $full ($w x $hh)"
