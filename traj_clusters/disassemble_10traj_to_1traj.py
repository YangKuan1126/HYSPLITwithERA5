#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_traj_10.py  (年份区间过滤 + 简洁进度输出)
==============================================

- 通过 -r/--range 可指定 1951-2020 的年份区间
- 文件名中两位年份 YY → 51-99 映射 1951-1999；00-20 映射 2000-2020
- PowerShell 终端只显示 “正在处理年份 YYYY”，不再逐文件刷屏
"""
from pathlib import Path
import re
import argparse
from typing import List, Optional, Tuple


# ---------- 行号空格对齐 ---------- #
def _format_id_line(raw: str, new_id: int) -> str:
    m = re.match(r"^(\s*)(\d+)(\s+.*)$", raw)
    if not m:
        return raw
    lead, old_id, tail = m.groups()
    return f"{lead}{str(new_id).rjust(len(old_id))}{tail}"


# ---------- 年份解析 ---------- #
def _two_digit_to_four(yy: int) -> Optional[int]:
    if 51 <= yy <= 99:
        return 1900 + yy
    elif 0 <= yy <= 20:
        return 2000 + yy
    return None


def _year_in_name(name: str) -> Optional[int]:
    if m4 := re.search(r"(19|20)\d{2}", name):
        return int(m4.group(0))
    if m2 := re.search(r"\D(\d{2})\D", f"_{name}_"):
        return _two_digit_to_four(int(m2.group(1)))
    return None


# ---------- 拆分逻辑 ---------- #
def split_trajectories(input_path: Path, output_root: Path):
    lines: List[str] = input_path.read_text().splitlines()

    idx_back = next(i for i, ln in enumerate(lines)
                    if re.match(r"^\s*\d+\s+BACKWARD", ln))
    total = int(lines[idx_back].split()[0])

    init_start = idx_back + 1
    init_end   = init_start + total
    idx_cols   = next(i for i, ln in enumerate(lines)
                      if re.match(r"^\s*\d+\s+PRESSURE", ln))

    header        = lines[:idx_back]
    backward_line = lines[idx_back]
    init_lines    = lines[init_start:init_end]
    col_line      = lines[idx_cols]
    data_lines    = lines[idx_cols + 1:]

    for traj_id in range(1, total + 1):
        out_dir = output_root / f"P{traj_id}"
        out_dir.mkdir(parents=True, exist_ok=True)
        outfile = out_dir / input_path.name

        back_new = _format_id_line(backward_line, 1)
        init_new = _format_id_line(init_lines[traj_id - 1], 1)
        data_new = [
            _format_id_line(ln, 1)
            for ln in data_lines
            if re.match(rf"^\s*{traj_id}\s+", ln)
        ]

        with outfile.open("w", encoding="utf-8") as fw:
            fw.write("\n".join(header) + "\n")
            fw.write(back_new + "\n")
            fw.write(init_new + "\n")
            fw.write(col_line + "\n")
            fw.write("\n".join(data_new) + "\n")


# ---------- CLI ---------- #
def _parse_range(r: str) -> Tuple[int, int]:
    m = re.match(r"^\s*(\d{4})\s*-\s*(\d{4})\s*$", r)
    if not m:
        raise argparse.ArgumentTypeError("年份区间格式应为 1951-1970")
    a, b = map(int, m.groups())
    return (a, b) if a <= b else (b, a)


def main():
    ap = argparse.ArgumentParser(
        description="拆分 10 轨迹 tdump，并按年份区间过滤（简洁进度输出）")
    ap.add_argument("input",  help="tdump 文件或目录")
    ap.add_argument("output", help="输出顶层目录")
    ap.add_argument("-r", "--range", type=_parse_range,
                    help="年份区间 例: 1951-1970", default=None)
    args = ap.parse_args()

    inp = Path(args.input).expanduser().resolve()
    out = Path(args.output).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    # 收集文件
    targets = [inp] if inp.is_file() else sorted(
        p for p in inp.iterdir() if p.is_file())

    # 过滤年份
    if args.range:
        s, e = args.range
        targets = [f for f in targets
                   if (y := _year_in_name(f.name)) and s <= y <= e]

    if not targets:
        print("[!] 未找到符合条件的文件。")
        return

    ### CHANGED ###  —— 只按年份输出一次进度
    printed_years = set()

    for f in targets:
        year = _year_in_name(f.name)
        if year not in printed_years:
            print(f"正在处理年份 {year} ...")
            printed_years.add(year)
        try:
            split_trajectories(f, out)
        except Exception as e:
            print(f"[!] 处理 {f} 时出错: {e}")

    print("全部指定年份处理完成。")


if __name__ == "__main__":
    main()
