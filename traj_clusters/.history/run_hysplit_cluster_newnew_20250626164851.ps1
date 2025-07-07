<#
  run_hysplit_cluster.ps1 — v8.0  2025-06-27
  ========================================================
  • 新增  -Aggregate  开关：带该参数时，把 -Months 列表一次性聚类
  • 无 -Aggregate 时，保持旧逻辑，逐月循环处理
  • 其余流程（cluster → trajmean → merglist → trajplot）保持一致
  .\run_hysplit_cluster.ps1 `
    -TrajRoot  "F:\ERA5_pressure_level\traj_points" `
    -YearStart 1979 -YearEnd 2020 `
    -Months    1,2,3,4,5 `
    -Points    P1,P2 `
    -KeepHours 06,18 `
    -Aggregate       # ← 新增开关
#>

param (
    [Parameter(Mandatory=$true)][string]  $TrajRoot,
    [Parameter(Mandatory=$true)][int]     $YearStart,
    [Parameter(Mandatory=$true)][int]     $YearEnd,
    [int[]]    $Months    = @(),
    [string[]] $Points    = @('P1'),
    [string[]] $KeepHours = @('06','18'),
    [switch]   $Aggregate                # ← 一次性聚类所有指定月份
)

# ========= 常量配置 =========
$pythonExe   = 'py'; $pyVersion = '-3.9'; $scriptIN = 'create_INFILE.py'
$hysRoot     = 'C:\hysplit'
$scriptsDir  = "D:\Github\HYSPLITwithERA5\traj_clusters"
$execDir     = "$hysRoot\exec"
$workDir     = "$hysRoot\cluster\working"
$templateCC  = 'CCONTROL'
$trajData    = 'DELPCT'
$clusendArgs = '-a30 -n1 -t30 -p15'
$trajmeanExe = "$execDir\trajmean.exe"
$merglistExe = "$execDir\merglist.exe"
$trajmeanV   = 0   # 0-pressure  1-agl

# ========= 基础检查 =========
foreach ($p in @($TrajRoot,$execDir,$templateCC,$trajmeanExe)) {
    if (-not (Test-Path $p)) { throw "❌ 路径不存在: $p" }
}
if (-not (Get-Command $pythonExe -ErrorAction SilentlyContinue)) {
    throw '❌ 未找到 Python 启动器 py'
}

# ========= 工具函数 =========
function Get-MonTag([int[]]$monArray) {
    $monArray = $monArray | Sort-Object
    if ($monArray.Count -eq 1) { return '{0:d2}' -f $monArray[0] }
    else {
        $min = '{0:d2}' -f $monArray[0]
        $max = '{0:d2}' -f $monArray[-1]
        return "M${min}-${max}"      # 例：M01-05
    }
}

# ========= 共用过程 =========
function Invoke-ClusterPipeline {
    param (
        [string]$MonTag,   # 月份标签（01 / M01-05）
        [string]$Point     # P1 / P2…
    )

    Write-Host "===== 处理: 月=$MonTag, 点=$Point =====" -ForegroundColor Cyan

    # —— 目录 & 文件标签 ——
    $archiveDir = "$hysRoot\cluster\archive\${YearStart}_${YearEnd}_${MonTag}_$Point"
    New-Item -ItemType Directory -Path $archiveDir -Force | Out-Null
    $infile = Join-Path $workDir 'INFILE'

    # —— 1. 生成 INFILE ——
    $pyArgs = @($pyVersion, $scriptIN,
                '--root', $TrajRoot,
                '--outfile', $infile,
                '--years',  $YearStart, $YearEnd,
                '--ref-subdir', $Point,
                '--months')
    $pyArgs += $Months          # 传全部月份或单月
    $pyArgs += '--keep-hours'
    $pyArgs += $KeepHours
    & $pythonExe @pyArgs
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $infile)) {
        Write-Warning "[INFILE] 生成失败"; return
    }

    # —— 2. cluster 系列 ——
    Copy-Item $templateCC (Join-Path $workDir 'CCONTROL') -Force
    Push-Location $workDir

    & "$execDir\cluster.exe"
    $label = "${YearStart}_${YearEnd}_${MonTag}_${Point}"
    & "$execDir\clusplot.exe" "-i$trajData" "+g1" "-l$label" "-oclusplot_${label}.html"

    & "$execDir\clusend.exe" $clusendArgs
    if (-not (Test-Path 'CLUSEND')) { Write-Warning "[CLUSEND] 未生成"; Pop-Location; return }

    $select_k = Join-Path $scriptsDir 'select_K.py'
    $Kstr = & $pythonExe $pyVersion $select_k (Join-Path $workDir 'DELPCT') --min 1 --max 15 --S 1.0 --online
    $K = [int]$Kstr.Trim()
    Write-Host "[cluster] 使用 K=$K" -ForegroundColor Yellow
    & "$execDir\cluslist.exe" "-iCLUSTER" "-n$K" "-oCLUSLIST"
    if (-not (Test-Path 'CLUSLIST')) { Write-Warning "[CLUSLIST] 未生成"; Pop-Location; return }
    & "$execDir\clusmem.exe" "-iCLUSLIST"
    Rename-Item -Path 'CLUSLIST' -NewName "CLUSLIST_$K" -Force

    # —— 3. 生成 tmp + trajmean ——
    Push-Location $scriptsDir
    & $pythonExe $pyVersion create_traj_tmp.py -d $workDir
    Pop-Location

    $meanFiles = @()
    Get-ChildItem -Path $workDir -Filter 'TRAJ.INP.C*' | ForEach-Object {
        $cxfile = $_.FullName; $cxname = $_.Name
        Write-Host "[trajmean] 处理: $cxname" -ForegroundColor Magenta
        if ($cxname -match 'TRAJ\.INP\.(C\d+_\d+)') { $core = $matches[1] } else { $core = $cxname }
        $output = "${core}_mean"
        $cmd = "$trajmeanExe -i+`"$cxname`" -o$output -m0 -v$trajmeanV"
        Write-Host "    CMD: $cmd"
        iex $cmd
        $meanFiles += $output

        # 删除 tmp
        Get-Content $cxfile | Where-Object { $_ -match '\\' } | ForEach-Object {
            $tmp = $_.TrimEnd()
            if (Test-Path $tmp) { Remove-Item $tmp -Force }
        }
    }

    # —— 4. merglist ——
    if ($meanFiles.Count) {
        $inputList  = $meanFiles -join '+'
        $mergedBase = 'merged_mean'
        $cmd2 = "$merglistExe -i$inputList -o$mergedBase"
        Write-Host "[merglist] CMD: $cmd2" -ForegroundColor Cyan
        iex $cmd2
    } else { Write-Warning "[merglist] 无 mean 文件"; Pop-Location; return }

    # —— 5. trajplot ——
    $trajplotExe = "$execDir\trajplot.exe"
    & $trajplotExe --% -a3 -A3 -f0 +g1 -i"merged_mean.tdump" -j"$hysRoot/graphics/arlmap" -oTRAJMEAN -k3 -l24 -L1 -m0 -s1 -v4 -z67
    Rename-Item 'TRAJMEAN.html' "${label}_TRAJMEAN.html"  -Force
    Rename-Item 'TRAJMEAN_01.kml' "${label}_TRAJMEAN.kml" -Force
    Write-Host "[trajplot] 完成绘图 → ${label}_TRAJMEAN.html" -ForegroundColor Green

    # —— 6. 归档 ——
    Get-ChildItem $workDir -File | Where-Object { $_.Name -ne 'CCONTROL' } |
        Move-Item -Destination $archiveDir -Force
    Write-Host "[archive] 已归档到 $archiveDir" -ForegroundColor Green

    Pop-Location       # 退回 scriptsDir
}

# ========= 主逻辑 =========
if ($Aggregate) {
    # 一次聚类全部指定月份
    $monTag = Get-MonTag $Months
    foreach ($pt in $Points) { Invoke-ClusterPipeline -MonTag $monTag -Point $pt }
} else {
    # 逐月循环
    foreach ($month in $Months) {
        $monTag = '{0:d2}' -f $month
        foreach ($pt in $Points) { Invoke-ClusterPipeline -MonTag $monTag -Point $pt }
    }
}
