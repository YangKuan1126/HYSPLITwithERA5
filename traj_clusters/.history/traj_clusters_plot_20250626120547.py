"""
========================================
240 h 后向轨迹：批量 12 个月二级聚类 + 均值保存
========================================
输入根目录:  F:\ERA5_pressure_level\traj_clusters
  └── 1979_2020_01_P1\C1_3_mean.tdump ...
输出根目录: F:\ERA5_pressure_level\traj_clusters_plot\<月份标签>\
  ├── <月标签>_labels.csv
  └── cluster_1_mean.csv … cluster_K_mean.csv
"""

# ---------- 基础包 ----------
from pathlib import Path
import re, itertools
import numpy as np
import pandas as pd
from haversine import haversine_vector, Unit
from scipy.cluster.hierarchy import linkage, fcluster
import scipy.spatial.distance as ssd

# ---------- 0. 全局配置 ----------
DATA_ROOT  = Path(r"F:\ERA5_pressure_level\traj_clusters")
SAVE_ROOT  = Path(r"F:\ERA5_pressure_level\traj_clusters_plot")
K          = 4                          # 固定簇数；如要自选可改
SKIP_ROWS  = 5                          # tdump 文件头行数

# ---------- 1. 找出所有月份标签 ----------
month_tags = sorted({
    re.search(r"\d{4}_\d{4}_\d{2}", str(p)).group()
    for p in DATA_ROOT.rglob("*_P*/C*_mean*")
})
print("检测到月份：", month_tags)

# ---------- 2. 月度循环 ----------
for month_tag in month_tags:
    print(f"\n=== 处理 {month_tag} ===")
    # 2-1 收集该月所有 mean 文件
    mean_files = sorted([
        f for f in DATA_ROOT.rglob(f"{month_tag}_P*/C*_mean*")
        if re.fullmatch(r"C\d+_\d+_mean(?:\.tdump)?", f.name)
    ])
    if not mean_files:
        print("  未找到文件，跳过…")
        continue
    N = len(mean_files)
    print(f"  发现 {N} 条平均轨迹")

    # 2-2 解析 tdump → (T,2)
    def parse_tdump(path):
        df = pd.read_csv(
            path, skiprows=SKIP_ROWS, sep=r"\s+",
            names=["traj","sb","year","mon","day","hrs",
                   "min","eight","cnt","lat","lon","p","zero"]
        )
        return df[["lat","lon"]].to_numpy(float)

    tracks = [parse_tdump(f) for f in mean_files]
    lengths = {len(t) for t in tracks}
    if len(lengths) != 1:
        raise ValueError(f"{month_tag}: 轨迹长度不一致 {sorted(lengths)}")
    T = lengths.pop()
    tracks_3d = np.stack(tracks)

    # 2-3 距离矩阵
    D = np.zeros((N,N))
    for i,j in itertools.combinations(range(N),2):
        D[i,j] = D[j,i] = haversine_vector(
            tracks_3d[i], tracks_3d[j], Unit.KILOMETERS
        ).sum()
    condensed = ssd.squareform(D)

    # 2-4 Ward 聚类 & 标签
    labels = fcluster(linkage(condensed,'ward'), K, 'maxclust')
    print("  各簇样本量:", np.bincount(labels)[1:])

    # 2-5 创建输出目录
    save_dir = SAVE_ROOT / month_tag
    save_dir.mkdir(parents=True, exist_ok=True)

    # a) 标签 CSV（含文件名和完整路径）
    df_lab = pd.DataFrame({
        "file":  [f.name for f in mean_files],
        "path":  [str(f) for f in mean_files],
        "cluster": labels
    })
    label_csv = save_dir / f"{month_tag}_labels.csv"
    df_lab.to_csv(label_csv, index=False, encoding="utf-8-sig")
    print("  标签保存:", label_csv.name)

    # b) 各簇均值轨迹
    for cid in np.unique(labels):
        mean_xy = tracks_3d[labels==cid].mean(axis=0)
        pd.DataFrame(mean_xy, columns=["lat","lon"]).to_csv(
            save_dir / f"cluster_{cid}_mean.csv", index=False
        )
    print("  均值轨迹保存至:", save_dir)
