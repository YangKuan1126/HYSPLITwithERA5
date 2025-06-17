#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
disassemble_10traj_to_1traj.py   – 2025-06-21 directory-first 版
---------------------------------------------------------------
功能概要
• 递归遍历 <input> 目录，将 HYSPLIT 轨迹文件（1 起点或 10 起点，BACKWARD / FORWARD）
  拆分为单轨迹文件，按 <output>/<year>/P{1-10}/ 保存。
• 年份优先取最外层纯数字四位目录；若目录无年份则解析文件名。
• 兼容文件名中的 10 位 YYYYMMDDHH、8 位 YYYYMMDD / YYMMDDHH、6-7 位 YYMMDD 等。
• -r/--range 可过滤年份，如 -r 2019-2020。
"""

from pathlib import Path
import re
import argparse
from typing import Optional, Tuple

# ────────── 年份解析 ──────────────────────────────────────────────
def _yy_to_yyyy(yy: int) -> Optional[int]:
    if 50 <= yy <= 99:
        return 1900 + yy
    if 0 <= yy <= 20:
        return 2000 + yy
    return None

def _year_in_string(s: str) -> Optional[int]:
    if m := re.search(r"(19|20)\d{2}", s):
        return int(m.group(0))
    if m := re.search(r"\D(\d{2})\D", f"_{s}_"):
        return _yy_to_yyyy(int(m.group(1)))
    return None

def _year_from_filename(name: str) -> Optional[int]:
    """解析文件名里的时间戳"""
    if m := re.search(r"(\d{10}|\d{8}|\d{6,7})", name):
        d = m.group(1)
        # 10 位 YYYYMMDDHH
        if len(d) == 10 and d.startswith(("19", "20")):
            return int(d[:4])
        # 8 位 YYYYMMDD
        if len(d) == 8 and d.startswith(("19", "20")):
            mm, dd = int(d[4:6]), int(d[6:8])
            if 1 <= mm <= 12 and 1 <= dd <= 31:
                return int(d[:4])
        # 其余按两位年份映射
        if y := _yy_to_yyyy(int(d[:2])):
            return y
    return _year_in_string(name)

# ────────── 行首编号重写 ──────────────────────────────────────────
def _renumber(line: str, new_id: int) -> str:
    m = re.match(r"^(\s*)(\d+)(\s+.*)$", line)
    return line if not m else f"{m.group(1)}{str(new_id).rjust(len(m.group(2)))}{m.group(3)}"

# ────────── 拆分函数 ────────────────────────────────────────────
def _split_file(src: Path, dst_root: Path, year: int):
    lines = src.read_text().splitlines()

    # 1) BACKWARD / FORWARD 行
    idx_back = next(i for i, l in enumerate(lines)
                    if re.match(r"^\s*\d+\s+(BACKWARD|FORWARD)", l))
    idx_init = idx_back + 1

    # 2) PRESSURE 行
    try:
        idx_cols = next(i for i, l in enumerate(lines[idx_init:], idx_init)
                        if re.match(r"^\s*\d+\s+PRESSURE", l))
    except StopIteration:
        raise ValueError("未找到 PRESSURE 行")

    init_lines = lines[idx_init:idx_cols]
    n = len(init_lines)                          # 真正轨迹数（1 或 10）
    if n < 1:
        raise ValueError("未检测到起点行")

    col_line   = lines[idx_cols]
    data_lines = lines[idx_cols + 1:]

    # 3) 自动判定“轨迹编号列”是第 0 列还是第 1 列
    id_col = 0
    ids0 = {int(l.split()[0]) for l in data_lines[:200] if l.split()}
    if not set(range(1, n + 1)).issubset(ids0):
        ids1 = {int(l.split()[1]) for l in data_lines[:200] if len(l.split()) > 1}
        if set(range(1, n + 1)).issubset(ids1):
            id_col = 1
        else:
            raise ValueError("无法判断编号列")

    header    = lines[:idx_back]
    back_line = lines[idx_back]

    for tid in range(1, n + 1):
        out_dir = dst_root / str(year) / f"P{tid}"
        out_dir.mkdir(parents=True, exist_ok=True)
        outfile = out_dir / src.name

        with outfile.open("w", encoding="utf-8") as fw:
            fw.write("\n".join(header) + "\n")
            fw.write(_renumber(back_line, 1) + "\n")
            fw.write(_renumber(init_lines[tid - 1], 1) + "\n")
            fw.write(col_line + "\n")
            for l in data_lines:
                parts = l.split()
                if not parts:
                    continue
                if int(parts[id_col]) == tid:
                    fw.write(_renumber(l, 1) + "\n")

# ────────── CLI ─────────────────────────────────────────────────
def _parse_range(text: str) -> Tuple[int, int]:
    m = re.fullmatch(r"\s*(\d{4})\s*-\s*(\d{4})\s*", text)
    if not m:
        raise argparse.ArgumentTypeError("区间示例：2019-2020")
    a, b = map(int, m.groups())
    return (a, b) if a <= b else (b, a)

def main():
    ap = argparse.ArgumentParser(description="拆分 HYSPLIT 多起点轨迹文件")
    ap.add_argument("input", help="源文件或目录")
    ap.add_argument("output", help="输出顶层目录")
    ap.add_argument("-r", "--range", type=_parse_range, help="年份区间 例如 1950-2020")
    args = ap.parse_args()

    src = Path(args.input).resolve()
    dst = Path(args.output).resolve()
    dst.mkdir(parents=True, exist_ok=True)

    yr_min, yr_max = args.range if args.range else (None, None)

    # 收集文件
    files = [src] if src.is_file() else [p for p in src.rglob("*") if p.is_file()]
    items = []
    for f in files:
        # ① 先看父目录纯数字四位
        y = None
        for p in f.parents:
            if re.fullmatch(r"(19|20)\d{2}", p.name):
                y = int(p.name)
                break
        # ② 再看文件名
        if y is None:
            y = _year_from_filename(f.name)
        if y and (yr_min is None or yr_min <= y <= yr_max):
            items.append((f, y))

    if not items:
        print("[!] 未找到符合年份条件的文件")
        return
    items.sort(key=lambda t: t[1])

    processed_years = set()
    for f, y in items:
        if y not in processed_years:
            print(f"正在处理年份 {y} …")
            processed_years.add(y)
        try:
            _split_file(f, dst, y)
        except Exception as e:
            print(f"[!] 跳过 {f.name} → {type(e).__name__}: {e}")

    print("全部年份处理完成。")

if __name__ == "__main__":
    main()
