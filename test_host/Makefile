SIM ?= icarus
TOPLEVEL_LANG = verilog
SRC_DIR = $(CURDIR)/../src
PROJECT_SOURCES = tt_um_cokane_soc.v soc_core.v wb_decoder.v cokane_wb.v mac_wb.v picorv32.v mac_hybrid.sv mac_residue7_check.sv signed_residue7.sv secded_decoder.sv secded_encoder.sv
ifeq ($(GATES),yes)
VERILOG_SOURCES = $(PDK_ROOT)/sky130A/libs.ref/sky130_fd_sc_hd/verilog/primitives.v $(PDK_ROOT)/sky130A/libs.ref/sky130_fd_sc_hd/verilog/sky130_fd_sc_hd.v $(CURDIR)/../layout/tt_um_cokane_soc.pnl.v
COMPILE_ARGS += -DGL_TEST -DFUNCTIONAL -DUSE_POWER_PINS -DUNIT_DELAY=\#1
else
VERILOG_SOURCES = $(addprefix $(SRC_DIR)/,$(PROJECT_SOURCES))
endif
VERILOG_SOURCES += $(CURDIR)/../test/tb.v
COMPILE_ARGS += -I$(SRC_DIR)
TOPLEVEL = tb
COCOTB_TEST_MODULES = test_host
include $(shell cocotb-config --makefiles)/Makefile.sim
