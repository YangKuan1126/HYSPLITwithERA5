#!/usr/bin/env python3
"""
remove_incomplete_traj.py

检查每个轨迹文件的最后一条记录第9列：
  - 若 == 240.0 或 == -240.0 则视为完整；
  - 否则视为不完整，需要删除。

用法：
  # 仅演示（不会删除）
  python remove_incomplete_traj.py \
    --base_dir "F:\ERA5_pressure_level\traj_points" \
    --dry_run

  # 正式执行删除
  python remove_incomplete_traj.py \
    --base_dir "F:\ERA5_pressure_level\traj_points"
"""

import os
import argparse

def get_last_val(filepath):
    """
    读取文件最后一条非空记录的第9列（索引8）并返回浮点数。
    如果没有有效行或转换失败，返回 None。
    """
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    for line in reversed(lines):
        parts = line.strip().split()
        if len(parts) >= 9:
            try:
                return float(parts[8])
            except ValueError:
                return None
    return None

def find_and_delete(base_dir, dry_run=True):
    """
    遍历 base_dir 下所有文件，针对不完整轨迹文件：
      - dry_run=True  只打印 “Would delete: … (last_val=…)”
      - dry_run=False 打印 “Deleting: … (last_val=…)” 并实际删除
    """
    to_delete = []

    for root, _, files in os.walk(base_dir):
        for fname in files:
            fpath = os.path.join(root, fname)
            if not os.path.isfile(fpath):
                continue

            last_val = get_last_val(fpath)
            # 如果最后一列既不是 240.0 也不是 -240.0，即视为不完整
            if last_val not in (240.0, -240.0):
                to_delete.append(fpath)
                if dry_run:
                    print(f"Would delete: {fpath}  (last_val={last_val})")
                else:
                    print(f"Deleting:    {fpath}  (last_val={last_val})")
                    try:
                        os.remove(fpath)
                    except Exception as e:
                        print(f"  ERROR deleting {fpath}: {e}")

    label = "to delete" if dry_run else "deleted"
    print(f"\nTotal files {label}: {len(to_delete)}")
    if not dry_run:
        print("Deletion complete.")

def main():
    parser = argparse.ArgumentParser(
        description="删除最后一条记录第9列不为 ±240.0 的轨迹文件"
    )
    parser.add_argument(
        '--base_dir', '-b',
        required=True,
        help="轨迹数据根目录，例如 F:\\ERA5_pressure_level\\traj_points"
    )
    parser.add_argument(
        '--dry_run', '-n',
        action='store_true',
        help="仅打印将要删除的文件，不实际删除"
    )
    args = parser.parse_args()

    find_and_delete(args.base_dir, dry_run=args.dry_run)

if __name__ == '__main__':
    main()
