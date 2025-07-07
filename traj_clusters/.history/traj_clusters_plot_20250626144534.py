"""
========================================
240 h 后向轨迹：批量 12 个月二级聚类 + 图表输出
========================================
"""

# ---------- 通用包 ----------
from pathlib import Path
import re, itertools
import numpy as np, pandas as pd
from haversine import haversine_vector, Unit
import scipy.spatial.distance as ssd
from scipy.cluster.hierarchy import linkage, fcluster

# ---------- 绘图 ----------
import matplotlib.pyplot as plt
import matplotlib as mpl
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cartopy.io.shapereader as shpreader

# ---------- 绘图函数：单月 / 任意轨迹集合 ----------
def plot_month(tracks_3d, labels, shp_path, outfile,
               lw=0.5, alpha=0.6):
    mpl.rcParams['font.sans-serif'] = ['Times New Roman']
    mpl.rcParams['axes.unicode_minus'] = False

    w, h = 58/25.4, 58/25.4*0.6  # 58 mm × 35 mm
    fig  = plt.figure(figsize=(w, h), dpi=300)
    ax   = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())

    # ---- 底图 ----
    ax.set_extent([-25, 180, 0, 90])
    ax.coastlines(linewidth=0.3, alpha=0.7)
    ax.add_feature(cfeature.BORDERS, linewidth=0.3, alpha=0.7)

    # ---- 研究区 ----
    ax.add_feature(
        cfeature.ShapelyFeature(
            shpreader.Reader(shp_path).geometries(),
            ccrs.PlateCarree(),
            edgecolor='black', facecolor='none', linewidth=1.0
        )
    )

    # ---- 轨迹 ----
    cmap   = plt.get_cmap('tab10')
    colors = {cid: cmap(i) for i, cid in enumerate(np.unique(labels))}
    for lab, tr in zip(labels, tracks_3d):
        ax.plot(tr[:, 1], tr[:, 0], transform=ccrs.PlateCarree(),
                color=colors[lab], lw=lw, alpha=alpha)

    # ---- 刻度 & 网格 ----
    xticks = [-20, 20, 60, 100, 140, 180]
    yticks = [20, 40, 60, 80]
    ax.set_xticks(xticks, crs=ccrs.PlateCarree())
    ax.set_yticks(yticks, crs=ccrs.PlateCarree())
    ax.set_xticklabels(['20°W'] + [f'{x}°E' for x in xticks[1:]], fontsize=4)
    ax.set_yticklabels([f'{y}°N' for y in yticks], fontsize=4)

    ax.gridlines(crs=ccrs.PlateCarree(),
                 xlocs=xticks, ylocs=yticks,
                 color='grey', linestyle='--', linewidth=0.25,
                 alpha=0.5, draw_labels=False)

    ax.tick_params(direction='out', length=2, width=0.4, pad=1)

    # ---- 外框线宽 0.5 ----
    for spine in ax.spines.values():
        spine.set_linewidth(0.5)

    plt.tight_layout()
    fig.savefig(outfile, dpi=300)
    plt.close(fig)

# ---------- 全局配置 ----------
DATA_ROOT  = Path(r"F:\ERA5_pressure_level\traj_clusters")
SAVE_ROOT  = Path(r"F:\ERA5_pressure_level\traj_clusters_plot")
K          = 4
SKIP_ROWS  = 5
shp_path   = r"E:\VIC_INPUT\汉江_流域边界.shp"

# ---------- 1. 取月份标签 ----------
month_tags = sorted({
    re.search(r"\d{4}_\d{4}_\d{2}", str(p)).group()
    for p in DATA_ROOT.rglob("*_P*/C*_mean*")
})
print("检测到月份：", month_tags)

# ---------- 2. 月度循环 ----------
for month_tag in month_tags:
    print(f"\n=== 处理 {month_tag} ===")
    mean_files = sorted([
        f for f in DATA_ROOT.rglob(f"{month_tag}_P*/C*_mean*")
        if re.fullmatch(r"C\d+_\d+_mean(?:\.tdump)?", f.name)
    ])
    if not mean_files:
        print("  无文件，跳过…")
        continue
    N = len(mean_files)

    # -- 解析 --
    def parse_tdump(p):
        df = pd.read_csv(p, skiprows=SKIP_ROWS, sep=r"\s+",
                         names=["traj","sb","year","mon","day","hrs",
                                "min","eight","cnt","lat","lon","p","zero"])
        return df[["lat","lon"]].to_numpy(float)

    tracks = [parse_tdump(f) for f in mean_files]
    assert len({len(t) for t in tracks}) == 1, "轨迹长度不一"
    tracks_3d = np.stack(tracks)

    # -- 距离 & 聚类 --
    D = np.zeros((N,N))
    for i,j in itertools.combinations(range(N),2):
        D[i,j] = D[j,i] = haversine_vector(
            tracks_3d[i], tracks_3d[j], Unit.KILOMETERS).sum()
    labels = fcluster(linkage(ssd.squareform(D), 'ward'), K, 'maxclust')

    # -- 输出目录 --
    out_dir = SAVE_ROOT / month_tag
    out_dir.mkdir(parents=True, exist_ok=True)

    # -- CSV：标签 --
    pd.DataFrame({
        "file":[f.name for f in mean_files],
        "path":[str(f) for f in mean_files],
        "cluster":labels
    }).to_csv(out_dir / f"{month_tag}_labels.csv",
              index=False, encoding="utf-8-sig")

    # -- CSV：簇均值 & 收集绘图 --
    mean_tracks, mean_labels = [], []
    for cid in np.unique(labels):
        mean_xy = tracks_3d[labels==cid].mean(axis=0)
        mean_tracks.append(mean_xy)
        mean_labels.append(cid)
        pd.DataFrame(mean_xy, columns=["lat","lon"]).to_csv(
            out_dir / f"cluster_{cid}_mean.csv", index=False)

    # -- PNG：全部轨迹 --
    plot_month(tracks_3d, labels, shp_path,
               out_dir / f"{month_tag}_traj.png")

    # -- PNG：均值轨迹 --
    plot_month(np.array(mean_tracks), np.array(mean_labels), shp_path,
               out_dir / f"{month_tag}_traj_MEAN.png",
               lw=1.2, alpha=0.9)

    print(f"  完成 {month_tag}: CSV + 图已保存")
