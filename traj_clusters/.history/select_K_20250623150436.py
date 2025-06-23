#!/usr/bin/env python3
"""
根据 DELPCT 自动选择最佳聚类数 K，使用 kneed 库判断肘部。
输入：含三列：倒序 K、TSV、DELPCT（%变化）；
输出：推荐聚类数 K
"""

import numpy as np
import argparse
from kneed import KneeLocator

def select_best_k_kneed(path, min_k=1, max_k=15, S=1.0, online=True):
    data = np.loadtxt(path, usecols=(0,1,2))
    ks = data[:, 1].astype(int)
    pct = data[:, 2]

    # 筛选指定范围并正序
    mask = (ks >= min_k) & (ks <= max_k)
    ks_s, pct_s = ks[mask], pct[mask]
    order = np.argsort(ks_s)
    ks_s, pct_s = ks_s[order], pct_s[order]

    # 自动识别肘部（拐点）
    kl = KneeLocator(
        ks_s, pct_s,
        curve="convex", direction="decreasing",
        S=S, online=online
    )
    best = kl.knee
    return best if best is not None else ks_s[np.argmax(pct_s)]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="使用 kneed 自动识别 DELPCT 文件中的最佳聚类数"
    )
    parser.add_argument('file', help='含 K TSV DELPCT 三列的文件路径')
    parser.add_argument('--min', type=int, default=1, help='最小 K（含）')
    parser.add_argument('--max', type=int, default=15, help='最大 K（含）')
    parser.add_argument('--S', type=float, default=1.0, help='kneed S 参数（灵敏度）')
    parser.add_argument('--online', action='store_true', help='启用 online 模式')

    args = parser.parse_args()
    best_k = select_best_k_kneed(
        args.file, min_k=args.min, max_k=args.max,
        S=args.S, online=args.online
    )
    print(best_k)
