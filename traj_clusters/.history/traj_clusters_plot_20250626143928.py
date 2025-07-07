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
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib as mpl
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cartopy.io.shapereader as shpreader

# ---------- 绘图函数：58 mm 单图 ----------
def plot_month(tracks_3d, labels, shp_path, outfile):
    mpl.rcParams['font.sans-serif'] = ['Times New Roman']
    mpl.rcParams['axes.unicode_minus'] = False

    w, h = 58/25.4, 58/25.4*0.6
    fig  = plt.figure(figsize=(w, h), dpi=300)
    ax   = fig.add_subplot(1,1,1, projection=ccrs.PlateCarree())

    # 底图
    ax.set_extent([-25, 180, 0, 90])
    ax.coastlines(0.3, alpha=0.7)
    ax.add_feature(cfeature.BORDERS, linewidth=0.3, alpha=0.7)

    # 研究区
    ax.add_feature(
        cfeature.ShapelyFeature(
            shpreader.Reader(shp_path).geometries(),
            ccrs.PlateCarree(),
            edgecolor='black', facecolor='none', linewidth=1.0
        )
    )

    # 轨迹
    cmap = plt.get_cmap("tab10")
    colors = {cid: cmap(i) for i, cid in enumerate(np.unique(labels))}
    for lab, tr in zip(labels, tracks_3d):
        ax.plot(tr[:,1], tr[:,0], lw=0.5, alpha=0.6,
                transform=ccrs.PlateCarree(), color=colors[lab])

    # 刻度 & 网格（指定经纬线）
    xt = [-20, 20, 60, 100, 140, 180]
    yt = [20, 40, 60, 80]
    ax.set_xticks(xt, crs=ccrs.PlateCarree())
    ax.set_yticks(yt, crs=ccrs.PlateCarree())
    ax.set_xticklabels(['20°W'] + [f'{x}°E' for x in xt[1:]], fontsize=4)
    ax.set_yticklabels([f'{y}°N' for y in yt], fontsize=4)

    ax.gridlines(crs=ccrs.PlateCarree(), xlocs=xt, ylocs=yt,
                 color='grey', linestyle='--', linewidth=0.25, alpha=0.5,
                 draw_labels=False)

    ax.tick_params(direction='out', length=2, width=0.4, pad=1)

    # 外框 0.5
    for spine in ax.spines.values():
        spine.set_linewidth(0.5)

    plt.tight_layout()
    fig.savefig(outfile, dpi=300)
    plt.close(fig)

# ---------- 0. 全局配置 ----------
DATA_ROOT  = Path(r"F:\ERA5_pressure_level\traj_clusters")
SAVE_ROOT  = Path(r"F:\ERA5_pressure_level\traj_clusters_plot")
K          = 4                          # 固定簇数；如要自选可改
SKIP_ROWS  = 5                          # tdump 文件头行数
shp_path = r"E:\VIC_INPUT\汉江_流域边界.shp"   # 研究区 shp

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
    # c) 绘图
    png_path = save_dir / f"{month_tag}_traj.png"
    plot_month(tracks_3d, labels, shp_path, png_path)
    print("  月图已保存:", png_path)
