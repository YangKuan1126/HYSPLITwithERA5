"""
=========================================
240 h 后向轨迹 —— 二级聚类 + 均值保存（动态月份）
=========================================
读    ：F:\ERA5_pressure_level\traj_clusters\<月标签>_P*\C#_#_mean(.tdump)
写    ：F:\ERA5_pressure_level\traj_clusters_plot\<月标签>\
"""

# ------- 0. 基础包 -------
from pathlib import Path
import re, itertools
import numpy as np
import pandas as pd
from haversine import haversine_vector, Unit
from scipy.cluster.hierarchy import linkage, fcluster
import scipy.spatial.distance as ssd

# ------- 1. 配置输入根目录 -------
DATA_ROOT = Path(r"F:\ERA5_pressure_level\traj_clusters")

# rglob 递归搜索所有站点文件夹
mean_files = sorted([
    f for f in DATA_ROOT.rglob(r"*_P*/C*_mean*")
    if re.fullmatch(r"C\d+_\d+_mean(?:\.tdump)?", f.name)
])

print("发现平均轨迹文件：", len(mean_files))
if not mean_files:
    raise RuntimeError("未找到任何 C#_#_mean 文件，请检查路径！")

# ------- 2. 自动提取月份标签 (e.g. 1979_2020_03) -------
month_tag = re.search(r"\d{4}_\d{4}_\d{2}", str(mean_files[0])).group()
print("月份标签：", month_tag)

# ------- 3. 解析 tdump 为 (T,2) -------
def parse_tdump(path: Path) -> np.ndarray:
    df = pd.read_csv(
        path, skiprows=5, sep=r"\s+",
        names=[
            "traj_num","sb","year","mon","day","hrs",
            "min","eight","count","lat","lon","p","zero"
        ]
    )
    return df[["lat","lon"]].to_numpy(float)

tracks = [parse_tdump(f) for f in mean_files]
print(f"成功读取 {len(tracks)} 条平均轨迹")

# ------- 4. 校验长度一致 -------
lengths = {len(t) for t in tracks}
if len(lengths)!=1:
    raise ValueError(f"轨迹长度不一致：{sorted(lengths)}")
T = lengths.pop()

# ------- 5. 堆叠 3D 数组 -------
tracks_3d = np.stack(tracks)            # (N,T,2)
N = tracks_3d.shape[0]

# ------- 6. 距离矩阵 -------
D = np.zeros((N,N))
for i,j in itertools.combinations(range(N),2):
    D[i,j] = D[j,i] = haversine_vector(
        tracks_3d[i], tracks_3d[j], Unit.KILOMETERS
    ).sum()
condensed = ssd.squareform(D)

# ------- 7. Ward 聚类 (K=4) -------
K = 4
labels = fcluster(linkage(condensed,'ward'), K, 'maxclust')
print("各簇样本量：", np.bincount(labels)[1:])

# ------- 8. 输出目录 -------
SAVE_ROOT = Path(r"F:\ERA5_pressure_level\traj_clusters_plot") / month_tag
SAVE_ROOT.mkdir(parents=True, exist_ok=True)

# (a) 标签 CSV
label_csv = SAVE_ROOT / f"{month_tag}_labels.csv"
pd.DataFrame({"file":[f.name for f in mean_files], "cluster":labels}).to_csv(
    label_csv, index=False, encoding="utf-8-sig"
)
print("标签文件已保存：", label_csv)

# (b) 均值轨迹 CSV
for cid in np.unique(labels):
    mean_xy = tracks_3d[labels==cid].mean(axis=0)
    pd.DataFrame(mean_xy, columns=["lat","lon"]).to_csv(
        SAVE_ROOT / f"cluster_{cid}_mean.csv", index=False
    )

print("均值轨迹 CSV 文件：")
for p in sorted(SAVE_ROOT.glob("cluster_*_mean.csv")):
    print("  ", p)
