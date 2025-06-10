# Copyright (C) 1994, 1995, 1996, 1997, 1998, 1999, 2000, 2001, 2002,
# 2003, 2004, 2005, 2006, 2007, 2008, 2009  Free Software Foundation,
# Inc.
# This Makefile.in is free software; the Free Software Foundation
# gives unlimited permission to copy and/or distribute it,
# with or without modifications, as long as this notice is preserved.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY, to the extent permitted by law; without
# even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE.

# Makefile to be used with ECMWF ecCodes library
#22 jan 2018 (amc) added intel compiler options.
#26 aug 2019 (syz) include a Makefile.inc.
#28 aug 2019 (syz) moved ECCODES path and options to Makefile.inc.
# 强制使用 gfortran
FC := gfortran

# ecCodes 安装根目录
ECCODES_TOPDIR ?= /mnt/c/hysplit/eccodes-2.41.0

# Fortran 模块路径
ECCODESINC   = -I$(ECCODES_TOPDIR)/include

# 链接 ecCodes Fortran 接口和核心库
ECCODESLIBS  = -L$(ECCODES_TOPDIR)/lib -leccodes_f90 -leccodes

# 本地 hysplit 库
LIBHYS       = -L../metprog/library -lhysplit

# Fortran 编译与链接选项
FCFLAGS      = -g -ffree-form $(FFLAGS) $(FFLAGS_FREEFORM)
FCCOMPILE    = $(FC) $(ECCODESINC) $(FCFLAGS)
FCLINK       = $(FC) $(FCFLAGS)

# 可执行文件与目录
EXE          = ./
PGM          = era52arl

# 默认目标
all: $(PGM)

# 编译规则：.f -> .o
.SUFFIXES: .f .o
.f.o:
	$(FCCOMPILE) -c -o $@ $<

# 链接规则
$(PGM): $(PGM).o
	@rm -f $(EXE)/$(PGM)
	$(FCLINK) $< $(ECCODESLIBS) $(LIBHYS) -o $(EXE)/$(PGM)

# 清理
clean:
	rm -f $(EXE)/$(PGM) *.o











# include /mnt/c/hysplit/data2arl/hysplit_data2arl/Makefile.inc.gfortran

# EXE=./
# PGM=era52arl

# LIBHYS = -L../metprog/library -lhysplit

# FCFLAGS = -g $(FFLAGS) $(FFLAGS_FREEFORM)

# api2arl_DEPENDENCIES =  \
	# $(ECCODES_TOPDIR)/lib/libeccodes_f90.so \
	# $(ECCODES_TOPDIR)/lib/libeccodes.so
# FCCOMPILE = $(FC) $(ECCODESINC) $(FCFLAGS)
# FCLD = $(FC)
# FCLINK = $(FCLD) $(FCFLAGS) $(AM_LDFLAGS) \
	 # $(LDFLAGS) -o $(EXE)/$@

# .SUFFIXES:
# .SUFFIXES: .f .lo .o .obj

# $(PGM): $(PGM).o $(api2arl_DEPENDENCIES) 
	# @rm -f $(PGM)
	# $(FCLINK) $(PGM).o $(ECCODESLIBS) $(LIBHYS)


# .f.o:
	# $(FCCOMPILE) -c -o $@ $<  

# clean :
	 # rm -f $(EXE)/apidump
	 # rm -f $(EXE)/$(PGM)
	 # rm -f *.o
