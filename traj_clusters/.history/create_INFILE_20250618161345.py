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
from typing import List, Optional, Set

DIGITS8_RE = re.compile(r"(\d{8})$")  # 结尾 YYMMDDHH


def _extract_mm_hh(stem: str) -> tuple[Optional[int], Optional[str]]:
    m = DIGITS8_RE.search(stem)
    if not m:
        return None, None
    s = m.group(1)
    return int(s[2:4]), s[6:8]  # (MM, HH)


def _collect_traj_files(
    base_dir: pathlib.Path,
    start_year: int,
    end_year: int,
    point: str,
    months: Set[int],
    keep_hours: Set[str],
    pattern: str,
) -> List[pathlib.Path]:
    out: List[pathlib.Path] = []
    for yr in range(start_year, end_year + 1):
        d = base_dir / str(yr) / point
        if not d.is_dir():
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
            if hh not in keep_hours:
                continue
            out.append(f.resolve())
    return out


def main(argv: Optional[List[str]] = None) -> None:
    ap = argparse.ArgumentParser(
        description="Create INFILE (one trajectory path per line) for HYSPLIT cluster",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("--root", required=True, help="轨迹根目录 root/year/point/")
    ap.add_argument("--outfile", required=True, help="输出 INFILE 路径")
    ap.add_argument("--years", nargs=2, type=int, metavar=("START", "END"), required=True)
    ap.add_argument(
        "--months", nargs="*", type=int, default=[], help="目标月份 (1–12); 为空=全年"
    )
    ap.add_argument("--ref-subdir", default="P1", help="点位子目录，如 P1")
    ap.add_argument("--pattern", default="*", help="文件通配符 (默认 '*')")
    ap.add_argument(
        "--keep-hours",
        nargs="+",
        default=["06", "18"],
        metavar="HH",
        help="保留的起报小时 (两位)，默认 06 18",
    )
    args = ap.parse_args(argv)

    keep_hours = {h.zfill(2) for h in args.keep_hours}

    root = pathlib.Path(args.root)
    if not root.exists():
        sys.exit(f"❌ 根目录不存在: {root}")

    files = _collect_traj_files(
        base_dir=root,
        start_year=args.years[0],
        end_year=args.years[1],
        point=args.ref_subdir,
        months=set(map(int, args.months)),
        keep_hours=keep_hours,
        pattern=args.pattern,
    )
    if not files:
        sys.exit("❌ 未找到符合条件的轨迹文件，INFILE 未生成。")

    out_path = pathlib.Path(args.outfile)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="ascii") as fo:
        for p in files:
            fo.write(f"{p}\n")

    print(f"✅ INFILE 已写入 → {out_path}  (共 {len(files)} 条)")


if __name__ == "__main__":
    main()
