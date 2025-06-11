# HYSPLIT 与 ERA5 使用指南 | HYSPLIT with ERA5

## 📚 目录 | Table of Contents
- [# HYSPLITwithERA5](##-hysplitwithera5)
- [1. 通过IDM批量下载ERA5的pressure_level数据](#1-通过idm批量下载era5的pressure_level数据)
- [2. 通过grib_count在*WSL*中对<pressure_level>.grib进行检查](#2-通过grib_count在wsl中对<pressure_level>grib进行检查)
- [3. 对不完整的<pressure_level>.grib 数据进行删除和重新下载](#3-对不完整的<pressure_level>grib-数据进行删除和重新下载)
- [4. 检查重新下载的之间记录为不完整的<pressure_level>.grib](#4-检查重新下载的之间记录为不完整的<pressure_level>grib)
- [5. 下载地面数据 <single_level>.grib](#5-下载地面数据-<single_level>grib)
- [6. 自动化整个下载过程](#6-自动化整个下载过程)
- [1. 下载hysplit模型到Windows](#1-下载hysplit模型到windows)
- [2. 定义自己的SETUP.CFG文件](#2-定义自己的setupcfg文件)
- [3. 在*powershell*界面去批量运行后向轨迹模拟](#3-在powershell界面去批量运行后向轨迹模拟)

---

## # HYSPLITwithERA5

| 中文说明 | English Description |
|----------|----------------------|
| ## 下载ERA5数据 |  |


## 1. 通过IDM批量下载ERA5的pressure_level数据

| 中文说明 | English Description |
|----------|----------------------|
| 1.ERA5_6h_pressure_level_1month-WEEKLY.py 这个脚本可以实现的功能： |  |
| a) 定义下载的时间范围（ERA5_pressure_level的一次性最多提交150个任务，过大的文件ERA5网站的处理时间很长） |  |
| b) 可以在中断部分继续下载，不仅可以根据目录中的.grib文件，也可以根据.arl文件（驱动hysplit的数据） |  |
| c) 记录下载路径在*submitted_tasks.txt*中，一个文件名对应于一个链接，方便后续数据处理中出现问题可以从新下载，但是要注意下载链接的有效时间 |  |
| d) 由于我的目的是下载ERA5数据去驱动hysplit模型计算后向轨迹，后向追踪的时间为10天，同时需要计算轨迹的水汽运载量，如果你也有相似的需求可以直接使用我的变量设置，但是经纬度范围需要根据自己的研究区调整，这样可以帮你剩下很多时间和硬盘空间 |  |
| e) 驱动hysplit模型的数据类型需要根据自己的项目去查，再脚本中只需要对对应的部分进行修改即可 |  |
| f) 该脚本的下载过程是基于IDM这个软件，因而需要提前准备好这个软件 |  |
| g) 数据的下载格式为.grib,该格式占用的硬盘空间比netcdf文件小很多，但是在python中处理起来没有nc文件快 |  |


## 2. 通过grib_count在*WSL*中对<pressure_level>.grib进行检查

| 中文说明 | English Description |
|----------|----------------------|
| 为什么要对下载的数据进行检查，这一步比较耗费时间，但是是值得的，我想问题可能出现在IDM下载软件上，因为通过此方式下载的数据有概率会出现缺失的情况，因而我在*2.check_grib.sh*这个脚本中在WSL中使用了*grib_count <fiels_name>.grib* 这个命令对.grib的数据进行检查，对于完整的数据输入该命令会输出一串数字，而对于不完整的.grib文件则会报错，*2.check_grib.sh*脚本可以批量地统计指定路径下哪些文件是不完整，并会将不完整的文件路径以及文件名称记录在*incomplete_grib_files.txt*中 |  |
| grib_count的安装过程：sudo apt-get install wgrib2 |  |


## 3. 对不完整的<pressure_level>.grib 数据进行删除和重新下载

| 中文说明 | English Description |
|----------|----------------------|
| 首先通过重新下载可以解决数据不完整的问题，*3.WEEKLY_continue.py* 可根据 *incomplete_grib_files.txt* 指定不完整文件在 *submitted_tasks.txt* 中的链接先删除不完整的数据，然后根据下载链接进行重新下载，还是要注意链接的保质期 |  |


## 4. 检查重新下载的之间记录为不完整的<pressure_level>.grib

| 中文说明 | English Description |
|----------|----------------------|
| *4.check_incomplete_grib.sh* 会对 *incomplete_grib_files.txt* 中指定的文件进行grib_count检查 |  |


## 5. 下载地面数据 <single_level>.grib

| 中文说明 | English Description |
|----------|----------------------|
| 驱动hysplit模型需要气压层数据，同时也需要地面数据，两者的下载原理相同，不同的只是命名的方式不同 |  |


## 6. 自动化整个下载过程

| 中文说明 | English Description |
|----------|----------------------|
| *auto_download_check.bat* 将这个下载数据，检查数据的流程集中在这个脚本中，运行这个自动化脚本需要指定相应的路径和安装WSL，然后运行它等待完成即可完成数据下载 |  |
| ## 处理ERA5数据，将其转换为.arl格式 |  |
| #convert_era52arl# 文件夹内包含了已经编译好的era52arl程序，*era52arl.cfg* 是指定气压层变量和地面变量的核心文件，其中变量的名称和变量的代号要在ERA5的网站上去查找，变量的设置要根据自己的项目进行调整，在设置完 |  |
| #convert_era52arl# 文件夹内包含了已经编译好的era52arl程序，*era52arl.cfg* 是指定气压层变量和地面变量的核心文件，其中变量的名称和变量的代号要在ERA5的网站上去查找，变量的设置要根据自己的项目进行调整，在设置完 *era52arl.cfg* 之后就可以使用 *convert_grib_to_arl_WEEKLY.sh* 通过指定时间对当前路径下的<pressure_level>.grib 和 <single_level>.grib 以及 *era52arl.cfg* 进行转换，也就是说.grib文件最好存放在 #convert_era52arl# 这个文件夹内，数据会转换为.arl格式，用以驱动hysplit模型，.arl格式的文件比.grib格式的文件占用的硬盘空间更小。 |  |
| ## 批量运行hysplt模型 |  |


## 1. 下载hysplit模型到Windows

| 中文说明 | English Description |
|----------|----------------------|
| https://www.ready.noaa.gov/HYSPLIT.php 这是它的网址，进去很容易就能看到下载链接，下载非注册版本，一定要安装在C盘的根目录下 |  |


## 2. 定义自己的SETUP.CFG文件

| 中文说明 | English Description |
|----------|----------------------|
| 首先需要根据hysplit的图形界面对软件进行熟悉，然后建议在图形界面中事先定义好自己的SETUP.CFG文件，该文件记录了输入和输出数据的关键信息，一定要先定义好这个文件再去运行模型 |  |


## 3. 在*powershell*界面去批量运行后向轨迹模拟

| 中文说明 | English Description |
|----------|----------------------|
| *batch_hysplit_new.ps1* 可以批量生成CONTROL文件然后驱动hysplit模型，hysplit一次最多提交12个文件气象数据文件，我的项目是4个月为12个文件，也就是每四个月需要更换一次气象数据文件，同时计算完四个月后会删除对应时间的数据，仅保留部分数据用在 *batch_hysplit_rest.ps1* 中，该脚本是补充 *batch_hysplit_new.ps1* 中没有设计的日期的数据的运算 |  |
