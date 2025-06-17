#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
create_INFILE.py – 每行一个文件（适配 YYMMDDHH 文件名）
===========================================================
生成 HYSPLIT `cluster.exe` 所需 **INFILE**：**每个轨迹文件一行**，无文件总数。 

* 月份解析仍按 YYMMDDHH → MM。
* 兼容 Python 3.7–3.9（无联合类型语法）。
* 可通过 `--pattern` 过滤文件名。
使用范例：
py -3.9 create_INFILE.py --root F:\ERA5_pressure_level\traj_points --outfile C:\hysplit\cluster\working\INFILE --years 2019 2020 --months 1 2 3 --ref-subdir P1
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys
from typing import List, Optional

DIGITS8_RE = re.compile(r"(\d{8})$")  # 匹配结尾 8 位数字 (YYMMDDHH)

# ----------------- 工具函数 -----------------

def _extract_month(stem: str) -> Optional[int]:
    m = DIGITS8_RE.search(stem)
    if not m:
        return None
    return int(m.group(1)[2:4])  # YY **MM** DDHH


def _collect_traj_files(
    base_dir: pathlib.Path,
    start_year: int,
    end_year: int,
    point: str,
    months: set[int],
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
            if months:
                mm = _extract_month(f.stem)
                if mm is None or mm not in months:
                    continue
            out.append(f.resolve())
    return out

# ----------------- 主入口 -----------------

def main(argv: Optional[List[str]] = None) -> None:
    ap = argparse.ArgumentParser(
        description="Create INFILE (one trajectory path per line) for HYSPLIT cluster",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("--root", required=True, help="轨迹根目录 root/year/point/")
    ap.add_argument("--outfile", required=True, help="输出 INFILE 路径")
    ap.add_argument("--years", nargs=2, type=int, metavar=("START", "END"), required=True)
    ap.add_argument("--months", nargs="*", type=int, default=[], help="目标月份 (1–12)")
    ap.add_argument("--ref-subdir", default="P1", help="点位子目录")
    ap.add_argument("--pattern", default="*", help="文件通配符 (默认 '*')")
    args = ap.parse_args(argv)

    root = pathlib.Path(args.root)
    if not root.exists():
        sys.exit(f"❌ 根目录不存在: {root}")

    files = _collect_traj_files(
        base_dir=root,
        start_year=args.years[0],
        end_year=args.years[1],
        point=args.ref_subdir,
        months=set(map(int, args.months)),
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