<#
  run_hysplit_cluster.ps1 — v7.5
  ========================================================
  • 增加 trajmean.exe 调用，读取 TRAJ.INP.CX_Y 文件中路径
  • 构造 -i 参数为路径+...
  • 输出文件自动命名 mean_CX_Y
#>
param (
    [Parameter(Mandatory=$true)][string]  $TrajRoot,
    [Parameter(Mandatory=$true)][int]     $YearStart,
    [Parameter(Mandatory=$true)][int]     $YearEnd,
    [int[]]    $Months    = @(),
    [string[]] $Points    = @('P1'),
    [string[]] $KeepHours = @('06','18')
)

# 配置
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
$trajmeanV   = 0

# 检查
foreach ($p in @($TrajRoot,$execDir,$templateCC,$trajmeanExe)) {
    if (!(Test-Path $p)) { throw "路径不存在: $p" }
}
if (!(Get-Command $pythonExe -ErrorAction SilentlyContinue)) {
    throw '未找到 Python 启动器 py'
}

foreach ($month in $Months) {
    # 🔹 将月份循环移至最外层
    $monTag = '{0:d2}' -f $month

    foreach ($pt in $Points) {
        # 🔹 点位循环在月份内部运行
        Write-Host "===== 处理：月=$monTag，点=$pt =====" -ForegroundColor Cyan
        $archiveDir = "$hysRoot\cluster\archive\${YearStart}_${YearEnd}_${monTag}_$pt"
        New-Item -ItemType Directory -Path $archiveDir -Force | Out-Null
        # ———————— 复制原有流程（只是带 monTag 与 pt 处理） ————————

        # 1. 生成 INFILE，只包含当前月和点位
        $infile = Join-Path $workDir 'INFILE'
        $pyArgs = @($pyVersion, $scriptIN, '--root', $TrajRoot, '--outfile', $infile,
                    '--years', $YearStart, $YearEnd, '--ref-subdir', $pt,
                    '--months', $month,                  # 🔹 单月参数
                    '--keep-hours')
        $pyArgs += $KeepHours
        & $pythonExe @pyArgs
        if ($LASTEXITCODE -ne 0 -or !(Test-Path $infile)) {
            Write-Warning "[$pt][$monTag] INFILE 生成失败"
            continue
        }

        # 2~7: cluster → select K → trajmean → merglist → trajplot → 归档
        # 这些部分均在此块中，保持原来逻辑，仅需确保所有文件路径包含 month 和 pt 标识
        # 2. 复制 CCONTROL 并切换目录
        Copy-Item $templateCC (Join-Path $workDir 'CCONTROL') -Force
        Set-Location $workDir

        # 3~7. cluster 系列
        & "$execDir\cluster.exe"
        $label = "${YearStart}_${YearEnd}_${monTag}_$pt"
        & "$execDir\clusplot.exe" "-i$trajData" "+g1" "-l$label" "-oclusplot_${label}.html"
        
        & "$execDir\clusend.exe" -a30 -n1 -t30 -p15
        if (!(Test-Path 'CLUSEND')) {
            Write-Warning "[$pt] CLUSEND 未生成"; continue
        }
        $select_k = Join-Path $scriptsDir 'select_K.py'
        $file_tsv = Join-Path $workDir 'DELPCT'
        $Kstr = & $pythonExe $pyVersion $select_k $file_tsv --min 1 --max 15 --S 1.0 --online
        $K = [int]$Kstr.Trim()
        Write-Host "[$pt] 采用 K=$K" -ForegroundColor Yellow
        & "$execDir\cluslist.exe" "-iCLUSTER" "-n$K" "-oCLUSLIST"
        if (!(Test-Path 'CLUSLIST')) {
            Write-Warning "[$pt] CLUSLIST 未生成"; continue
        }
        & "$execDir\clusmem.exe" "-iCLUSLIST"
        rename-item -Path 'CLUSLIST' -NewName "CLUSLIST_$K" -Force
        # 8. 生成 tmp & 调用 trajmean
        cd $scriptsDir
        & $pythonExe $pyVersion create_traj_tmp.py -d $workDir
        # 9. 执行 trajmean 分析 & 删除 tmp 文件（使用 listfile 模式，不传全路径）
        cd $workDir
        $meanFiles = @()  # 存储本次生成的 mean 文件

        Get-ChildItem -Path $workDir -Filter 'TRAJ.INP.C*' | ForEach-Object {
            $cxfile = $_.FullName
            $cxname = $_.Name
            Write-Host "[trajmean] 处理: $cxname" -ForegroundColor Magenta

            # 直接用 listfile 模式：-i+“TRAJ.INP.C1_2” 即可
            if ($cxname -match 'TRAJ\.INP\.(C\d+_\d+)') {
                $core = $matches[1]
            } else {
                $core = $cxname
            }
            $output = "${core}_mean"

            # 这里不拼接全路径，只传文件名，加上“+”前缀
            $cmd = "$trajmeanExe -i+`"$cxname`" -o$output -m0 -v$trajmeanV"
            Write-Host "    CMD: $cmd"
            iex $cmd

            # 收集输出文件名，供后续 merglist 使用
            $meanFiles += $output

            # 🔥 新增：删除所有参与本次 trajmean 的 _tmp 文件
            #    仍然用原来方式删除 tmp 文件
            Get-Content $cxfile | Where-Object { $_ -match '\\' } | ForEach-Object {
                $tmp = $_.TrimEnd()
                if (Test-Path $tmp) {
                    Write-Host "    删除 temp 文件: $tmp" -ForegroundColor Yellow
                    Remove-Item $tmp -Force -Verbose
                } else {
                    Write-Host "    找不到 temp 文件，跳过: $tmp"
                }
            }
        }


        # 10. 使用 merglist.exe 合并所有 mean 文件
        cd $workDir
        if ($meanFiles.Count -gt 0) {
            # 构建 merglist 参数： -i file1+file2+... -o merged_base
            $inputList = $meanFiles -join '+'
            $mergedBase = 'merged_mean'  # 可自定义输出基名
            $cmd2 = "$merglistExe -i$inputList -o$mergedBase"
            Write-Host "[merglist] CMD: $cmd2" -ForegroundColor Cyan
            iex $cmd2
            Write-Host "[merglist] 合并完成，输出文件名 base：$mergedBase"
                } else {Write-Warning "[merglist] 未找到任何 mean 文件，跳过合并步骤"}
        # 11. 使用 trajplot.exe 生成 trajplot 图               
        cd $workDir
        $label = "${YearStart}_${YearEnd}_${monTag}_$pt"
        $trajplotExe = "$execDir\trajplot.exe"
        & $trajplotExe --% -a3 -A3 -f0 +g1 -i"merged_mean.tdump" -j"C:/hysplit/graphics/arlmap" -oTRAJMEAN -k3 -l24 -L1 -m0 -s1 -v4 -z67
        rename-item -Path 'TRAJMEAN.html' -NewName "${label}_TRAJMEAN.html" -Force
        rename-item -Path 'TRAJMEAN_01.kml' -NewName "${label}_TRAJMEAN.kml" -Force
        Write-Host "[trajplot] 完成绘图 -> ${label}_TRAJMEAN.html" -ForegroundColor Green
        # 12. 归档
        Get-ChildItem $workDir -File | Where-Object { $_.Name -ne 'CCONTROL' } |
         Move-Item -Destination $archiveDir -Force
        Write-Host "[$pt] 归档完成" -ForegroundColor Green
        cd $scriptsDir
    }
}
    