Param(
    [string] $RootDir         = 'F:\ERA5_pressure_level\traj_clusters\demo',
    [string] $ScriptsDir      = 'F:\scripts',
    [string] $PythonExe       = 'python',
    [string] $PyVersionArgs   = '',
    [string] $ExecDir         = 'F:\exec_dir',
    [string] $TrajmeanExe     = 'F:\exec_dir\trajmean.exe',
    [string] $MerglistExe     = 'F:\exec_dir\merglist.exe',
    [string] $TrajplotExe     = 'F:\exec_dir\trajplot.exe',
    [string] $TrajmeanV       = '0',
    [string] $YearStart       = '1979',  # 示例，你可改为 $pt.Split('_')[0]
    [string] $YearEnd         = '2019',
    [string] $MonTag          = '07'     # 示例，你可改为 $pt.Split('_')[2]
)

Get-ChildItem -Path $RootDir -Directory | ForEach-Object {
    $pt = $_.Name
    $workDir = $_.FullName
    Write-Host "`n=== 任务：$pt ===" -ForegroundColor Cyan

    Push-Location $workDir

    # 1. ✅ 清除除指定文件外的所有文件
    Get-ChildItem -File | Where-Object {
        -not ($_ .Name -eq 'TCLUS') -and
        -not ($_ .Name -eq 'TNOCLUS') -and
        -not ($_ .Name -eq 'DELPCT') -and
        -not ($_ .Name -eq 'CLUSTER') -and
        -not ($_ .Name -eq 'CLUSTERno') -and
        -not ($_ .Name -eq 'INFILE') -and
        -not ($_ .Name -eq 'CLUSEND') -and
        -not ($_ .Name -eq 'CMESSAGE') -and
        -not ($_ .Name -like 'clusplot_*.html')
    } | Remove-Item -Force -Verbose

    # 2. 🧠 运行 select_K.py 获取新 K
    $select_k  = Join-Path $ScriptsDir 'select_K.py'
    $file_tsv  = Join-Path $workDir 'DELPCT'
    $Kstr      = & $PythonExe $PyVersionArgs $select_k $file_tsv --min 1 --max 15 --S 1.0 --online
    $K         = try { [int]$Kstr.Trim() } catch { 3 }
    Write-Host "[$pt] 使用 K = $K" -ForegroundColor Yellow

    # 3. 执行 cluslist.exe
    & "$ExecDir\cluslist.exe" "-iCLUSTER" "-n$K" "-oCLUSLIST"
    if (!(Test-Path 'CLUSLIST')) { Write-Warning "CLUSLIST 未生成"; Pop-Location; return }

    # 4. 执行 clusmem.exe 并重命名结果
    & "$ExecDir\clusmem.exe" "-iCLUSLIST"
    Rename-Item -Path 'CLUSLIST' -NewName "CLUSLIST_$K" -Force

    # 5. create_traj_tmp.py 脚本生成临时 TRAJ.INP.C*
    Push-Location $ScriptsDir
    & $PythonExe $PyVersionArgs 'create_traj_tmp.py' '-d' $workDir
    Pop-Location

    Push-Location $workDir
    $meanFiles = @()

    # 6. 使用 trajmean.exe 生成每个 mean 文件并清理 tmp
    Get-ChildItem -Filter 'TRAJ.INP.C*' | ForEach-Object {
        $cxname = $_.Name
        if ($cxname -match 'TRAJ\.INP\.(C\d+_\d+)') { $core = $Matches[1] } else { $core = $cxname }
        $output = "${core}_mean"
        $cmd = "$TrajmeanExe -i+`"$cxname`" -o$output -m0 -v$TrajmeanV"
        Write-Host "    [trajmean] CMD: $cmd" -ForegroundColor Magenta
        iex $cmd
        $meanFiles += $output

        Get-Content $cxname | Where-Object { $_ -match '\\' } | ForEach-Object {
            $tmp = $_.TrimEnd()
            if (Test-Path $tmp) { Remove-Item $tmp -Force -Verbose }
        }
    }

    # 7. 🛠 合并 mean 文件
    if ($meanFiles.Count -gt 0) {
        $inputList   = $meanFiles -join '+'
        $mergedBase  = 'merged_mean'
        $cmd2        = "$MerglistExe -i$inputList -o$mergedBase"
        Write-Host "[merglist] CMD: $cmd2" -ForegroundColor Cyan
        iex $cmd2
        Write-Host "[merglist] 合并完成, 输出基名: $mergedBase"
    } else {
        Write-Warning "[merglist] 未找到 mean 文件, 跳过合并"
    }

    # 8. 📈 调用 trajplot.exe 绘制平均轨迹图
    $label = "${YearStart}_${YearEnd}_${MonTag}_$pt"
    $cmd3 = "$TrajplotExe --% -a3 -A3 -f0 +g1 -i""merged_mean.tdump"" -j""C:/hysplit/graphics/arlmap"" -oTRAJMEAN -k3 -l24 -L1 -m0 -s1 -v4 -z67"
    Write-Host "[trajplot] CMD: $cmd3" -ForegroundColor Green
    iex $cmd3
    Rename-Item -Path 'TRAJMEAN.html'       -NewName "${label}_TRAJMEAN.html" -Force
    Rename-Item -Path 'TRAJMEAN_01.kml'    -NewName "${label}_TRAJMEAN.kml"  -Force
    Write-Host "[trajplot] 图生成完成 -> ${label}_TRAJMEAN.html" -ForegroundColor Green

    Pop-Location
}
