<#
  run_hysplit_cluster.ps1 — v6.0  (自动生成簇平均 tdump)
  =====================================================================
  新增功能（2025‑06‑21）：
    • **trajmean.exe 一键生成每个簇的平均轨迹（Cxx_mean.tdump）**
        - 读取 CLUSLIST → 按簇号分组 → 临时写成员列表 → 调 trajmean.exe。
        - 默认高度 `-v1`（AGL），可通过 `$trajmeanV` 调整。
    • 生成的 `Cxx_mean.tdump` 和示例 `clusplot_*.html`、`CLUSLIST` 等一起归档；
    • 其余流程保持 v5.2（支持 -KeepHours，PNG 转换关闭）。

  调用示例同前。若只想关闭均值生成，将 `$genMeans` 设为 `$false` 即可。
#>

param (
    [Parameter(Mandatory = $true)][string]  $TrajRoot,
    [Parameter(Mandatory = $true)][int]     $YearStart,
    [Parameter(Mandatory = $true)][int]     $YearEnd,

    [int[]]    $Months     = @(),
    [string[]] $Points     = @('P1'),
    [string[]] $KeepHours  = @('06','18')
)

# ===== 可配置路径 =====
$pythonExe   = "py";   $pyVersion = "-3.9"; $scriptIN = "create_INFILE.py"
$hysRoot     = "C:\hysplit"; $exeDir = "$hysRoot\exec"; $workDir = "$hysRoot\cluster\working"
$templateCC  = "CCONTROL"; $clusDataset = "DELPCT"
$clusendArgs = "-a30 -n1 -t30 -p15"
$trajmeanExe = "$exeDir\trajmean.exe"   # 生成簇平均轨迹
$trajmeanV   = 1                          # 0=pressure,1=agl
$genMeans    = $true                     # ▶️ 是否生成 Cxx_mean.tdump
$convertSvgToPng = $false                # PNG 转换仍关闭

# ===== 检查 =====
foreach ($p in @($TrajRoot,$exeDir,$templateCC,$trajmeanExe)) {
    if (!(Test-Path $p)) { throw "❌ 路径不存在: $p" }
}
if (!(Get-Command $pythonExe -ErrorAction SilentlyContinue)) { throw "❌ 未找到 Python 启动器 py" }

# ===== 月标签 =====
$monTag = if ($Months.Count) { ($Months | ForEach-Object { '{0:d2}' -f $_ }) -join '' } else { 'all' }

# ===== 主循环 =====
foreach ($pt in $Points) {
    Write-Host "========== 处理 [$pt] ==========" -ForegroundColor Cyan
    $archiveDir = "$hysRoot\cluster\archive\${YearStart}_${YearEnd}_${monTag}_$pt"
    New-Item -ItemType Directory -Path $archiveDir -Force | Out-Null

    # 1 生成 INFILE
    $infilePath = "$workDir\INFILE"
    $pyArgs = @($pyVersion,$scriptIN,'--root',$TrajRoot,'--outfile',$infilePath,'--years',$YearStart,$YearEnd,'--ref-subdir',$pt)
    if ($Months) { $pyArgs += '--months'; $pyArgs += $Months }
    if ($KeepHours) { $pyArgs += '--keep-hours'; $pyArgs += $KeepHours }
    & $pythonExe @pyArgs
    if ($LASTEXITCODE -ne 0 -or !(Test-Path $infilePath)) { Write-Warning "[$pt] INFILE 生成失败，跳过"; continue }

    # 2 准备工作目录
    Copy-Item $templateCC "$workDir\CCONTROL" -Force
    Set-Location $workDir

    # 3 第一次 cluster.exe
    & "$exeDir\cluster.exe"

    # 4 clusplot 曲线
    $label = "${YearStart}_${YearEnd}_${monTag}_${pt}"
    & "$exeDir\clusplot.exe" "-i$clusDataset" "+g1" "-l$label" "-oclusplot_${label}.html"

    # 5 clusend.exe 取 K
    if (Test-Path 'CLUSEND') { Remove-Item 'CLUSEND' -Force }
    & "$exeDir\clusend.exe" $clusendArgs
    if (!(Test-Path 'CLUSEND')) { Write-Warning "[$pt] 未生成 CLUSEND"; continue }
    $Kfinal = [int]((Get-Content 'CLUSEND')[-2].Trim().Split()[0])
    Write-Host "[$pt] 采用 K=$Kfinal" -ForegroundColor Yellow

    # 6 cluslist.exe
    & "$exeDir\cluslist.exe" "-iCLUSTER" "-n$Kfinal" "-oCLUSLIST"
    if (!(Test-Path 'CLUSLIST')) { Write-Warning "[$pt] cluslist 未生成 CLUSLIST"; continue }

    # 7 clusmem.exe 生成 TRAJ.INP.Cxx
    & "$exeDir\clusmem.exe" "-iCLUSLIST"    
    # 8 生成每个簇的平均轨迹 (直接读 TRAJ.INP.Cxx 文件)
    if ($genMeans) {
        # 找到所有 TRAJ.INP.C??_* 文件；按编号排序
        Get-ChildItem -Filter "TRAJ.INP.C??_*" | Sort-Object Name | ForEach-Object {

            # ---- ❶ 解析簇编号 & 读取成员路径 ----
            $match = $_.BaseName -match "TRAJ\\.INP\\.C(\\d{2})"
            if (-not $match) { return }
            $k = [int]$Matches[1]           # e.g. 01,02…

            $paths = Get-Content $_.FullName | Where-Object { $_.Trim() }
            if ($paths.Count -eq 0) {
                Write-Warning "[$pt] 簇 $k 文件为空，跳过 trajmean"
                return
            }

            # 把文件路径用 + 连接；注意整体加双引号
            $plusList = ($paths -join "+").Replace('"','')
            $outTd    = "C$('{0:D2}' -f $k)_mean.tdump"

            # ---- ❷ 调 trajmean.exe ----
            & $trajmeanExe "-i\"$plusList\"" "-o$outTd" -m0 "-v$trajmeanV" 2>$null

            if (Test-Path $outTd) {
                Write-Host "[$pt] 生成平均轨迹 $outTd" -ForegroundColor Green
            } else {
                Write-Warning "[$pt] trajmean 生成 $outTd 失败"
            }
        }
    }


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
    -YearStart 1979 -YearEnd 2020 `
    -Months    1 `
    -Points    P2,P3,P4,P5 `
    -KeepHours 06,18
#>

# C:\hysplit\exec\trajplot.exe -a3 -A3 -f0 -g1000 +g1 -i"TRAJ.INP.C1_5+TRAJ.INP.C2_5+TRAJ.INP.C3_5+TRAJ.INP.C4_5+TRAJ.INP.C5_5" -jC:/hysplit/graphics/arlmap -k1 -l24 -L1 -m0 -s1 -v4 -z50
