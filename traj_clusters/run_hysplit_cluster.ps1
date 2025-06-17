<#
  run_hysplit_cluster.ps1 — v4.1  (SVG 输出)
  =============================================================
  关键变动：
    • 调用 clusplot.exe 时增加 `+g1`（SVG 模式）并指定 `-o clusplot_raw.svg`。
    • 不再生成 PostScript；工作/归档目录直接得到 `clusplot_raw.svg`（浏览器可直接打开）。
    • 其余流程不变：第一次 cluster 计算 TSV → clusend 拐点 → 写 K → 第二次 cluster 归类。

  使用示例见脚本底部注释。
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
$clusDataset = "DELPCT"   # TSV 数据文件名

# ===== 基本检查 =====
foreach ($p in @($TrajRoot,$exeDir,$templateCC)) { if (!(Test-Path $p)) { throw "❌ 路径不存在: $p" } }
if (!(Get-Command $pythonExe -ErrorAction SilentlyContinue)) { throw "❌ 未找到 Python 启动器 py" }

# ===== 月份标签 =====
$monTag = if ($Months.Count) { ($Months | ForEach-Object { '{0:d2}' -f $_ }) -join '' } else { 'all' }

# ===== 主循环 =====
foreach ($pt in $Points) {
    Write-Host "========== 处理 [$pt] ==========" -ForegroundColor Cyan

    # 1. 归档目录
    $archiveDir = "$hysRoot\cluster\archive\${YearStart}_${YearEnd}_${monTag}_$pt"
    New-Item -ItemType Directory -Path $archiveDir -Force | Out-Null

    # 2. 生成 INFILE
    $infilePath = "$workDir\INFILE"
    $pyArgs = @($pyVersion,$scriptIN,'--root',$TrajRoot,'--outfile',$infilePath,'--years',$YearStart,$YearEnd,'--ref-subdir',$pt)
    if ($Months) { $pyArgs += '--months'; $pyArgs += $Months }
    & $pythonExe @pyArgs
    if ($LASTEXITCODE -ne 0 -or !(Test-Path $infilePath)) { Write-Warning "[$pt] INFILE 生成失败，跳过"; continue }

    # 3. 准备工作目录
    Copy-Item $templateCC "$workDir\CCONTROL" -Force
    Set-Location $workDir

    # 4. 第一次 cluster.exe
    & "$exeDir\cluster.exe"

    # 5. clusplot.exe → SVG
    & "$exeDir\clusplot.exe" "-i$clusDataset" "+g1" "-o" "clusplot_raw.svg"
    if (!(Test-Path 'clusplot_raw.svg')) { Write-Warning "[$pt] clusplot 未生成 SVG。" }

    # 6. 20% / 30% 拐点
    foreach ($f in 'CLUSEND','CLUSEND_20','CLUSEND_30') { if (Test-Path $f) { Remove-Item $f -Force } }
    & "$exeDir\clusend.exe" 20
    Rename-Item 'CLUSEND' 'CLUSEND_20' -Force
    $K20 = [int]((Get-Content 'CLUSEND_20')[0].Split()[0])
    & "$exeDir\clusend.exe" 30
    Rename-Item 'CLUSEND' 'CLUSEND_30' -Force
    $K30 = [int]((Get-Content 'CLUSEND_30')[0].Split()[0])
    $Kfinal = if ($K20 -ge 3) { $K20 } else { $K30 }
    Write-Host "[$pt] 采用 K=$Kfinal (20%=$K20  30%=$K30)" -ForegroundColor Yellow

    # 7. 更新 CCONTROL
    (Get-Content 'CCONTROL') | ForEach-Object -Begin {$i=0} -Process { $i++; if ($i -eq 4) { "$Kfinal" } else { $_ } } | Set-Content 'CCONTROL' -Encoding ASCII

    # 8. 第二次 cluster.exe
    & "$exeDir\cluster.exe"

    # 9. 归档
    Get-ChildItem $workDir -File | Where-Object { $_.Name -ne 'CCONTROL' } | Move-Item -Destination $archiveDir -Force
    Write-Host "[$pt] ✅ 归档完成 → $archiveDir" -ForegroundColor Green
    Write-Host "---------------------------------------------`n"
}

Write-Host "所有点位处理完毕。" -ForegroundColor Green

<#
调用示例：
.\run_hysplit_cluster.ps1 `
    -TrajRoot  "F:\ERA5_pressure_level\traj_points" `
    -YearStart 1950 -YearEnd 1953 `
    -Months    1 `
    -Points    P1
#>
