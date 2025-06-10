import cdsapi
import os
import time
import calendar
import threading
from subprocess import call

# 设置下载文件夹路径
# Set download folder path
output_folder = r"F:\ERA5_pressure_level"
os.makedirs(output_folder, exist_ok=True)

# 设置记录已提交任务的文件路径
# Set path for file recording submitted tasks (including filenames and download URLs)
submitted_tasks_file = os.path.join(output_folder, "submitted_tasks.txt")

# 读取已提交任务的记录
# Read records of submitted tasks
if os.path.exists(submitted_tasks_file):
    with open(submitted_tasks_file, "r") as f:
        submitted_tasks = set(line.strip().split(' | ')[0] for line in f)
else:
    submitted_tasks = set()

# 初始化CDS API客户端
# Initialize CDS API client
client = cdsapi.Client()

# 定义数据集和基本请求参数
# Define dataset and basic request parameters
# Variable names (e.g. temperature) can be found on ERA5 website
dataset = "reanalysis-era5-pressure-levels"
base_request = {
    "product_type": ["reanalysis"],
    "variable": [
        "geopotential", "relative_humidity", "specific_humidity",
        "temperature", "u_component_of_wind", "v_component_of_wind",
        "vertical_velocity"
    ],
    "time": ["00:00", "06:00", "12:00", "18:00"],
    "pressure_level": [
        "1", "3", "7", "20", "50", "100", "150", "200", "250",
        "350", "450", "550", "650", "750", "800", "850", "900", "950", "1000"
    ],
    "data_format": "grib",
    "download_format": "unarchived",
    "area": [90, -25, 0, 180]
}

# 定义使用IDM下载的函数
# Define function for downloading with IDM
def idmDownloader(task_url, folder_path, file_name):
    idm_engine = r"D:\Internet Download Manager\IDMan.exe"
    # 添加下载任务
    # Add download task
    call([idm_engine, '/d', task_url, '/p', folder_path, '/f', file_name, '/a'])
    # 开始下载任务
    # Start download task
    call([idm_engine, '/s'])

# 定义下载任务的函数
# Define download task function
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
        # 等待文件下载完成
        # Wait for download to complete
        while not os.path.exists(filepath):
            time.sleep(10)
        print(f"✔ {filename} 下载完成。")
        print(f"✔ {filename} download completed.")
        # 记录下载链接
        # Record filename and download URL
        with open(submitted_tasks_file, "a") as f:
            f.write(f"{filename} | {download_url}\n")
    except Exception as e:
        print(f"下载 {filename} 时发生错误：{e}")
        print(f"Error occurred while downloading {filename}: {e}")

# 设置下载时间范围
# Set download time range
# Note: ERA5 has a limit of 150 concurrent download tasks
start_year = 1950
end_year = 1953
for year in range(start_year -1 , end_year + 1):  
    # 特殊处理起始年份（用于HYSPLIT后向轨迹计算）
    # Special handling for start year (for HYSPLIT back trajectory calculation)
    if year == start_year - 1:
        month_range = [12]  # 仅下载12月数据 / Only download December data
    else:
        month_range = range(1, 13)  # 其他年份下载1-12月数据 / Download Jan-Dec for other years
    
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
                continue  # 跳过空的部分 / Skip empty parts
            # 输出的文件名
            # Output filename
            filename = f"north_6h_pressure_{ym}_{mm}_p{idx}.grib" 
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
            # If file already exists, skip
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
            # Wait time between requests
            time.sleep(5)

print("\n所有任务已提交。")
print("\nAll tasks submitted.")