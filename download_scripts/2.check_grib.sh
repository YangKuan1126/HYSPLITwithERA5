#!/bin/bash

# 设置 GRIB 文件所在的目录
# Set the directory where GRIB files are located
GRIB_DIR="/mnt/f/ERA5_pressure_level"

# 设置输出文件路径
# Set the path for the output recording file
OUTPUT_FILE="incomplete_grib_files.txt"

# 清空输出文件
# Clear the output file before each run
> "$OUTPUT_FILE"

# 遍历目录中的所有 GRIB 文件
# Iterate through all GRIB files in the directory
for grib_file in "$GRIB_DIR"/north_6h_pressure_*.grib; do
    # 检查文件是否存在
    # Check if the file exists
    if [ ! -f "$grib_file" ]; then
        continue
    fi

    # 提取文件名（不含路径和扩展名）
    # Extract filename (without path and extension)
    filename=$(basename "$grib_file" .grib)

    # 构造对应的 ARL 文件名
    # Construct corresponding ARL filename:
    # 1. Remove prefix 'north_6h_pressure_'
    # 2. Add prefix 'north_6h_' and extension '.arl'
    arl_filename="north_6h_${filename#north_6h_pressure_}.arl"
    arl_file="${GRIB_DIR}/${arl_filename}"

    # 如果对应的 ARL 文件存在，则跳过检查
    # Skip check if corresponding ARL file already exists
    if [ -f "$arl_file" ]; then
        echo "🔁 已存在 ARL 文件，跳过: $grib_file"
        echo "🔁 ARL file exists, skipping: $grib_file"
        continue
    fi

    # 使用 grib_count 获取消息数量
    # Use grib_count to get message count
    count_output=$(grib_count "$grib_file" 2>&1)

    # 检查输出是否为纯数字
    # Check if output is a pure number
    if [[ ! "$count_output" =~ ^[0-9]+$ ]]; then
        echo "$grib_file" >> "$OUTPUT_FILE"
        echo "❌ 不完整或损坏的文件: $grib_file"
        echo "❌ Incomplete or corrupted file: $grib_file"
    else
        echo "✅ 文件完整: $grib_file"
        echo "✅ File is complete: $grib_file"
    fi
done

echo "检查完成。不完整的文件已记录在 $OUTPUT_FILE 中。"
echo "Check completed. Incomplete files have been recorded in $OUTPUT_FILE."