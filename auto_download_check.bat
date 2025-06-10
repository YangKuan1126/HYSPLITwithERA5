@echo off
setlocal enabledelayedexpansion

REM 设置 Python 路径 | Set Python path
set PYTHON3_PATH=D:\Pyton3.9.6\python.exe

REM 设置脚本路径 | Set script paths
set DOWNLOAD_SCRIPT=F:\ERA5_Downlaods_Scripts\1.ERA5_6h_pressure_level_1month-WEEKLY.py
set CONTINUE_SCRIPT=F:\ERA5_Downlaods_Scripts\4.WEEKLY_continue.py
set DOWNLOAD_SINGLE_SCRIPT=F:\ERA5_Downlaods_Scripts\5.ERA5_6h_single_level_WEEKLY.py

REM 初次下载数据 | Initial data download
echo Running initial download script...
echo 正在运行初始下载脚本...
%PYTHON3_PATH% "%DOWNLOAD_SCRIPT%"

REM 执行 WSL 中的 check_grib.sh（仅执行一次）| Run check_grib.sh in WSL (once only)
echo Running check_grib.sh in WSL...
echo 正在WSL中运行check_grib.sh...
wsl bash -c "/mnt/f/ERA5_Downlaods_Scripts/2.check_grib.sh"

:loop
REM 执行 Python 脚本重新下载不完整的文件 | Run Python script to redownload incomplete files
echo Running WEEKLY_continue.py...
echo 正在运行WEEKLY_continue.py...
%PYTHON3_PATH% "%CONTINUE_SCRIPT%"

REM 执行 WSL 中的 check_incomplete_gribs.sh，更新 incomplete_grib_files.txt
REM Run check_incomplete_gribs.sh in WSL to update incomplete_grib_files.txt
echo Running check_incomplete_gribs.sh in WSL...
echo 正在WSL中运行check_incomplete_gribs.sh...
wsl bash -c "/mnt/f/ERA5_Downlaods_Scripts/3.check_incomplete_grib.sh"

REM 检查 incomplete_grib_files.txt 是否为空 | Check if incomplete_grib_files.txt is empty
wsl bash -c "test -s /mnt/f/ERA5_Downlaods_Scripts/incomplete_grib_files.txt"
if %ERRORLEVEL% EQU 0 (
    echo Incomplete files remain. Continuing loop...
    echo 仍有不完整文件存在。继续循环...
    timeout /t 5 > nul
    goto loop
) else (
    echo All files are complete. Exiting loop.
    echo 所有文件已完成。退出循环。
)

endlocal

REM 执行 single_level 下载任务 | Run single_level download task
echo Running 5.ERA5_6h_single_level_WEEKLY.py ...
echo 正在运行5.ERA5_6h_single_level_WEEKLY.py...
%PYTHON3_PATH% "%DOWNLOAD_SINGLE_SCRIPT%"
pause