#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
meta_cluster_mean.py
====================
读取一个 “_META” 目录中各个 C?_M_mean 文件，
把同一 meta-cluster 内的所有后向轨迹按 ‘回溯小时’ 对齐后求平均，
并写出仅含“一条平均轨迹”的 C?_META_mean.tdump。

用法
----
    python meta_cluster_mean.py <meta_dir>

示例
----
    python meta_cluster_mean.py F:\ERA5_pressure_level\traj_clusters\1979_2020_01_META
"""

import sys, pathlib, re, numpy as np

# ---------- 正则 ----------
RE_HEAD  = re.compile(r'^\s*\d+\s+BACKWARD', re.I)
RE_PRESS = re.compile(r'^\s*1\s+PRESSURE',  re.I)

# ---------- 解析一个文件拆块 ----------
def split_blocks(lines):
    """返回 header(list[str]), blocks(list[list[str]])"""
    head_i  = next(i for i,l in enumerate(lines) if RE_HEAD.search(l))
    press_i = next(i for i,l in enumerate(lines[head_i+1:], head_i+1) if RE_PRESS.search(l))
    header  = lines[:press_i]          # 含 “3 BACKWARD …” 与旧坐标行
    blocks  = []
    cur = []
    for l in lines[press_i:]:
        if RE_PRESS.match(l):          # 遇到下一个文件意外拼接时的 PRESSURE
            continue
        # 新轨迹编号一般以空格+数字开头：利用空行分隔判断
        if l.strip() and l.lstrip()[0].isdigit() and cur:
            blocks.append(cur); cur=[l]
        else:
            cur.append(l)
    if cur:
        blocks.append(cur)
    return header, blocks

# ---------- 把 block（一条轨迹）转成 hr→[lat,lon,prs] 字典 ----------
def track_to_dict(block):
    d = {}
    for l in block:
        if not l.strip():
            continue
        t = l.split()
        if len(t) < 12:
            continue
        hr   = int(float(t[8]))        # 回溯小时
        lat  = float(t[-5])
        lon  = float(t[-4])
        prs  = float(t[-3])
        d.setdefault(hr, []).append([lat, lon, prs])
    return d if len(d) >= 100 else None   # 少于 100 h 视为异常

# ---------- 由若干轨迹字典求平均并生成新 tdump 内容 ----------
def build_mean_tdump(dicts, header_lines):
    # 1) 汇总所有小时
    hrs = sorted(set().union(*dicts), reverse=False)   # 0, -1, …
    rows = []
    for hr in hrs:
        triples = [np.mean(d[hr],axis=0) for d in dicts if hr in d]
        rows.append([hr, *np.mean(triples, axis=0)])
    rows.sort(key=lambda r: r[0])        # 升序

    # 2) 更新 header 中旧坐标行为平均 hr=0 坐标
    hdr = header_lines.copy()
    for i,l in enumerate(hdr):
        if RE_HEAD.search(l):
            coord_idx = i+1              # 下一行
            break
    parts = hdr[coord_idx].rstrip('\n').split()
    parts[-5] = f"{rows[0][1]:8.3f}"
    parts[-4] = f"{rows[0][2]:9.3f}"
    parts[-3] = f"{rows[0][3]:8.1f}"
    hdr[coord_idx] = " ".join(parts)+'\n'

    # 3) PRESSURE 段
    press = [" 1 PRESSURE\n"]
    tmpl  = (" " + " ".join(["{:5d}"] + ["{:3d}"]*6 +
            ["{:6.1f}","{:8.3f}","{:9.3f}","{:8.1f}","{:8.1f}"]) + "\n")
    for i,(hr,lat,lon,prs) in enumerate(rows,1):
        press.append(tmpl.format(i,1,1,1,1,1,1,-88,hr,lat,lon,prs,0.0))
    return hdr + press

# ---------- 处理单个 C?_M_mean ----------
def process_one_file(fpath: pathlib.Path):
    lines  = fpath.read_text(encoding='utf-8',errors='ignore').splitlines(keepends=True)
    header, blocks = split_blocks(lines)
    dicts = [d for b in blocks if (d:=track_to_dict(b))]
    if not dicts:
        print(f"[WARN] {fpath.name} 无有效轨迹，跳过")
        return
    tdump = build_mean_tdump(dicts, header)
    out_path = fpath.with_name(fpath.stem.replace('_M_mean','_META_mean')+'.tdump')
    out_path.write_text("".join(tdump), encoding='utf-8')
    print(f"→ {out_path.name}  生成，平均 {len(dicts)} 条轨迹，{len(tdump)} 行")

# ---------- 主程序 ----------
def main(meta_dir):
    meta_dir = pathlib.Path(meta_dir)
    if not meta_dir.is_dir():
        sys.exit(f"❌ 目录不存在: {meta_dir}")
    files = sorted(meta_dir.glob('C*_M_mean'))
    if not files:
        sys.exit("❌ 未找到 C*_M_mean 文件")
    for fp in files:
        process_one_file(fp)
    print("✅ 全部完成。")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit("用法: python meta_cluster_mean.py <meta_dir>")
    main(sys.argv[1])
