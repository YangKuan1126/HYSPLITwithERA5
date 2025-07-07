"""
meta_cluster_mean.py — 计算“月度‐多点”二次聚类后的平均后向轨迹
====================================================
给定一个“*META”目录（由先前脚本 `recluster_centroids.py` 生成），
其中包含若干 `C*_M_mean` 轨迹文件，每个文件是一批同一
meta‑cluster 内成员轨迹的**拼接**。本脚本将：

1. 从每个 *M_mean 文件中分割出原始成员轨迹（241 行/条）。
2. 对所有成员轨迹在 **纬度、经度、气压** 三个维度分别求
   时刻（−240…0 h）上的算术平均。
3. 将得到的“平均轨迹”写成 HYSPLIT 可读格式：
      * 标头行使用 *BACKWARD OMEGA MEANTRAJ*，经纬度气压为
        t=0 h 的平均值；
      * **轨迹顺序**由 0 h → −240 h（即 0 行在前，−240 在末）。

输出文件名：`C?_?_META_mean.tdump` → `C?_?_META_mean_avg.tdump`。

用法示例：
    python meta_cluster_mean.py F:/ERA5_pressure_level/traj_clusters/1979_2020_01_META
"""
from __future__ import annotations

import pathlib
import sys
from typing import List
import numpy as np

# ------------------------------------------------------------
# 解析 / 写入工具函数
# ------------------------------------------------------------

ROWS_PER_TRAJ = 241  # 每条后向轨迹固定 241 行（0, -1, …, -240）


def split_blocks(lines: List[str], rows: int = ROWS_PER_TRAJ) -> List[List[str]]:
    """将 *M_mean 文件分割为若干轨迹块（含首行 PRESSURE）。"""
    blocks: List[List[str]] = []
    buf: List[str] = []
    for ln in lines:
        buf.append(ln)
        if len(buf) == rows + 1:  # +1 because first PRESSURE header line
            blocks.append(buf)
            buf = []
    if buf:
        print("[WARN] 遇到残缺轨迹块，已忽略")
    return blocks


def track_to_array(block: List[str]) -> np.ndarray:
    """将单条轨迹块转为 (241, 3) 实数数组：lat, lon, p。"""
    data = []
    for ln in block[1:]:  # 跳过 PRESSURE 行
        parts = ln.strip().split()
        if len(parts) < 3:
            continue
        lat = float(parts[-4])
        lon = float(parts[-3])
        p = float(parts[-2])
        data.append((lat, lon, p))
    if len(data) != ROWS_PER_TRAJ:
        raise ValueError("轨迹行数不足 241 行")
    return np.array(data)  # shape (241, 3)


def array_to_block(arr: np.ndarray, header: str) -> List[str]:
    """将平均数组与原首行信息拼回 HYSPLIT block (返回行列表)。"""
    out = [header]
    for step, (lat, lon, p) in enumerate(arr):
        # 时间戳：保持 −step 值；其余字段按 HYSPLIT 要求固定
        # 我们保留： type=1, hy=1, year=xx, month=xx… 这里简化固定 1
        tt = -step  # 0, -1, … -240
        out.append(f"     1     1     1     1     1     1     1   -88 {tt:6.1f}   {lat:8.3f}   {lon:8.3f}  {p:7.1f}      0.0")
    return out


# ------------------------------------------------------------
# 主处理逻辑
# ------------------------------------------------------------

def process_one_file(fp: pathlib.Path) -> None:
    lines = fp.read_text(encoding="ascii", errors="ignore").splitlines()
    if not lines:
        print(f"[WARN] 空文件跳过: {fp.name}")
        return

    # 旧 header (例如 " 3 BACKWARD OMEGA MERGMEAN")
    old_header = lines[0]
    blocks = split_blocks(lines[1:])  # 跳过旧 header
    if not blocks:
        print(f"[WARN] {fp.name} 无有效轨迹，跳过")
        return

    arrs = np.stack([track_to_array(b) for b in blocks])  # shape (n,241,3)
    mean_xyz = arrs.mean(axis=0)  # (241,3)

    # 反转顺序：0 h 在最前，−240 h 在最后
    mean_xyz = mean_xyz[::-1]  # now step 0 行 first, step 240 行 last

    # 构造新 header：使用平均经纬压
    lat0, lon0, p0 = mean_xyz[0]  # t=0 h 平均值
    new_header = f"     1 BACKWARD OMEGA    MEANTRAJ\n     1     1     1     1     1     1   {lat0:6.3f}  {lon0:7.3f}  {p0:7.1f}"

    block = array_to_block(mean_xyz, new_header)
    out_path = fp.with_name(fp.stem + "_avg.tdump")
    out_path.write_text("\n".join(block) + "\n", encoding="ascii")
    print(f"✅ 写入平均轨迹 → {out_path.name}")


def main(meta_dir: str) -> None:
    meta = pathlib.Path(meta_dir)
    if not meta.is_dir():
        sys.exit("❌ 路径不存在或非目录")

    for fp in sorted(meta.glob("C*_M_mean")):
        process_one_file(fp)

    print("🎉 全部完成。")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("用法: python meta_cluster_mean.py <META_dir>")
    main(sys.argv[1])
