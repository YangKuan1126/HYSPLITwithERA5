import re, glob, pathlib, pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

# -------- 1. 读取 10 个 merged_mean.tdump 并抽取质心 -----------------
root = pathlib.Path(r'F:\ERA5_pressure_level\traj_clusters\1979_2020_01_')
centroid_rows = []   # 存储所有质心

pattern_begin = re.compile(r'\d+\s+BACKWARD')   # “3 BACKWARD …”
pattern_press = re.compile(r'^\s*1\s+PRESSURE')  # “1 PRESSURE”
float_re = re.compile(r'[-+]?\d+\.\d+')

def extract_centroids(tdump):
    with open(tdump, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    # 找到开始与结束行号
    start = next(i for i,l in enumerate(lines) if pattern_begin.search(l))
    end   = next(i for i,l in enumerate(lines[start+1:], start+1) if pattern_press.search(l))
    # 去掉第一行(标头)后，直到 end 之前
    block = lines[start+1 : end]

    out = []
    for idx, line in enumerate(block, 1):
        nums = float_re.findall(line)
        if len(nums) >= 3:
            lat, lon, press = map(float, nums[-3:])
            out.append((idx, lat, lon, press))
    return out

# 遍历十个点
for tdump in glob.glob(str(root) + 'P*/merged_mean.tdump'):
    point_id = pathlib.Path(tdump).parent.name  # 例如 1979_2020_01_P1
    for cid, lat, lon, press in extract_centroids(tdump):
        centroid_rows.append({
            'point': point_id,
            'cluster_in_point': cid,
            'lat': lat,
            'lon': lon,
            'press': press
        })

df = pd.DataFrame(centroid_rows)
print('读取完毕，质心数量:', len(df))

# -------- 2. 选择特征并标准化 -----------------
X = df[['lat', 'lon']].values                  # 只按空间聚类
X_std = StandardScaler().fit_transform(X)

# -------- 3. 自动寻找最佳 K (轮廓系数) ----------
best_k, best_score, best_labels = None, -1, None
for k in range(2, min(10, len(df))):           # 至多 10
    labels = KMeans(k, random_state=0, n_init='auto').fit_predict(X_std)
    score  = silhouette_score(X_std, labels)
    if score > best_score:
        best_k, best_score, best_labels = k, score, labels

print(f'自动选出 K = {best_k}  (silhouette={best_score:.3f})')
df['meta_cluster'] = best_labels

# -------- 4. 保存 & （可选）简单可视化 ----------
df.to_csv('centroids_meta_clustered.csv', index=False, encoding='utf-8-sig')
print('已写出 centroids_meta_clustered.csv')

# 若想画散点图：
try:
    import matplotlib.pyplot as plt
    for m in sorted(df.meta_cluster.unique()):
        sub = df[df.meta_cluster==m]
        plt.scatter(sub.lon, sub.lat, label=f'簇{m}', alpha=.7)
    plt.legend(); plt.xlabel('经度'); plt.ylabel('纬度'); plt.title('二次聚类结果')
    plt.show()
except ImportError:
    pass
