# -*- coding: utf-8 -*-
"""
meta_cluster_tracks.py
----------------------
把一个月份(10 个点)的所有 C*_mean 质心轨迹重新聚类，
生成新的 C*_M_mean 文件，仍为 HYSPLIT tdump 格式。
"""

import sys, re, glob, pathlib
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

ROOT = pathlib.Path(r"F:\ERA5_pressure_level\traj_clusters")   # 顶层路径

# ---------- 实用正则 ----------
RE_HEAD  = re.compile(r"^\s*\d+\s+BACKWARD")   # 如 "3 BACKWARD OMEGA MERGMEAN"
RE_PRESS = re.compile(r"^\s*1\s+PRESSURE")

def parse_one_cmean(path: pathlib.Path):
    """
    读取一个 Cx_y_mean 文件，返回:
        (lat, lon, press, block_lines[list[str]])
    """
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines(keepends=True)
    head_i  = next(i for i,l in enumerate(lines) if RE_HEAD.search(l))
    press_i = next(i for i,l in enumerate(lines[head_i+1:], head_i+1) if RE_PRESS.search(l))
    # 头后第一行就是质心坐标
    lat, lon, press = map(float, lines[head_i+1].split()[-3:])
    block = lines[:press_i] + lines[press_i:]  # 把整个文件都记录
    return lat, lon, press, block

def find_cmean_files(month_tag: str):
    """返回所有点下的 C*_mean 文件路径列表"""
    files = []
    for pdir in ROOT.glob(f"{month_tag}_P*/C*_mean"):
        files.append(pdir)
    return sorted(files)

def auto_k(X_std, kmax=10):
    best_k, best_s = None, -1
    for k in range(2, min(kmax, len(X_std))):
        lbl = KMeans(k, random_state=0, n_init=10).fit_predict(X_std)
        s   = silhouette_score(X_std, lbl)
        if s > best_s:
            best_k, best_s, best_lbl = k, s, lbl
    return best_k, best_lbl

def main(month_tag: str):
    files = find_cmean_files(month_tag)
    if not files:
        sys.exit(f"❌ 未找到任何 C*_mean 文件 under {ROOT}/{month_tag}_P*")

    # 1. 读取所有质心
    records = []
    for fp in files:
        lat, lon, press, block = parse_one_cmean(fp)
        cid = int(re.match(r"C(\d+)_", fp.name).group(1))  # 原簇号
        point = fp.parent.name                             # 1979_2020_01_P1
        records.append(dict(path=str(fp),
                            point=point,
                            orig_cluster=cid,
                            lat=lat, lon=lon, press=press,
                            block=block))

    df = pd.DataFrame(records)
    print("读取轨迹块:", len(df))

    # 2. 再聚类
    feats = df[['lat','lon']].values        # 只按空间；想加 press 列就改
    X_std = StandardScaler().fit_transform(feats)
    k, labels = auto_k(X_std, kmax=8)
    print(f"自动得到 meta_cluster K = {k}")
    df['meta'] = labels

    # 3. 输出
    out_dir = ROOT / f"{month_tag}_META"
    out_dir.mkdir(exist_ok=True)
    writers = {}  # meta -> open file handle

    for _, row in df.iterrows():
        meta = int(row.meta)
        fout = writers.get(meta)
        if fout is None:
            fout = (out_dir / f"C{meta+1}_{k}_M_mean").open("w", encoding="utf-8")
            writers[meta] = fout
            fout.write(f"# META_CLUSTER {meta+1}  (K={k})\n")

        fout.write(f"# from {row.path}\n")
        fout.writelines(row.block)
        fout.write("\n")

    for f in writers.values():
        f.close()

    print(f"✅ 完成！输出目录: {out_dir}, 生成 {len(writers)} 个 C*_M_mean 文件")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("用法: python meta_cluster_tracks.py 1979_2020_01")
    main(sys.argv[1])
