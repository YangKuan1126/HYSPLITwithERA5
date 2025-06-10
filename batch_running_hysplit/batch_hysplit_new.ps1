# 设置 HYSPLIT 可执行文件路径
$HYSPLIT_EXEC = "C:\hysplit\exec\hyts_std.exe"

# 设置气象数据和轨迹输出的基本目录
$METEO_DIR = "G:\ERA5_pressure_levels"
$TRAJ_BASE_DIR = "G:\traj"

# 定义阶段（每阶段四个月）
$phases = @(
    @{ StartMonth = 1; EndMonth = 4 },
    @{ StartMonth = 5; EndMonth = 8 },
    @{ StartMonth = 9; EndMonth = 12 }
)

# 定义需要处理的年份列表（仅处理所列年份）
$years = @(1971, 1972, 1973, 1977, 1978)  # 新增: 指定要处理的年份列表
# 遍历年份列表中的每个年份和阶段
foreach ($year in $years) {  # 修改: 原为 1971..1973，现改为使用年份列表
    foreach ($phase in $phases) {
        $startMonth = $phase.StartMonth
        $endMonth = $phase.EndMonth

        # 设置起始日期为该阶段第一个月的11日00:00
        $startDate = Get-Date -Year $year -Month $startMonth -Day 11 -Hour 0 -Minute 0 -Second 0

        # 设置结束日期为该阶段最后一个月的最后一天18:00
        $endDate = (Get-Date -Year $year -Month $endMonth -Day 1).AddMonths(1).AddDays(-1).AddHours(18)

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
            $controlContent += "12"

            # 添加气象数据文件路径（每月三个文件，共四个月）
            for ($i = $startMonth; $i -le $endMonth; $i++) {
                $monthStr = "{0:D2}" -f $i
                for ($j = 1; $j -le 3; $j++) {
                    $controlContent += "$METEO_DIR\"
                    $controlContent += "north_6h_${year}_${monthStr}_p$j.arl"
                }
            }

            # 添加输出目录和文件名
            $TRAJ_DIR = Join-Path $TRAJ_BASE_DIR $year
            if (!(Test-Path -Path $TRAJ_DIR)) {
                New-Item -ItemType Directory -Path $TRAJ_DIR | Out-Null
            }
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

        # 清理阶段结束后不需要的 .arl 文件
        $monthsToKeep = @(
            @{ Month = $startMonth; Part = 1 },
            @{ Month = $endMonth; Part = 3 }
        )

        for ($i = $startMonth; $i -le $endMonth; $i++) {
            $monthStr = "{0:D2}" -f $i
            for ($j = 1; $j -le 3; $j++) {
                $shouldKeep = $false
                foreach ($keep in $monthsToKeep) {
                    if ($keep.Month -eq $i -and $keep.Part -eq $j) {
                        $shouldKeep = $true
                        break
                    }
                }
                if (-not $shouldKeep) {
                    $fileToDelete = Join-Path $METEO_DIR "north_6h_${year}_${monthStr}_p$j.arl"
                    if (Test-Path $fileToDelete) {
                        Remove-Item $fileToDelete -Force
                        Write-Host "Deleted: $fileToDelete"
                    }
                }
            }
        }
    }
}
