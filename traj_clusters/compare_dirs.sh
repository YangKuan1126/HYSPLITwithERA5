#!/usr/bin/env bash
#
# compare_dirs.sh  —— 仅列出 “只在目录 A 存在而目录 B 没有” 的文件名
# 用法：
#   ./compare_dirs.sh  <dirA> <dirB> <out_txt>       # 仅比较顶层文件
#   ./compare_dirs.sh  -r <dirA> <dirB> <out_txt>    # 递归比较所有子目录文件
#
# 例：
#   ./compare_dirs.sh -r \
#       "/mnt/f/ERA5_pressure_level/traj/1950" \
#       "/mnt/f/ERA5_pressure_level/traj_points/1950/P1" \
#       "/mnt/d/github/HYSPLITwithERA5/traj_clusters/only_in_A.txt"

set -euo pipefail

# ------------------- 参数解析 --------------------------
recurse=false
if [[ $1 == "-r" ]]; then
    recurse=true
    shift
fi

if [[ $# -ne 3 ]]; then
    echo "用法: $0 [-r] <dirA> <dirB> <out_txt>"
    exit 1
fi

dirA="$1"
dirB="$2"
outfile="$3"

# ------------------- 路径检查 --------------------------
if [[ ! -d $dirA ]]; then
    echo "❌ 目录 A 不存在: $dirA" >&2; exit 1
fi
if [[ ! -d $dirB ]]; then
    echo "❌ 目录 B 不存在: $dirB" >&2; exit 1
fi
mkdir -p "$(dirname "$outfile")"

# ------------------- 收集文件名 ------------------------
if $recurse; then
    listA=$(find "$dirA" -type f -printf '%f\n' | sort -u)
    listB=$(find "$dirB" -type f -printf '%f\n' | sort -u)
else
    listA=$(find "$dirA" -maxdepth 1 -type f -printf '%f\n' | sort -u)
    listB=$(find "$dirB" -maxdepth 1 -type f -printf '%f\n' | sort -u)
fi

countA=$(echo "$listA" | wc -l)
countB=$(echo "$listB" | wc -l)
echo "A 目录文件数: $countA"
echo "B 目录文件数: $countB"

# ------------------- 取差集并写文件 --------------------
onlyA=$(comm -23 <(echo "$listA") <(echo "$listB"))
cnt=$(echo "$onlyA" | grep -c '^' || true)

if [[ $cnt -eq 0 ]]; then
    echo "⚠️  未发现仅存在于 A 的文件。"
    : > "$outfile"        # 建空文件，保持脚本一致性
else
    echo "$onlyA" > "$outfile"
    echo "✅ 已写入差异清单 ($cnt 条): $outfile"
fi
