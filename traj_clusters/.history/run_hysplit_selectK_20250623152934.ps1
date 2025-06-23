Param(
    [string] $RootDir = 'F:\ERA5_pressure_level\traj_clusters',
    [string] $ScriptsDir = 'D:\Github\HYSPLITwithERA5\traj_clusters',
    [string] $PythonExe = 'py',
    [string] $PyVersionArgs = '-3.9',
    [string] $ExecDir = 'C:\hysplit\exec',
    [string] $TrajmeanExe = 'C:\hysplit\exec\trajmean.exe',
    [string] $TrajmeanV = '0'
)

Get-ChildItem -Path $RootDir -Directory | ForEach-Object {
    $pt = $_.Name
    $workDir = $_.FullName
    Write-Host "`n=== 任务：$pt ===" -ForegroundColor Cyan

    Push-Location $workDir

    # 🗑️ 清理旧文件：保留特定文件，其余删除
    Get-ChildItem -File | Where-Object {
        -not ($_ -match '^TCLUS$') -and
        -not ($_ -match '^TNOCLUS$') -and
        -not ($_ -match '^DELPCT$') -and
        -not ($_ -match '^CLUSTER$') -and
        -not ($_ -match '^CLUSTERno$') -and
        -not ($_ -match '^INFILE$') -and
        -not ($_ -match '^CLUSEND$') -and
        -not ($_ -match '^CMESSAGE$') -and
        -not ($_ -like 'clusplot_*.html')
    } | Remove-Item -Force -Verbse

    # 获取新的 K 并执行后续步骤...
    $select_k = Join-Path $ScriptsDir 'select_K.py'
    $file_tsv = Join-Path $workDir 'DELPCT'
    $Kstr = & $PythonExe $PyVersionArgs $select_k $file_tsv --min 1 --max 15 --S 1.0 --online
    $K = try { [int]$Kstr.Trim() } catch { 3 }
    Write-Host "[$pt] 使用 K = $K" -ForegroundColor Yellow

    & "$ExecDir\cluslist.exe" "-iCLUSTER" "-n$K" "-oCLUSLIST"
    if (!(Test-Path 'CLUSLIST')) { Write-Warning "CLUSLIST 未生成"; Pop-Location; return }

    & "$ExecDir\clusmem.exe" "-iCLUSLIST"
    Rename-Item -Path 'CLUSLIST' -NewName "CLUSLIST_$K" -Force

    Push-Location $ScriptsDir
    & $PythonExe $PyVersionArgs 'create_traj_tmp.py' '-d' $workDir
    Pop-Location

    Push-Location $workDir
    Get-ChildItem -Filter 'TRAJ.INP.C*' | ForEach-Object {
        $cxname = $_.Name
        if ($cxname -match 'TRAJ\.INP\.(C\d+_\d+)') { $core = $Matches[1] } else { $core = $cxname }
        $output = "${core}_mean"
        $cmd = "$TrajmeanExe -i+`"$cxname`" -o$output -m0 -v$TrajmeanV"
        Write-Host "    执行: $cmd" -ForegroundColor Magenta
        iex $cmd

        Get-Content $cxname | Where-Object { $_ -match '\\' } | ForEach-Object {
            $tmp = $_.TrimEnd()
            if (Test-Path $tmp) { Remove-Item $tmp -Force -Verbose }
        }
    }
    Pop-Location

    Pop-Location
}
