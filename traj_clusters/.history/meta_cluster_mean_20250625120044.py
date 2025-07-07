#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
meta_cluster_mean.py
--------------------
把 <…_META> 目录里的 C?_M_mean 文件再做一次聚合平均：
    • 每个文件往往包含同一 meta-cluster 的多条后向轨迹
    • 轨迹行以 “1 PRESSURE” 开头，后跟 0,-1,-2 … -n 小时；长度不限
    • 本脚本按 ‘回溯小时’ 对齐求平均 → 只写出 1 条平均轨迹
      (header 中坐标行也同步成均值的 hr = 0 坐标)

用法
    python meta_cluster_mean.py <meta_dir>
示例
    python meta_cluster_mean.py F:\ERA5_pressure_level\traj_clusters\1979_2020_01_META
"""

import sys, pathlib, re, numpy as np

# ---------- 正则 ----------
RE_BACK  = re.compile(r'^\s*\d+\s+BACKWARD', re.I)
RE_PRESS = re.compile(r'^\s*1\s+PRESSURE',  re.I)
RE_TRAJ  = re.compile(r'^\s*\d+')               # 轨迹行以数字起头

# ---------- 拆 header / blocks ----------
def split_blocks(lines):
    """
    header : “3 BACKWARD …” 到第一个 PRESSURE 之前
    blocks : 每个 PRESSURE 段后的完整轨迹 list[str]
    """
    header, blocks, cur = [], [], None
    for l in lines:
        if RE_PRESS.match(l):                  # 新轨迹开始
            if cur is not None:
                blocks.append(cur)
            cur = []                           # 不含‘1 PRESSURE’行本身
        elif cur is None:
            header.append(l)
        else:
            cur.append(l)
    if cur:
        blocks.append(cur)
    return header, blocks

# ---------- block 转为 {hr: [[lat,lon,prs]...]} ----------
def block_to_dict(block):
    d = {}
    for line in block:
        if not RE_TRAJ.match(line):
            continue
        t = line.split()
        if len(t) < 12:
            continue
        hr  = int(float(t[8]))     # 回溯小时 (0, -1, …)
        lat = float(t[-5])
        lon = float(t[-4])
        prs = float(t[-3])
        d.setdefault(hr, []).append([lat, lon, prs])
    return d if len(d) >= 100 else None   # <100 行认为异常

# ---------- 把若干轨迹平均并生成新 tdump -------------
def build_mean_tdump(dicts, header_lines):
    hrs  = sorted(set().union(*dicts))         # 0, -1, …
    rows = []
    for hr in hrs:
        lats = lons = prs = []
        for d in dicts:
            if hr in d:
                lat, lon, pr = np.mean(d[hr], axis=0)
                lats.append(lat); lons.append(lon); prs.append(pr)
        rows.append([hr,
                     float(np.mean(lats)),
                     float(np.mean(lons)),
                     float(np.mean(prs))])
    rows.sort(key=lambda r: r[0])              # 升序 (0 → -n)

    # ---- 更新 header 中坐标行为平均 hr=0 坐标 ----
    hdr = header_lines.copy()
    for i, l in enumerate(hdr):
        if RE_BACK.search(l):
            coord_idx = i + 1                  # 下一行
            parts = hdr[coord_idx].rstrip('\n').split()
            parts[-5] = f"{rows[0][1]:8.3f}"   # lat
            parts[-4] = f"{rows[0][2]:9.3f}"   # lon
            parts[-3] = f"{rows[0][3]:8.1f}"   # prs
            hdr[coord_idx] = " ".join(parts) + '\n'
            break

    # ---- PRESSURE 段 ----
    press = [" 1 PRESSURE\n"]
    tmpl  = (" " + " ".join(["{:5d}"] + ["{:3d}"]*6 +
            ["{:6.1f}",
             "{:8.3f}", "{:9.3f}", "{:8.1f}", "{:8.1f}"]) + "\n")
    for i, (hr, lat, lon, prs) in enumerate(rows, 1):
        press.append(tmpl.format(i, 1,1,1,1,1,1, -88,
                                 hr, lat, lon, prs, 0.0))
    return hdr + press

# ---------- 处理单文件 ----------
def process_file(fp: pathlib.Path):
    lines = fp.read_text(encoding='utf-8', errors='ignore').splitlines(keepends=True)
    header, blocks = split_blocks(lines)

    dicts = [d for b in blocks if (d := block_to_dict(b))]
    if not dicts:
        print(f"[WARN] {fp.name} 无有效轨迹，跳过")
        return

    tdump = build_mean_tdump(dicts, header)

    out = fp.with_name(fp.stem.replace('_M_mean', '_META_mean') + '.tdump')
    out.write_text("".join(tdump), encoding='utf-8')
    print(f"→ {out.name}  生成；平均 {len(dicts)} 条轨迹, 总 {len(tdump)} 行")

# ---------- 主入口 ----------
def main(meta_dir):
    meta = pathlib.Path(meta_dir)
    if not meta.is_dir():
        sys.exit(f"❌ 目录不存在: {meta}")
    files = sorted(meta.glob('C*_M_mean'))
    if not files:
        sys.exit("❌ 未找到 C*_M_mean 文件")

    for f in files:
        process_file(f)
    print("✅ 全部完成。")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("用法: python meta_cluster_mean.py <meta_dir>")
    main(sys.argv[1])
