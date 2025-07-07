# meta_cluster_mean.py
# -*- coding: utf-8 -*-
"""
把 C?_M_mean（同一 meta-cluster 内含多条后向轨迹）再求平均，
输出 HYSPLIT 兼容的 C?_META_mean.tdump（240 行平均轨迹）。

用法:
    python meta_cluster_mean.py <meta_dir>

    <meta_dir> 形如  F:\ERA5_pressure_level\traj_clusters\1979_2020_01_META
"""

import sys, re, pathlib, numpy as np

# ---------- 正则表达式 ----------
RE_HEAD  = re.compile(r'^\s*\d+\s+BACKWARD')   # "3 BACKWARD …"
RE_PRESS = re.compile(r'^\s*1\s+PRESSURE')
RE_TRACK = re.compile(r'^\s*\d+\s+-9')         # 轨迹记录行

def split_blocks(lines):
    """
    把整文件拆成若干 blocks，每个 block 为 list[str] (含 header+PRESSURE段)。
    返回 header_lines, blocks (list of list[str])
    """
    head_i  = next(i for i,l in enumerate(lines) if RE_HEAD.search(l))
    press_i = next(i for i,l in enumerate(lines[head_i+1:], head_i+1) if RE_PRESS.search(l))
    header  = lines[:press_i]   # 从文件开头到 PRESSURE 前一行
    blocks  = []
    cur = []
    for l in lines[press_i:]:
        if RE_TRACK.match(l) and cur:          # 新轨迹开始
            blocks.append(cur)
            cur = [l]
        else:
            cur.append(l)
    if cur:
        blocks.append(cur)
    return header, blocks

def track_to_array(block):
    """
    把一个 PRESSURE block 转成 ndarray shape (240, 4):
    col0: hour(int负值), col1: lat, col2: lon, col3: press
    """
    rows = []
    for l in block:
        if RE_TRACK.match(l):
            t = l.split()
            hr   = int(float(t[8]))            # -1 -2 … -240
            lat, lon, prs = map(float, t[-3:])
            rows.append((hr, lat, lon, prs))
    rows.sort(key=lambda r: r[0])              # 升序(-1,-2,…)
    return np.array(rows)

def array_to_block(arr, template_block):
    """
    使用 template_block 的格式，把均值数组写回为 PRESSURE block，
    并返回 list[str] (含 PRESSURE 行和 240 个轨迹行)。
    """
    out = []
    out.append(template_block[0])              # 复制 "1 PRESSURE"
    fmt_line = template_block[1]               # 用第一条轨迹作为格式模板
    parts    = fmt_line.rstrip('\n').split()
    for i, (hr, lat, lon, prs) in enumerate(arr, 1):
        new_parts = parts.copy()
        new_parts[0]  = f"{i:5d}"              # 重新编号 1…240
        new_parts[8]  = f"{hr:5.1f}"           # 小时列
        new_parts[-3] = f"{lat:8.3f}"
        new_parts[-2] = f"{lon:9.3f}"
        new_parts[-1] = f"{prs:8.1f}"
        out.append(" ".join(new_parts) + '\n')
    return out

def process_one_file(fpath: pathlib.Path):
    text = fpath.read_text(encoding='utf-8', errors='ignore').splitlines(keepends=True)
    header, blocks = split_blocks(text)

    # 把每条轨迹转为数组并堆叠
    arrs = [track_to_array(b)[:,1:] for b in blocks]   # shape -> (n,240,3)
    arrs = np.stack(arrs, axis=0)
    mean_xyz = arrs.mean(axis=0)                       # shape (240,3)

    # 用第一条轨迹的 PRESSURE 段当模板
    mean_block = array_to_block(
        np.column_stack((np.arange(-1, -241, -1), mean_xyz)), blocks[0]
    )

    # 写输出
    out_path = fpath.with_name(fpath.stem.replace('_M_mean','_META_mean') + '.tdump')
    with out_path.open('w', encoding='utf-8') as fo:
        fo.writelines(header)
        fo.writelines(mean_block)
    print(f"→ {out_path.name}  已生成 (平均 {len(blocks)} 条轨迹)")

def main(meta_dir):
    meta_dir = pathlib.Path(meta_dir)
    if not meta_dir.is_dir():
        sys.exit(f"❌ 目录不存在: {meta_dir}")

    files = sorted(meta_dir.glob('C*_M_mean'))
    if not files:
        sys.exit("❌ 未找到 C*_M_mean 文件")

    for fp in files:
        process_one_file(fp)

    print("✅ 所有 meta-cluster 已完成平均。")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit("用法: python meta_cluster_mean.py <meta_dir>")
    main(sys.argv[1])
