#!/usr/bin/env python3
"""
根据 DELPCT 自动选择最佳聚类数 K，无绘图，基于 TSV% 值拐点判断。
输入：含三列：K TSV DELPCT（%变化），其中 K 为第二列倒序的数据。
输出：推荐聚类数 K
"""

import numpy as np
import argparse

def select_best_k(path, pct_abs_thresh=10.0, pct_jump_thresh=5.0):
    data = np.loadtxt(path, usecols=(0,1,2))
    ks = data[:, 1].astype(int)        # 第二列：原本倒序的 K 数
    delpct = data[:, 2]

    # 计算 DELPCT 的增量（连续两个 DELPCT 差值）
    diffs = np.diff(delpct)
    # 触发条件：delpct 当前 ≥ pct_abs_thresh，且变化(diff) ≥ pct_jump_thresh，选择该点对应的 K
    for i in range(len(diffs)):
        if delpct[i] >= pct_abs_thresh and diffs[i] >= pct_jump_thresh:
            return ks[i]

    # 若未找到，则选最大 DELPCT 点对应 K
    idx = np.argmax(delpct)
    return ks[idx]+1

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="从 DELPCT 文件自动选择合理聚类数 K（无图）"
    )
    parser.add_argument('file', help="路径文件，含 K TSV DELPCT 三列")
    parser.add_argument('--abs', type=float, default=15.0,
                        help="最低 DELPCT 值门阈（%%），默认 15%%")
    parser.add_argument('--jump', type=float, default=10.0,
                        help="DEL PCT 的躍升门阈（%%），默认 10%%")
    args = parser.parse_args()

    K = select_best_k(args.file, args.abs, args.jump)
    print(K)
