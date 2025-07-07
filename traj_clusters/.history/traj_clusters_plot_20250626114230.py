"""
=========================================
240 h 后向轨迹 —— 二级聚类 + 均值保存
=========================================
步骤：
1. 递归读取指定月份 (这里示例 1979_2020_03) 各站点的 C#_#_mean.tdump
2. 确保轨迹长度一致 → 堆叠成 (N, T, 2)
3. 计算两两轨迹累积 Haversine 距离 → 距离矩阵 D
4. 用 Ward 层次聚类；手动指定 K = 4
5. 保存标签到 CSV
6. 计算每个簇的均值轨迹并保存为 CSV
"""

# ----------- 0. 基础包 -----------
from pathlib import Path
import re
import pandas as pd
import numpy as np
import itertools
from haversine import haversine_vector, Unit
from scipy.cluster.hierarchy import linkage, fcluster
import scipy.spatial.distance as ssd

# ----------- 1. 读取所有 C#_#_mean 文件 -----------
root = Path(r"F:\ERA5_pressure_level\traj_clusters")   # 数据根目录

mean_files = sorted([
    f for f in root.rglob("1979_2020_03_P*/C*_mean*")  # 只扫 3 月的 P1…P10
    if re.fullmatch(r"C\d+_\d+_mean(?:\.tdump)?", f.name)
])

print("发现平均轨迹文件：", len(mean_files))

# ----------- 2. 把 tdump 解析为 (T,2) -------------

def parse_tdump(path: Path) -> np.ndarray:
    """
    读取 HYSPLIT mean.tdump，仅返回纬度、经度列
    默认文件头 6 行，剩余用空白分隔
    """
    df = pd.read_csv(
        path,
        skiprows=6,            # 如果头是真 5 行就改成 5
        sep=r"\s+",
        names=[
            "traj_num", "sb", "year", "mon", "day", "hrs",
            "min", "eight", "count", "lat", "lon", "p", "zero"
        ],
    )
    return df[["lat", "lon"]].to_numpy(float)

# 读取全部轨迹
tracks = [parse_tdump(f) for f in mean_files]
print(f"成功读取 {len(tracks)} 条平均轨迹")

# ----------- 3. 校验轨迹长度一致 -----------
lengths = {len(t) for t in tracks}
if len(lengths) != 1:
    raise ValueError(f"轨迹长度不一致：{sorted(lengths)}，请检查数据！")
T = lengths.pop()
print(f"统一长度：{T} 个时间步")

# ----------- 4. 堆叠成三维数组 -----------
tracks_3d = np.stack(tracks)  # shape = (N, T, 2)

# ----------- 5. 构造距离矩阵 -----------
N = tracks_3d.shape[0]
D = np.zeros((N, N))

for i, j in itertools.combinations(range(N), 2):
    # 对每个时间步累加球面距离
    D[i, j] = D[j, i] = haversine_vector(
        tracks_3d[i], tracks_3d[j], Unit.KILOMETERS
    ).sum()

condensed = ssd.squareform(D)  # (N·(N-1)/2,) 一维向量

# ----------- 6. Ward 层次聚类 -----------
Z = linkage(condensed, method="ward")

# ----------- 7. 指定簇数 K = 4 -----------
K = 4
labels = fcluster(Z, K, criterion="maxclust")
print("各簇样本量：", np.bincount(labels)[1:])

# ----------- 8. 保存标签 CSV -----------
LABEL_CSV = r"D:\Github\HYSPLITwithERA5\traj_clusters\mar_labels.csv"
pd.DataFrame({"file": [f.name for f in mean_files], "cluster": labels}).to_csv(
    LABEL_CSV, index=False, encoding="utf-8-sig"
)
print("标签已保存：", LABEL_CSV)

# ----------- 9. 计算并保存簇均值轨迹 -----------
SAVE_DIR = Path(r"D:\Github\HYSPLITwithERA5\traj_clusters\mar_means")  # 可自由改
SAVE_DIR.mkdir(parents=True, exist_ok=True)

for cid in np.unique(labels):
    mean_traj = tracks_3d[labels == cid].mean(axis=0)  # (T,2)
    pd.DataFrame(mean_traj, columns=["lat", "lon"]).to_csv(
        SAVE_DIR / f"cluster_{cid}_mean.csv", index=False
    )

print("均值轨迹 CSV 已生成：")
for p in sorted(SAVE_DIR.glob("*.csv")):
    print("  ", p)
