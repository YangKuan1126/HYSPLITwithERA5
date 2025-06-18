<#
  run_hysplit_cluster.ps1 — v5.1  (SVG 保留，不再转换 PNG)
  =====================================================================
  变动（2025-06-20）：
    • 关闭 SVG→PNG 自动转换：`$convertSvgToPng = $false`。
    • 保留 SVG 输出与 cluslist/clusmem 归类流程。
    • 若未来需要 PNG，只需将 `$convertSvgToPng` 改回 `$true` 并保证 Inkscape 在 PATH。
#>

param(
    [Parameter(Mandatory=$true)][string]  $TrajRoot,
    [Parameter(Mandatory=$true)][int]     $YearStart,
    [Parameter(Mandatory=$true)][int]     $YearEnd,
    [int[]]   $Months = @(),
    [string[]]$Points = @('P1')
)

# ===== 可配置路径 =====
$pythonExe   = "py"
$pyVersion   = "-3.9"
$scriptIN    = "create_INFILE.py"
$hysRoot     = "C:\hysplit"
$exeDir      = "$hysRoot\exec"
$workDir     = "$hysRoot\cluster\working"
$templateCC  = "CCONTROL"
$clusDataset = "DELPCT"
$clusendArgs = "-a30 -n1 -t30 -p15"
$convertSvgToPng = $false              # ▶️ 不再转换 PNG
$inkscapeExe = "inkscape"

# ===== 检查 =====
foreach ($p in @($TrajRoot,$exeDir,$templateCC)) { if (!(Test-Path $p)) { throw "❌ 路径不存在: $p" } }
if (!(Get-Command $pythonExe -ErrorAction SilentlyContinue)) { throw "❌ 未找到 Python 启动器 py" }

# ===== 月标签 =====
$monTag = if ($Months.Count) { ($Months | ForEach-Object { '{0:d2}' -f $_ }) -join '' } else { 'all' }

# ===== 主循环 =====
foreach ($pt in $Points) {
    Write-Host "========== 处理 [$pt] ==========" -ForegroundColor Cyan

    # 1 归档目录
    $archiveDir = "$hysRoot\cluster\archive\${YearStart}_${YearEnd}_${monTag}_$pt"
    New-Item -ItemType Directory -Path $archiveDir -Force | Out-Null

    # 2 生成 INFILE
    $infilePath = "$workDir\INFILE"
    $pyArgs = @($pyVersion,$scriptIN,'--root',$TrajRoot,'--outfile',$infilePath,'--years',$YearStart,$YearEnd,'--ref-subdir',$pt)
    if ($Months) { $pyArgs += '--months'; $pyArgs += $Months }
    & $pythonExe @pyArgs
    if ($LASTEXITCODE -ne 0 -or !(Test-Path $infilePath)) { Write-Warning "[$pt] INFILE 生成失败，跳过"; continue }

    # 3 准备工作目录
    Copy-Item $templateCC "$workDir\CCONTROL" -Force
    Set-Location $workDir

    # 4 第一次 cluster.exe（生成 TSV 数据）
    & "$exeDir\cluster.exe"

    # 5 clusplot → SVG with label
    $label = "${YearStart}_${YearEnd}_${monTag}_${pt}"
    $svgFile = "clusplot_${label}.svg"
    & "$exeDir\clusplot.exe" "-i$clusDataset" "+g1" "-l$label" "-o" $svgFile
    if (!(Test-Path $svgFile)) { Write-Warning "[$pt] clusplot 未生成 SVG" }

    # （PNG 转换已禁用）
    if ($convertSvgToPng -and (Get-Command $inkscapeExe -ErrorAction SilentlyContinue)) {
        $pngFile = $svgFile -replace "\.svg$", ".png"
        & $inkscapeExe $svgFile --export-type=png --export-filename=$pngFile --batch-process --with-gui 2>$null
        if (Test-Path $pngFile) { Write-Host "[$pt] 已生成 PNG → $pngFile" -ForegroundColor Green }
    }

    # 6 clusend.exe（一次运行）
    if (Test-Path 'CLUSEND') { Remove-Item 'CLUSEND' -Force }
    & "$exeDir\clusend.exe" $clusendArgs
    if (!(Test-Path 'CLUSEND')) { Write-Warning "[$pt] 未生成 CLUSEND"; continue }
    $lines  = Get-Content 'CLUSEND'
    if ($lines.Count -lt 2) { Write-Warning "[$pt] CLUSEND 行数不足"; continue }
    $Kfinal = [int]($lines[-2].Trim().Split()[0])
    Write-Host "[$pt] 采用 K=$Kfinal (倒数第二行)" -ForegroundColor Yellow

    # 7 cluslist.exe 归类
    $cluslist = "CLUSLIST_$Kfinal"
    & "$exeDir\cluslist.exe" "-iCLUSTER" "-n$Kfinal" "-o$cluslist"
    if (!(Test-Path $cluslist)) { Write-Warning "[$pt] cluslist 未生成 $cluslist"; continue }

    # 8 clusmem.exe 生成簇平均轨迹
    $meanFile = "TRAJ.INP.C$('{0:D2}' -f $Kfinal)"
    & "$exeDir\clusmem.exe" "-i$cluslist" "-o$meanFile"
    if (!(Test-Path $meanFile)) { Write-Warning "[$pt] clusmem 未生成 $meanFile" }

    # 9 归档
    Get-ChildItem $workDir -File | Where-Object { $_.Name -ne 'CCONTROL' } | Move-Item -Destination $archiveDir -Force
    Write-Host "[$pt] ✅ 归档完成 → $archiveDir" -ForegroundColor Green
    Write-Host "---------------------------------------------`n"
}

Write-Host "所有点位处理完毕。" -ForegroundColor Green

<#
示例：
.\run_hysplit_cluster.ps1 `
    -TrajRoot  "F:\ERA5_pressure_level\traj_points" `
    -YearStart 1950 -YearEnd 1953 `
    -Months 1 `
    -Points P1
#>
