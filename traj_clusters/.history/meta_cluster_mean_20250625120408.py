#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
meta_cluster_mean.py  ·  重新对一个 META 目录里的 C?_M_mean 做均值
---------------------------------------------------------------------
输出 C?_META_mean.tdump（单条平均轨迹，格式与 HYSPLIT 原生相同）

用法:
    python meta_cluster_mean.py <META_DIR>
"""

import sys, pathlib, re, numpy as np

# ---------- 正则 ----------
RE_BACK   = re.compile(r'^\s*\d+\s+BACKWARD', re.I)   # '3 BACKWARD …'
RE_PRESS  = re.compile(r'^\s*1\s+PRESSURE',  re.I)    # '1 PRESSURE'
RE_TRAJ   = re.compile(r'^\s*\d+')                   # 轨迹行

# ---------- 拆 header / blocks ----------
def split_blocks(lines):
    header, blocks, cur = [], [], None
    for l in lines:
        if RE_PRESS.match(l):                # 新 block 起点
            if cur is not None:
                blocks.append(cur)
            cur = []                         # 不含 PRESSURE 行自身
        elif cur is None:
            header.append(l)
        else:
            cur.append(l)
    if cur:
        blocks.append(cur)
    return header, blocks

# ---------- block → dict{hr:[lat,lon,prs]} ----------
def block_to_dict(block):
    d = {}
    for line in block:
        if not RE_TRAJ.match(line):
            continue
        t = line.split()
        if len(t) < 12:
            continue                         # 列数不足
        hr  = int(float(t[8]))               # 0, -1…
        lat = float(t[-5])
        lon = float(t[-4])
        prs = float(t[-3])
        d.setdefault(hr, []).append([lat, lon, prs])
    return d if len(d) >= 100 else None      # 行太少视为异常

# ---------- 多条轨迹求平均，返回 header+PRESSURE ----------
def build_mean_tdump(dicts, header, template_row):
    # 1) 聚合 & 求均值
    hrs = sorted(set().union(*dicts))        # 0, -1, -2…
    rows = []
    for hr in hrs:
        vals = [np.mean(d[hr], axis=0) for d in dicts if hr in d]
        lat, lon, prs = np.mean(vals, axis=0)
        rows.append([hr, lat, lon, prs])
    rows.sort(key=lambda r: r[0])            # 升序 (0 → -n)

    # 2) 更新 header 坐标行为 hr = 0 的均值坐标
    hdr = header.copy()
    for i, l in enumerate(hdr):
        if RE_BACK.search(l):
            coord_idx = i + 1                # BACKWARD 下一行
            parts = hdr[coord_idx].rstrip('\n').split()
            # header 坐标行长度≥7，最后 3 个即 lat lon prs
            parts[-3] = f"{rows[-1][1]:8.3f}"  # hr=0 是列表最后一个
            parts[-2] = f"{rows[-1][2]:9.3f}"
            parts[-1] = f"{rows[-1][3]:8.1f}"
            hdr[coord_idx] = " ".join(parts) + '\n'
            break

    # 3) PRESSURE 段
    press = [" 1 PRESSURE\n"]
    tok_template = template_row.split()
    for idx, (hr, lat, lon, prs) in enumerate(rows, 1):
        toks = tok_template.copy()
        toks[0]  = f"{idx:5d}"               # 行号
        toks[8]  = f"{hr:6.1f}"              # 小时
        toks[-5] = f"{lat:8.3f}"
        toks[-4] = f"{lon:9.3f}"
        toks[-3] = f"{prs:8.1f}"
        press.append(" ".join(toks) + '\n')

    return hdr + press

# ---------- 处理单个文件 ----------
def process_file(fp: pathlib.Path):
    text  = fp.read_text(encoding='utf-8', errors='ignore')
    lines = text.splitlines(keepends=True)
    header, blocks = split_blocks(lines)

    dicts = [d for b in blocks if (d := block_to_dict(b))]
    if not dicts:
        print(f"[WARN] {fp.name} 无有效轨迹，跳过")
        return

    # 取第一条轨迹首行作模板
    first_block   = next(b for b in blocks if block_to_dict(b))
    template_row  = next(l for l in first_block if RE_TRAJ.match(l)).rstrip('\n')

    tdump = build_mean_tdump(dicts, header, template_row)
    out   = fp.with_name(fp.stem.replace('_M_mean', '_META_mean') + '.tdump')
    out.write_text("".join(tdump), encoding='utf-8')
    print(f"→ {out.name} 生成；平均 {len(dicts)} 条轨迹，{len(tdump)} 行")

# ---------- 主入口 ----------
def main(meta_dir):
    meta = pathlib.Path(meta_dir)
    if not meta.is_dir():
        sys.exit(f"❌ 目录不存在: {meta}")
    files = sorted(meta.glob('C*_M_mean'))
    if not files:
        sys.exit("❌ 未找到 C*_M_mean 文件")

    for fp in files:
        process_file(fp)
    print("✅ 全部完成。")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit("用法: python meta_cluster_mean.py <META_DIR>")
    main(sys.argv[1])
