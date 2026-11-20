SIM ?= icarus
TOPLEVEL_LANG = verilog
VERILOG_SOURCES = $(CURDIR)/../src/cokane_wb.v $(CURDIR)/tb.v
TOPLEVEL = tb
COCOTB_TEST_MODULES = test_cokane
COMPILE_ARGS += -g2012 -Wall
include $(shell cocotb-config --makefiles)/Makefile.sim
