#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
create_INFILE.py – 每行一个文件（仅保留指定起报小时）
====================================================
生成 HYSPLIT `cluster.exe` 所需 INFILE，并可通过 --keep-hours
参数筛选文件名末尾 YYMMDDHH 的 “HH” 字段（默认 06 与 18）。

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
from collections import deque

DIGITS8_RE = re.compile(r"(\d{8})$")  # 匹配文件名结尾的 YYMMDDHH


def _extract_mm_hh(stem: str) -> tuple[int | None, str | None]:
    """从文件名 stem 提取月份和小时"""
    m = DIGITS8_RE.search(stem)
    if not m:
        return None, None
    s = m.group(1)
    return int(s[2:4]), s[6:8]


def _collect_traj_files(
    root: pathlib.Path, start: int, end: int,
    point: str, months: Set[int], hours: Set[str], pattern: str
) -> List[pathlib.Path]:
    files: List[pathlib.Path] = []
    for year in range(start, end + 1):
        d = root / str(year) / point
        if not d.exists():
            print(f"[WARN] 缺失目录: {d}", file=sys.stderr)
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
            files.append(f)
    return files


def get_first_last_q(path: pathlib.Path) -> tuple[float, float]:
    """
    跳过首部非数据行，从第一条有效数据行读取 q 值，
    并通过 deque 获取最后一条 q 值。
    """
    first_q = last_q = None
    with path.open('r', encoding='utf-8', errors='ignore') as f:
        # 首条有效数据
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 2 and parts[-1].replace('.', '', 1).isdigit():
                first_q = float(parts[-1])
                break
        if first_q is None:
            raise ValueError("未找到首条数据行 q 值")
        # 最后一条数据
        dq = deque(f, maxlen=1)
        if not dq:
            raise ValueError("未找到末条数据行")
        parts = dq[0].strip().split()
        if len(parts) < 2 or not parts[-1].replace('.', '', 1).isdigit():
            raise ValueError("末行 q 值不合法")
        last_q = float(parts[-1])
    return first_q, last_q


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(
        description="Create INFILE für HYSPLIT – only Δq > 0 trajectories"
    )
    ap.add_argument("--root",       required=True, help="轨迹根目录 root/year/point")
    ap.add_argument("--outfile",    required=True, help="输出 INFILE 文件路径")
    ap.add_argument("--years",      nargs=2, type=int, required=True, metavar=("START", "END"))
    ap.add_argument("--months",     nargs="*", type=int, default=[], help="目标月份 (1–12)，空表示全年")
    ap.add_argument("--ref-subdir", default="P1", help="点位子目录名，如 P1")
    ap.add_argument("--pattern",    default="*", help="轨迹文件通配符")
    ap.add_argument("--keep-hours", nargs="+", default=["06", "18"], help="保留的起报小时")
    args = ap.parse_args(argv)

    root = pathlib.Path(args.root)
    if not root.exists():
        sys.exit(f"❌ 根目录不存在: {root}")

    months = set(args.months)
    hours = {h.zfill(2) for h in args.keep_hours}

    files = _collect_traj_files(root, args.years[0], args.years[1],
                                args.ref_subdir, months, hours, args.pattern)
    if not files:
        sys.exit("❌ 未找到带条件轨迹文件，退出")

    good: List[pathlib.Path] = []
    for f in files:
        try:
            q0, qN = get_first_last_q(f)
            dq = q0 - qN
            if dq > 0:
                good.append(f)
            else:
                print(f"[剔除] {f.name} Δq={dq:.3f} ≤ 0")
        except Exception as e:
            print(f"[错误] {f.name}: {e}", file=sys.stderr)

    if not good:
        sys.exit("❌ 没有满足 Δq > 0 的轨迹，INFILE 未生成")

    out_path = pathlib.Path(args.outfile)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="ascii") as fo:
        for p in good:
            fo.write(f"{p}\n")

    print(f"✅ INFILE 写入 {out_path} (共保留 {len(good)}/{len(files)} 条轨迹)")


if __name__ == "__main__":
    main()