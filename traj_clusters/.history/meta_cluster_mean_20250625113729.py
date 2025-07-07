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
    rows = []
    for l in block:
        if not l.strip():
            continue
        toks = l.split()
        if len(toks) < 12:
            continue
        hr   = int(float(toks[8]))        # 0, -1, … -240
        lat  = float(toks[-5])
        lon  = float(toks[-4])
        prs  = float(toks[-3])
        rows.append((hr, lat, lon, prs))
    if len(rows) < 200:                  # 行数不足视为无效
        return None
    rows.sort(key=lambda r: r[0])
    return np.array(rows)                # (241,4)


def array_to_block(arr, header_lines):
    """
    arr (241,4): hr lat lon prs
    header_lines: 原 header (含 3 BACKWARD 行 + 旧坐标行)
    返回新的 header + PRESSURE block
    """
    # ------------- 更新 header 中的坐标行 -------------
    hdr = header_lines.copy()
    # 假设 header 倒数第二行就是旧“质心坐标行”
    coord_idx = -1
    for i, l in enumerate(hdr[::-1], 1):
        if RE_HEAD.search(l):
            coord_idx = len(hdr) - i + 1   # 紧跟 BACKWARD 行的下一行
            break
    # 若找到就替换
    if coord_idx > 0:
        parts = hdr[coord_idx].rstrip('\n').split()
        parts[-3] = f"{arr[0,1]:8.3f}"     # lat
        parts[-2] = f"{arr[0,2]:9.3f}"     # lon
        parts[-1] = f"{arr[0,3]:8.1f}"     # press
        hdr[coord_idx] = " ".join(parts) + '\n'

    # ------------- 生成 PRESSURE 段 -------------------
    press_block = [" 1 PRESSURE\n"]
    fmt_src = (" " + " ".join(["{:5d}"] + ["{:3d}"]*6 + ["{:6.1f}"] + ["{:8.3f}","{:9.3f}","{:8.1f}","{:8.1f}"]) + "\n")
    for i, (hr, lat, lon, prs) in enumerate(arr, 1):
        press_block.append(fmt_src.format(
            i, 1, 1, 1, 1, 1, 1, -88, hr, lat, lon, prs, 0.0))

    return hdr + press_block


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
    mean_block = array_to_block(np.column_stack((np.arange(0, -241, -1), mean_xyz)), header)

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
