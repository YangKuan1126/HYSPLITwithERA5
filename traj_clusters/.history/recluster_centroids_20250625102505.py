import re, glob, pathlib, pandas as pd

ROOT = pathlib.Path(r'F:\ERA5_pressure_level\traj_clusters')   # 月份目录的上一级
MONTH_TAG = '1979_2020_01_'  # 本次处理的月份前缀，可放循环

csv_path   = pathlib.Path('centroids_meta_clustered.csv')      # 上一步生成的 CSV
out_parent = ROOT / (MONTH_TAG.rstrip('_') + '_META')          # 输出放这里
out_parent.mkdir(parents=True, exist_ok=True)

# ---------- 1. 读取 CSV 得到 meta_cluster 映射 -----------------
df_meta = pd.read_csv(csv_path, encoding='utf-8-sig')
# 期望列: point, cluster_in_point, meta_cluster
key = df_meta.set_index(['point', 'cluster_in_point'])['meta_cluster'].to_dict()

# ---------- 2. 解析所有 merged_mean.tdump ---------------------
pat_begin  = re.compile(r'\d+\s+BACKWARD')
pat_press  = re.compile(r'^\s*1\s+PRESSURE')

def read_blocks(tdump_path: pathlib.Path):
    """返回 {local_cluster_id: list[str]}，含 header 与 PRESSURE 块"""
    lines  = tdump_path.read_text(encoding='utf-8', errors='ignore').splitlines(keepends=True)
    start  = next(i for i,l in enumerate(lines) if pat_begin.search(l))
    end    = next(i for i,l in enumerate(lines[start+1:], start+1) if pat_press.search(l))
    header = lines[:start+1]                   # 文件头 + "3 BACKWARD ..."
    blocks = {}
    cid = 0
    for line in lines[start+1:end]:
        if line.strip():                       # 非空行
            cid += 1
            blocks[cid] = header + [line]      # 只有一行坐标 header
    # PRESSURE 块：同样切 3 行一组
    cur = None
    for line in lines[end:]:
        if re.match(r'^\s*1\s*-9', line):      # 新 cluster 开头
            cur = 1
            cid = int(line.split()[0])         # 第一列
            blocks[cid].append(line)
        elif cur is not None:
            blocks[cid].append(line)
    return blocks

# ---------- 3. 写出按 meta_cluster 合并的 .tdump ---------------
meta_files = {}  # meta_id -> open file handle

for tdump in glob.glob(str(ROOT / f'{MONTH_TAG}P*/merged_mean.tdump')):
    point_id = pathlib.Path(tdump).parent.name         # 如 1979_2020_01_P3
    blocks   = read_blocks(pathlib.Path(tdump))
    for cid, lines in blocks.items():
        meta = key.get((point_id, cid))
        if meta is None:
            print(f'[WARN] 映射缺失 {point_id} C{cid}')
            continue

        fout = meta_files.get(meta)
        if fout is None:
            out_path = out_parent / f'meta_{meta:02d}.tdump'
            fout = out_path.open('w', encoding='utf-8')
            meta_files[meta] = fout
            # 写个说明行
            fout.write(f'# META_CLUSTER {meta}  (组合轨迹)\n')

        # 写来源信息 + 该质心所有行
        fout.write(f'# from {tdump}\n')
        fout.writelines(lines)
        fout.write('\n')

# 关闭文件
for f in meta_files.values():
    f.close()

print(f'✅ 已在 {out_parent} 生成 {len(meta_files)} 个 meta_cluster 合并文件')
