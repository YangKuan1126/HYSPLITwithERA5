# 设置 HYSPLIT 可执行文件路径
$HYSPLIT_EXEC = "C:\hysplit\exec\hyts_std.exe"

# 设置气象数据和轨迹输出的基本目录
$METEO_DIR = "G:\ERA5_pressure_levels"
$TRAJ_BASE_DIR = "G:\traj"

# 创建输出目录（如果不存在）
foreach ($year in 1971..1973) {
    $TRAJ_DIR = Join-Path $TRAJ_BASE_DIR $year
    if (!(Test-Path -Path $TRAJ_DIR)) {
        New-Item -ItemType Directory -Path $TRAJ_DIR
    }
}

# 定义需要处理的月份
$monthsToProcess = @(1, 5, 9)

# 遍历年份和指定月份
foreach ($year in 1971..1973) {
    foreach ($month in $monthsToProcess) {
        # 设置起始日期为该月1日00:00
        $startDate = Get-Date -Year $year -Month $month -Day 1 -Hour 0 -Minute 0 -Second 0

        # 设置结束日期为该月10日18:00
        $endDate = Get-Date -Year $year -Month $month -Day 10 -Hour 18 -Minute 0 -Second 0

        # 设置时间间隔（6小时）
        $interval = New-TimeSpan -Hours 6

        # 初始化当前时间为起始时间
        $currentTime = $startDate

        while ($currentTime -le $endDate) {
            $yy = $currentTime.ToString("yy")
            $mm = $currentTime.ToString("MM")
            $dd = $currentTime.ToString("dd")
            $hh = $currentTime.ToString("HH")
            $tag = "shit$yy$mm$dd$hh"

            # 构建 CONTROL 文件内容
            $controlContent = @()
            $controlContent += "$yy $mm $dd $hh"
            $controlContent += "10"
            $controlContent += "33.140 107.160     0.5"
            $controlContent += "33.300 109.800     0.5"
            $controlContent += "32.800 111.200     0.5"
            $controlContent += "32.630 112.410     0.5"
            $controlContent += "31.300 112.540     0.5"
            $controlContent += "30.600 114.300     0.5"
            $controlContent += "34.000 107.500     0.5"
            $controlContent += "33.880 109.000     0.5"
            $controlContent += "32.480 109.540     0.5"
            $controlContent += "32.100 111.300     0.5"
            $controlContent += "-240"
            $controlContent += "0"
            $controlContent += "10000.0"
            $controlContent += "2"

            # 添加气象数据文件路径
            # 前一个月的第三个时期
            $prevMonth = $month - 1
            $prevYear = $year
            if ($prevMonth -eq 0) {
                $prevMonth = 12
                $prevYear = $year - 1
            }
            $prevMonthStr = "{0:D2}" -f $prevMonth
            $controlContent += "$METEO_DIR\"
            $controlContent += "north_6h_${prevYear}_${prevMonthStr}_p3.arl"

            # 当前月的第一个时期
            $monthStr = "{0:D2}" -f $month
            $controlContent += "$METEO_DIR\"
            $controlContent += "north_6h_${year}_${monthStr}_p1.arl"

            # 添加输出目录和文件名
            $TRAJ_DIR = Join-Path $TRAJ_BASE_DIR $year
            $controlContent += "$TRAJ_DIR\"
            $controlContent += $tag

            # 写入 CONTROL 文件
            $controlContent | Set-Content -Path ".\CONTROL"

            # 创建临时文件路径用于重定向输出
            $stdoutFile = [System.IO.Path]::GetTempFileName()
            $stderrFile = [System.IO.Path]::GetTempFileName()

            # 运行 HYSPLIT，并将输出重定向到临时文件，避免在终端显示进度信息
            Start-Process -FilePath $HYSPLIT_EXEC `
                          -NoNewWindow `
                          -Wait `
                          -RedirectStandardOutput $stdoutFile `
                          -RedirectStandardError $stderrFile

            # 删除临时文件
            Remove-Item $stdoutFile, $stderrFile -Force
            Write-Host "***COMPLETED***:$tag"
            # 增加当前时间
            $currentTime = $currentTime.Add($interval)
        }
    }
}
