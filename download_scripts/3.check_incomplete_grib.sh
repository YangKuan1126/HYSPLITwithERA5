#!/bin/bash

# 设置不完整的 GRIB 文件列表路径
# Set path to the incomplete GRIB files list
INCOMPLETE_FILE_LIST="/mnt/f/ERA5_pressure_level/incomplete_grib_files.txt"

# 创建一个临时文件用于存储仍然不完整的文件路径
# Create a temporary file to store still incomplete file paths
TEMP_FILE=$(mktemp)

# 逐行读取不完整的 GRIB 文件路径
# Read incomplete GRIB file paths line by line
while IFS= read -r grib_file; do
    # 检查文件是否存在
    # Check if the file exists
    if [ ! -f "$grib_file" ]; then
        echo "⚠️ 文件不存在，跳过：$grib_file"
        echo "⚠️ File does not exist, skipping: $grib_file"
        echo "$grib_file" >> "$TEMP_FILE"
        continue
    fi

    # 使用 grib_count 获取消息数量
    # Use grib_count to get message count
    count_output=$(grib_count "$grib_file" 2>&1)

    # 检查输出是否为纯数字
    # Check if output is a pure number
    if [[ "$count_output" =~ ^[0-9]+$ ]]; then
        echo "✅ 文件完整，已从列表中移除：$grib_file"
        echo "✅ File is complete, removed from list: $grib_file"
    else
        echo "❌ 文件仍然不完整，保留在列表中：$grib_file"
        echo "❌ File is still incomplete, keeping in list: $grib_file"
        echo "$grib_file" >> "$TEMP_FILE"
    fi
done < "$INCOMPLETE_FILE_LIST"

# 用更新后的列表替换原始文件
# Replace original file with updated list
mv "$TEMP_FILE" "$INCOMPLETE_FILE_LIST"

echo "检查完成。更新后的不完整文件列表已保存至：$INCOMPLETE_FILE_LIST"
echo "Check completed. Updated incomplete files list saved to: $INCOMPLETE_FILE_LIST"