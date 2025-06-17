from pathlib import Path
from disassemble_10traj_to_1traj import _year_from_filename   # 导入你的解析函数

root = Path(r"F:\ERA5_pressure_level\traj\1950")   # 修改为要检查的目录
out_file = Path(r"D:\Github\HYSPLITwithERA5\traj_clusters\parsed_years.txt")

lines = []
for f in root.rglob("*"):            # 递归遍历；若只查顶层用 iterdir()
    if f.is_file():
        y = _year_from_filename(f.name)
        lines.append(f"{f.name}\t{y}")

out_file.parent.mkdir(parents=True, exist_ok=True)
out_file.write_text("\n".join(lines), encoding="utf-8")
print(f"已写入解析结果：{out_file}  （共 {len(lines)} 行）")
