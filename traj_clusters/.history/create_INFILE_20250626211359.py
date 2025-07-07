#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
create_INFILE.py – 每行一个文件（仅保留指定起报小时）
====================================================
生成 HYSPLIT `cluster.exe` 所需 INFILE，并可通过 --keep-hours
参数筛选文件名末尾 YYMMDDHH 的 “HH” 字段（默认 06 与 18）。

根据轨迹文件首条有效数据行和末行的 q 值判断 Δq 是否 > 0。

用法示例：
py -3.9 create_INFILE.py ^
    --root F:\ERA5_pressure_level\traj_points ^
    --outfile C:\hysplit\cluster\working\INFILE ^
    --years 1951 2020 ^
    --months 1 ^
    --ref-subdir P1 ^
    --keep-hours 06 18
"""

from __future__ import annotations
import argparse
import pathlib
import re
import sys
from typing import List, Set


DIGITS8_RE = re.compile(r"(\d{8})$")  # 匹配文件名结尾 YYMMDDHH


def _extract_mm_hh(stem: str) -> tuple[int | None, str | None]:
    m = DIGITS8_RE.search(stem)
    if not m:
        return None, None
    s = m.group(1)
    return int(s[2:4]), s[6:8]


def _collect_traj_files(root: pathlib.Path, start: int, end: int,
                        point: str, months: Set[int], hours: Set[str], pattern: str) -> List[pathlib.Path]:
    trajs = []
    for yr in range(start, end + 1):
        d = root / str(yr) / point
        if not d.is_dir():
            print(f"[WARN] 路径不存在: {d}", file=sys.stderr)
            continue
        for f in sorted(d.glob(pattern)):
            if not f.is_file():
                continue
            mm, hh = _extract_mm_hh(f.stem)
            if mm is None or hh is None:
                continue
            if months and mm not in months:
                continue
            if hh not in hours:
                continue
            trajs.append(f)
    return trajs


def get_first241_q(path: pathlib.Path) -> tuple[float, float]:
    """
    跳过表头行，获取表头之后第1行和第241行的最后一列 q 值
    """
    first_q = last_q = None
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    # 找到表头索引
    header_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith("2 PRESSURE SPCHUMID"):
            header_idx = i
            break
    if header_idx is None:
        raise ValueError("未找到表头行")

    # 计算目标行索引
    idx1 = header_idx + 1
    idx241 = header_idx + 241
    if idx1 >= len(lines) or idx241 >= len(lines):
        raise ValueError(f"文件行数不够，缺少第 {'1' if idx241 < idx1 else '241'} 行")

    # 提取 q 值
    def extract_q(line: str) -> float:
        parts = line.strip().split()
        return float(parts[-1])

    first_q = extract_q(lines[idx1])
    last_q = extract_q(lines[idx241])

    return first_q, last_q


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(
        description="仅保留第1和第241行 Δq > 0 的轨迹文件"
    )
    ap.add_argument("--root",       required=True, help="轨迹根目录, 结构 root/year/point")
    ap.add_argument("--outfile",    required=True, help="输出的 INFILE 文件路径")
    ap.add_argument("--years",      nargs=2, type=int, required=True, metavar=("START", "END"))
    ap.add_argument("--months",     nargs="*", type=int, default=[], help="要保留的月份列表，空=全部")
    ap.add_argument("--ref-subdir", default="P1", help="点位目录名，如 P1")
    ap.add_argument("--pattern",    default="*", help="轨迹文件通配符")
    ap.add_argument("--keep-hours", nargs="+", default=["06", "18"], help="保留的起报小时")
    args = ap.parse_args(argv)

    root = pathlib.Path(args.root)
    if not root.exists():
        sys.exit(f"❌ 根目录不存在：{root}")

    months = set(args.months)
    hours = {h.zfill(2) for h in args.keep_hours}

    trajs = _collect_traj_files(root, args.years[0], args.years[1],
                                args.ref_subdir, months, hours, args.pattern)
    if not trajs:
        sys.exit("❌ 没有找到符合条件的轨迹文件")

    kept: List[pathlib.Path] = []
    for f in trajs:
        try:
            q1, q241 = get_first241_q(f)
            dq = q1 - q241
            if dq > 0:
                kept.append(f)
            else:
                print(f"[剔除] {f.name} Δq={dq:.3f} ≤ 0")
        except Exception as e:
            print(f"[错误] {f.name}: {e}", file=sys.stderr)

    if not kept:
        sys.exit("❌ 没有轨迹满足 Δq > 0 条件")

    out_file = pathlib.Path(args.outfile)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with out_file.open("w", encoding="ascii") as fo:
        for p in kept:
            fo.write(f"{p}\n")

    print(f"✅ INFILE 已生成：{out_file} （保留 {len(kept)}/{len(trajs)} 条轨迹）")


if __name__ == "__main__":
    main()