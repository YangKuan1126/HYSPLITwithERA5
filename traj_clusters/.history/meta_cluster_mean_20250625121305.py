#!/usr/bin/env python3
# meta_cluster_mean.py
"""
将同一 meta-cluster 内所有轨迹( lat, lon, pressure ) 逐时取平均，
生成 1 条 “平均轨迹” (*.tdump)。  
• 自动跳过残缺/异常行（如 “BACKWARD OMEGA …”）  
• 平均时同时包含气压  
• 输出顺序：0 h 在最上；-240 h 在最下  
"""

from __future__ import annotations
import sys, pathlib, re, warnings
import numpy as np

TDUMP_GLOB = r"C[0-9]_?_?_M_mean"  # 适配 C1_7_M_mean 这类文件

# ---------- 解析单条轨迹 -------------------------------------------------
_DATA_RE = re.compile(r"\s-?\d+\.\d+")  # 行里至少含 1 个浮点数即视作数据

def track_to_array(block: list[str]) -> np.ndarray | None:
    """
    block = 241 行文本（含 header）。返回 shape (241,3): lat,lon,press
    若长度不足 241 或无法解析，返回 None
    """
    rows: list[list[float]] = []
    for ln in block:
        if not _DATA_RE.search(ln):          # 跳过 “BACKWARD …” 等非数据行
            continue
        parts = ln.split()
        if len(parts) < 4:                    # 保险：字段太少
            continue
        try:
            lat  = float(parts[-4])           # 倒数第4=纬度
            lon  = float(parts[-3])           # 倒数第3=经度
            pres = float(parts[-2])           # 倒数第2=气压
        except ValueError:
            continue                          # 含非数字，跳过
        rows.append([lat, lon, pres])

    if len(rows) != 241:
        return None
    # 翻转，使 0h→-240h
    return np.asarray(rows[::-1])             # shape (241,3)

# ---------- 写平均轨迹 ----------------------------------------------------
def array_to_block(arr: np.ndarray, header: str) -> list[str]:
    """
    arr: (241,3) lat,lon,press
    返回 241+2 行：头 + PRESSURE + 数据行
    """
    out   = []
    out.append(header.rstrip() + "\n")                      # e.g. '1 BACKWARD OMEGA    MEANTRAJ'
    out.append("     1 PRESSURE\n")
    for hh, (lat, lon, pres) in enumerate(arr):
        line = (f"     1     1     1     1     1     1     0   -88"
                f"{hh:7.1f}{lat:10.3f}{lon:10.3f}{pres:9.1f}      0.0\n")
        out.append(line)
    return out

# ---------- 主流程 --------------------------------------------------------
def process_one_file(fpath: pathlib.Path) -> None:
    txt = fpath.read_text().splitlines()
    # 拆分为若干 block（以 'PRESSURE' 开头）
    blocks, buf = [], []
    for ln in txt:
        if ln.lstrip().startswith("1 PRESSURE") and buf:
            blocks.append(buf)
            buf = [ln]
        else:
            buf.append(ln)
    if buf:
        blocks.append(buf)

    # 取 header 供复写
    header_line = next((ln for ln in txt if "BACKWARD" in ln), "     1 BACKWARD OMEGA    MEANTRAJ")

    arrs = []
    for b in blocks:
        a = track_to_array(b)
        if a is None:
            warnings.warn("遇到残缺轨迹块，已忽略")
            continue
        arrs.append(a)

    if not arrs:
        warnings.warn(f"{fpath.name} 无有效轨迹，跳过")
        return

    mean_xyz = np.mean(arrs, axis=0)                     # (241,3)
    block    = array_to_block(mean_xyz, header_line)

    out_path = fpath.with_name(fpath.stem + "_avg.tdump")
    out_path.write_text("".join(block), encoding="ascii")
    print(f"✅ {fpath.name} → {out_path.name}")

def main(meta_dir: str) -> None:
    root = pathlib.Path(meta_dir)
    for fp in root.glob(TDUMP_GLOB):
        process_one_file(fp)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("用法:  py meta_cluster_mean.py  <META目录>")
    main(sys.argv[1])
