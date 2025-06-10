import os
import time
from subprocess import call

# 设置 IDM 的可执行文件路径
# Set path to IDM executable
IDM_PATH = r"D:\Internet Download Manager\IDMan.exe"

# 设置记录已提交任务的文件路径
# Set path to file recording submitted tasks
submitted_tasks_file = r"G:\ERA5_pressure_levels\submitted_tasks.txt"

# 设置不完整的 GRIB 文件列表路径
# Set path to list of incomplete GRIB files
incomplete_files_list = r"G:\incomplete_grib_files.txt"

# 读取 submitted_tasks.txt，创建文件名到下载链接的映射
# Read submitted_tasks.txt and create filename to URL mapping
submitted_tasks = {}
with open(submitted_tasks_file, "r") as f:
    for line in f:
        parts = line.strip().split(" | ")
        if len(parts) == 2:
            filename, url = parts
            submitted_tasks[filename] = url

# 读取不完整的 GRIB 文件列表
# Read list of incomplete GRIB files
with open(incomplete_files_list, "r") as f:
    incomplete_files = [line.strip() for line in f if line.strip()]

# 存储需要重新下载的文件路径
# Store files that need to be re-downloaded
files_to_check = []

# 处理每个不完整的 GRIB 文件
# Process each incomplete GRIB file
for grib_path in incomplete_files:
    # 将 WSL 路径转换为 Windows 路径
    # Convert WSL path to Windows path
    if grib_path.startswith("/mnt/"):
        drive_letter = grib_path[5]
        windows_path = drive_letter.upper() + ":" + grib_path[6:].replace("/", "\\")
    else:
        windows_path = grib_path  # 如果已经是 Windows 路径 / If already Windows path

    if not os.path.isfile(windows_path):
        print(f"文件不存在，跳过：{windows_path}")
        print(f"File does not exist, skipping: {windows_path}")
        continue

    # 获取文件名
    # Get filename
    filename = os.path.basename(windows_path)

    # 查找对应的下载链接
    # Find corresponding download URL
    download_url = submitted_tasks.get(filename)
    if not download_url:
        print(f"未找到下载链接，跳过：{filename}")
        print(f"Download URL not found, skipping: {filename}")
        continue

    # 删除不完整的 GRIB 文件
    # Delete incomplete GRIB file
    try:
        os.remove(windows_path)
        print(f"已删除不完整的文件：{windows_path}")
        print(f"Deleted incomplete file: {windows_path}")
    except Exception as e:
        print(f"删除文件时出错：{windows_path}，错误信息：{e}")
        print(f"Error deleting file: {windows_path}, error: {e}")
        continue

    # 使用 IDM 添加下载任务
    # Add download task using IDM
    call([IDM_PATH, '/d', download_url, '/p', os.path.dirname(windows_path), '/f', filename, '/a'])
    print(f"已添加下载任务：{filename}")
    print(f"Added download task: {filename}")

    # 添加到检查列表
    # Add to check list
    files_to_check.append(windows_path)

# 开始所有下载任务
# Start all download tasks
call([IDM_PATH, '/s'])
print("已启动所有下载任务。")
print("Started all download tasks.")

# 等待所有文件下载完成
# Wait for all files to finish downloading
print("等待所有文件下载完成...")
print("Waiting for all files to finish downloading...")
while True:
    incomplete = [f for f in files_to_check if not os.path.exists(f)]
    if not incomplete:
        break
    time.sleep(10)
print("所有文件已下载完成。")
print("All files have finished downloading.")