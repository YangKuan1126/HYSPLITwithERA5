#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import re
import argparse
from pathlib import Path

def process_trajectory_file(orig_path):
    """处理单个轨迹文件，生成带 _tmp 后缀的新文件。成功返回新文件路径，失败返回None。"""
    try:
        with open(orig_path, 'r') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"警告: 无法读取文件 {orig_path}，已跳过。")
        return None

    # 标志行索引
    omega_idx = None  # "FORWARD/BACKWARD OMEGA" 行索引
    label_idx = None  # 包含 PRESSURE MIXDEPTH SPCHUMID 的行索引
    num_traj = 1      # 轨迹数量（默认1）

    # 查找 OMEGA 行（方向和垂直运动方法行）
    for i, line in enumerate(lines):
        if ("OMEGA" in line) and ("FORWARD" in line or "BACKWARD" in line):
            omega_idx = i
            # 提取轨迹数量（行首I6整数）
            try:
                num_traj = int(line.strip().split()[0])
            except:
                num_traj = 1
            break
    if omega_idx is None:
        print(f"警告: 文件 {orig_path} 格式异常（未找到 OMEGA 行），已跳过。")
        return None

    # 起始点信息行索引为 OMEGA 行的下一行开始，共 num_traj 行
    start_info_indices = list(range(omega_idx + 1, omega_idx + 1 + num_traj))
    # 诊断变量标签行应位于起始点信息行之后
    search_start = omega_idx + 1 + num_traj
    for j in range(search_start, len(lines)):
        if "PRESSURE" in lines[j] and "MIXDEPTH" in lines[j] and "SPCHUMID" in lines[j]:
            label_idx = j
            break
    if label_idx is None:
        print(f"警告: 文件 {orig_path} 格式异常（未找到诊断变量标签行），已跳过。")
        return None

    # 提取第一条数据行的起始高度（高度为倒数第4列）
    data_start_idx = label_idx + 1
    if data_start_idx >= len(lines):
        print(f"警告: 文件 {orig_path} 内容不完整（缺少数据行），已跳过。")
        return None
    first_data_line = lines[data_start_idx].rstrip('\n')  # 去除换行便于处理
    data_tokens = first_data_line.strip().split()
    if len(data_tokens) < 4:
        print(f"警告: 文件 {orig_path} 数据行格式异常，已跳过。")
        return None
    start_height = data_tokens[-4]  # 起始高度值字符串

    # 修改诊断变量标签行："3 PRESSURE MIXDEPTH SPCHUMID" -> "1 PRESSURE"
    original_label_line = lines[label_idx].rstrip('\n')
    # 构造新标签行，保持原始缩进和格式
    try:
        # 原行开头I6数值改为1（占6列宽度）
        new_label_num = f"{1:6d}"
    except:
        new_label_num = "     1"  # 回退方案，6列右对齐数字1
    new_label_line = new_label_num + " PRESSURE"
    # 如原行有换行则补回换行
    if lines[label_idx].endswith('\n'):
        new_label_line += '\n'
    lines[label_idx] = new_label_line

    # 更新每个起始点信息行的高度值为提取的起始高度
    for idx in start_info_indices:
        line_content = lines[idx].rstrip('\n')
        # 用正则匹配最后一个非空字段及其前的空白
        match = re.search(r'(\S+)(\s*)$', line_content)
        if match:
            prefix = line_content[:match.start(1)]   # 最后值之前的部分（含前导空格）
            old_val = match.group(1)                # 原最后一个值（高度）
            suffix_spaces = match.group(2)          # 原值后面的空格（如果有）
            # 将新的起始高度字符串按原值长度右对齐，以保留列位置
            new_val = start_height.rjust(len(old_val))
            line_content = prefix + new_val + suffix_spaces
        # 恢复换行符
        if lines[idx].endswith('\n'):
            line_content += '\n'
        lines[idx] = line_content

    # 删除每条数据行最后两列（MIXDEPTH和SPCHUMID）
    for k in range(data_start_idx, len(lines)):
        # 停止于下一段非数据内容（一般文件结尾或下一个轨迹开始）
        # 若存在多个轨迹，数据行在轨迹间可能交错，此处简单假定此文件内同属一个轨迹集合
        line = lines[k]
        if not line.strip():
            # 空白行或无内容则跳过
            continue
        # 去除末尾换行进行处理
        has_newline = line.endswith('\n')
        content = line.rstrip('\n')
        # 用正则去掉最后两个以空格分隔的字段
        content_new = re.sub(r'\s+\S+\s+\S+\s*$', '', content)
        if has_newline:
            content_new += '\n'
        lines[k] = content_new

    # 写入修改后的内容到 _tmp 文件
    orig_path = Path(orig_path)
    tmp_path = orig_path.parent / (orig_path.name + "_tmp")
    try:
        with open(tmp_path, 'w') as f_out:
            f_out.writelines(lines)
    except Exception as e:
        print(f"警告: 写入文件 {tmp_path} 失败：{e}")
        return None

    return tmp_path

def main():
    parser = argparse.ArgumentParser(description="批量转换 HYSPLIT 轨迹文件为_tmp格式")
    parser.add_argument("-d", "--dir", required=True, help="包含 TRAJ.INP.C* 文件的目录")
    args = parser.parse_args()
    base_dir = Path(args.dir)
    if not base_dir.is_dir():
        print("错误: 提供的目录无效！")
        return

    # 查找目录下的 TRAJ.INP.C* 文件
    trajinp_files = sorted(base_dir.glob("TRAJ.INP.C*"))
    if not trajinp_files:
        print("错误: 指定目录中未找到 TRAJ.INP.C* 文件！")
        return

    # 记录已处理的轨迹文件，避免重复处理
    processed_map = {}  # {原始路径字符串: 新路径字符串或 None}
    for inp_file in trajinp_files:
        # 读取列表文件内容
        try:
            with open(inp_file, 'r') as fin:
                lines = fin.readlines()
        except Exception as e:
            print(f"警告: 无法读取列表文件 {inp_file}，已跳过。")
            continue

        new_lines = []
        modified = False
        for line in lines:
            stripped = line.strip()
            if not stripped:
                # 空行原样保留
                new_lines.append(line)
                continue
            traj_path_str = stripped  # 原轨迹文件路径（字符串形式）
            # 判断是否已处理过
            if traj_path_str in processed_map:
                new_path_str = processed_map[traj_path_str]
                if new_path_str:
                    # 已成功处理过，直接替换为 _tmp 路径
                    new_lines.append(new_path_str + ("\n" if line.endswith("\n") else ""))
                    modified = True
                else:
                    # 处理过但失败（返回None），保留原路径
                    new_lines.append(line)
                continue

            # 第一次遇到该轨迹文件路径，尝试处理
            # 将相对路径转换为绝对路径（相对于基目录）
            traj_path = Path(traj_path_str)
            if not traj_path.is_absolute():
                traj_path = base_dir / traj_path
            # 处理轨迹文件
            tmp_file = process_trajectory_file(traj_path)
            if tmp_file is None:
                # 处理失败，保留原路径
                processed_map[traj_path_str] = None
                new_lines.append(line)
            else:
                # 处理成功，替换路径为新文件
                new_path_str = str(tmp_file)
                # 为保持与原列表格式一致（如原是相对路径），去掉基目录前缀
                if not traj_path_str.startswith(os.sep):
                    # 相对路径场景下，只使用文件名和后缀
                    new_path_str = traj_path_str + "_tmp"
                processed_map[traj_path_str] = new_path_str
                new_lines.append(new_path_str + ("\n" if line.endswith("\n") else ""))
                modified = True

        # 将更新后的列表写回文件
        try:
            with open(inp_file, 'w') as fout:
                fout.writelines(new_lines)
            if modified:
                print(f"已更新列表文件: {inp_file.name}")
        except Exception as e:
            print(f"警告: 写入列表文件 {inp_file} 失败：{e}")

if __name__ == "__main__":
    main()
