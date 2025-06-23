#!/usr/bin/env python3
"""
根据 DELPCT 自动选择最佳聚类数 K，无绘图，基于 TSV% 值拐点判断。
输入：含三列：K TSV DELPCT（%变化），其中 K 为第二列倒序的数据。
输出：推荐聚类数 K
"""

import numpy as np
import argparse

import numpy as np

def select_best_k(path, pct_abs_thresh=15.0, pct_jump_thresh=10.0):
    """
    根据 CLUSEND（包含三列：倒序的 K、TSV、DELPCT(%变化)）自动选取最佳聚类数 K。
    如果选出的 K <= 2，则返回 3。
    """
    # 读取文件：列索引 0=原倒序行号、1=K、2=DELPCT
    data = np.loadtxt(path, usecols=(0,1,2))
    ks = data[:, 1].astype(int)   # 第二列：原本倒序的 K 数
    delpct = data[:, 2]           # 第三列：TSV 百分比变化

    # 计算 DELPCT 的增量（连续两次的差值）
    diffs = np.diff(delpct)

    # 查找第一个既满足 delpct >= pct_abs_thresh 又满足增量 >= pct_jump_thresh 的点
    for i in range(len(diffs)):
        if delpct[i] >= pct_abs_thresh and diffs[i] >= pct_jump_thresh:
            best_k = ks[i]
            break
    else:
        # 如果循环未 break，取 DELPCT 最大值对应的 K
        idx = np.argmax(delpct)
        best_k = ks[idx]

    # 新增判断：若 best_k 小于等于 2，则强制设为 3
    if best_k <= 2:
        best_k = 3

    return best_k

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="从 DELPCT 文件自动选择合理聚类数 K（无图）"
    )
    parser.add_argument('file', help="路径文件，含 K TSV DELPCT 三列")
    parser.add_argument('--abs', type=float, default=15.0,
                        help="最低 DELPCT 值门阈（%%），默认 15%%")
    parser.add_argument('--jump', type=float, default=10.0,
                        help="DEL PCT 的跃升门阈（%%），默认 10%%")
    args = parser.parse_args()

    # 调用已经包含 <=2 强制为 3 的函数
    K = select_best_k(args.file, args.abs, args.jump)
    print(K)

