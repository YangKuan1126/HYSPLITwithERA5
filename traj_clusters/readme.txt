如果计算的时间很长。比如计算1951到2020年1月的数据，可以调整以下的内容：
也就是CCONTROL的内容
240  这一行就不要改了
3    可以降低单个文件的读取效率
2    可以增加读取批量文件的效率
./
0
例如：
1991到2020年1月P1一共有3680个文件，但是经过上述的设置之后
cluster.exe会读取的实际数目为1732,这样可以大大减少运行的压力
内存的占用也比较合理，cluster.exe占用900m的内存

.\run_hysplit_cluster_new.ps1 -TrajRoot  "F:\ERA5_pressure_level\traj_points" -YearStart 1979 -YearEnd 2020 -Months 7 -Points P1 -KeepHours 06,18
