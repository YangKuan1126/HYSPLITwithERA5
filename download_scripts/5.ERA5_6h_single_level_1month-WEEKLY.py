import cdsapi
import os
import time
import calendar
import threading
from subprocess import call

# 设置下载文件夹路径
# Set download directory path
output_folder = r"F:\ERA5_pressure_level"
os.makedirs(output_folder, exist_ok=True)

# 设置记录已提交任务的文件路径
# Set path for recording submitted tasks
submitted_tasks_file = os.path.join(output_folder, "submitted_single_tasks.txt")

# 读取已提交任务的记录（使用文件名集合）
# Read records of submitted tasks (using filename set)
if os.path.exists(submitted_tasks_file):
    with open(submitted_tasks_file, "r") as f:
        submitted_tasks = set(line.strip() for line in f)
else:
    submitted_tasks = set()

# 初始化CDS API客户端
# Initialize CDS API client
client = cdsapi.Client()

# 定义数据集和基本请求参数（single level）
# Define dataset and basic request parameters (single level)
dataset = "reanalysis-era5-single-levels"
base_request = {
    "product_type": ["reanalysis"],
    "variable": [
        "10m_u_component_of_wind",
        "10m_v_component_of_wind",
        "2m_temperature",
        "surface_pressure"
    ],
    "time": ["00:00", "06:00", "12:00", "18:00"],
    "data_format": "grib",
    "download_format": "unarchived",
    "area": [90, -25, 0, 180]
}

# 使用IDM下载文件的函数
# Function to download files using IDM
def idmDownloader(task_url, folder_path, file_name):
    idm_engine = r"D:\Internet Download Manager\IDMan.exe"
    call([idm_engine, '/d', task_url, '/p', folder_path, '/f', file_name, '/a'])
    call([idm_engine, '/s'])

# 下载任务线程函数
# Thread function for download task
def download_task(client, dataset, req, output_folder, filename, filepath):
    try:
        print(f"\n>> 提交 {filename} 任务……")
        print(f"\n>> Submitting {filename} task...")
        result = client.retrieve(dataset, req)
        download_url = result.location
        if not download_url:
            raise RuntimeError("未能获取下载链接。")
            raise RuntimeError("Failed to get download URL.")
        print(f"✔ 任务完成，开始下载 {filename} ……")
        print(f"✔ Task completed, starting download {filename}...")
        idmDownloader(download_url, output_folder, filename)
        while not os.path.exists(filepath):
            time.sleep(10)
        print(f"✔ {filename} 下载完成。")
        print(f"✔ {filename} download completed.")
    except Exception as e:
        print(f"下载 {filename} 时发生错误：{e}")
        print(f"Error occurred while downloading {filename}: {e}")

# 设置时间范围：2008年 至 2010年
# Set time range: 2008 to 2010
start_year = 1950
end_year = 1953

for year in range(start_year -1 , end_year + 1):  # 包含1996到2000年
    # 特殊处理1996年只下载12月
    # Special handling for 1996 - only download December
    if year == start_year - 1:
        month_range = [12]  # 仅处理12月 / Only process December
    else:
        month_range = range(1, 13)  # 其他年份处理1-12月 / Other years process Jan-Dec
    
    for month in month_range:
        ym = str(year)
        mm = f"{month:02d}"
        days_in_month = calendar.monthrange(year, month)[1]
        day_list = [f"{d:02d}" for d in range(1, days_in_month + 1)]

        # 将一个月的数据分成三部分
        # Split month's data into three parts
        parts = [
            day_list[:10],  # 第1部分：1-10号 / Part 1: 1st-10th
            day_list[10:20],  # 第2部分：11-20号 / Part 2: 11th-20th
            day_list[20:]  # 第3部分：21号到月底 / Part 3: 21st-end of month
        ]

        for idx, days in enumerate(parts, start=1):
            if not days:
                continue  # 跳过空的部分（例如2月的第3部分可能为空）
                # Skip empty parts (e.g. Part 3 might be empty for February)
            filename = f"north_6h_single_{ym}_{mm}_p{idx}.grib"
            filepath = os.path.join(output_folder, filename)

            # 检查对应的 .arl 文件是否存在
            # Check if corresponding .arl file exists
            arl_filename = f"north_6h_{ym}_{mm}_p{idx}.arl"
            arl_filepath = os.path.join(output_folder, arl_filename)
            if os.path.exists(arl_filepath):
                print(f"[跳过] {arl_filename} 已存在，对应的 .grib 文件 {filename} 不再下载。")
                print(f"[Skip] {arl_filename} exists, corresponding .grib file {filename} won't be downloaded.")
                continue

            # 如果文件已存在，跳过
            # If file exists, skip
            if os.path.exists(filepath):
                print(f"[跳过] {filename} 已存在。")
                print(f"[Skip] {filename} already exists.")
                continue

            # 如果任务已提交，跳过
            # If task already submitted, skip
            if filename in submitted_tasks:
                print(f"[跳过] {filename} 已提交。")
                print(f"[Skip] {filename} already submitted.")
                continue

            # 构造请求参数
            # Build request parameters
            req = base_request.copy()
            req["year"] = [ym]
            req["month"] = [mm]
            req["day"] = days
            # 打印关键参数
            # Print key parameters
            print(f"[调试] 请求参数 - 年份: {ym}, 月份: {mm}, 部分: p{idx}, 天数: {len(days)}")
            print(f"[Debug] Request params - Year: {ym}, Month: {mm}, Part: p{idx}, Days: {len(days)}")
            print(f"      日期范围: {days[0]} 至 {days[-1]}")
            print(f"      Date range: {days[0]} to {days[-1]}")

            # 启动下载线程
            # Start download thread
            t = threading.Thread(target=download_task, args=(client, dataset, req, output_folder, filename, filepath))
            t.start()

            # 等待时间
            # Wait time
            time.sleep(5)

print("\n所有任务已提交。")
print("\nAll tasks submitted.")