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
    把一条 PRESSURE block ➜ ndarray (241, 4):
        col0 hour, col1 lat, col2 lon, col3 press
    若行数不足 241 或列数异常返回 None
    """
    rows = []
    for l in block:
        if not l.strip():                 # 跳过空行
            continue
        toks = l.split()
        if len(toks) < 12:                # 行太短视为异常
            continue
        hr   = int(float(toks[8]))        # 0, -1, … -240
        lat  = float(toks[-5])
        lon  = float(toks[-4])
        prs  = float(toks[-3])
        rows.append((hr, lat, lon, prs))

    if len(rows) < 200:                   # 少于 ~240 行则判无效
        return None

    rows.sort(key=lambda r: r[0])         # 按 hr 递增
    return np.array(rows)                 # shape (241,4)

def array_to_block(arr, template_block):
    """
    arr: ndarray (241,4)  hr lat lon prs
    template_block: 原始 block，用其前两行确定格式
    返回平均 PRESSURE block 列表
    """
    out = []
    out.append(template_block[0])         # '1 PRESSURE' 行

    # 用原轨迹首行当格式模板
    fmt_src = template_block[1].rstrip('\n').split()
    for i, (hr, lat, lon, prs) in enumerate(arr, 1):
        parts = fmt_src.copy()
        parts[0]  = f"{i:5d}"             # 重新编号
        parts[8]  = f"{hr:6.1f}"          # 小时列宽按原样
        parts[-5] = f"{lat:8.3f}"
        parts[-4] = f"{lon:9.3f}"
        parts[-3] = f"{prs:8.1f}"
        out.append(" ".join(parts) + '\n')
    return out

def process_one_file(fpath: pathlib.Path):
    header, blocks = split_blocks(fpath.read_text(encoding='utf-8', errors='ignore').splitlines(keepends=True))

    arrays = []
    for b in blocks:
        arr = track_to_array(b)
        if arr is not None and arr.shape[0] >= 240:
            arrays.append(arr[:,1:])   # 取 lat lon press
    if not arrays:
        print(f"[WARN] {fpath.name} 没有有效轨迹，已跳过")
        return

    if len(arrays) == 1:
        mean_xyz = arrays[0]
    else:
        mean_xyz = np.stack(arrays, axis=0).mean(axis=0)   # (240,3)

    hrs = np.arange(-1, -241, -1)
    mean_block = array_to_block(np.column_stack((hrs, mean_xyz)), blocks[0])

    out_path = fpath.with_name(fpath.stem.replace('_M_mean', '_META_mean') + '.tdump')
    with out_path.open('w', encoding='utf-8') as fo:
        fo.writelines(header)
        fo.writelines(mean_block)
    print(f"→ {out_path.name}  已生成 (平均 {len(arrays)} 条轨迹)")

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
