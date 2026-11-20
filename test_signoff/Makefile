SIM ?= verilator
TOPLEVEL_LANG = verilog
SRC_DIR = $(CURDIR)/../src
ifeq ($(GATES),yes)
VERILOG_SOURCES = $(PDK_MODELS)/primitives.v $(PDK_MODELS)/sky130_fd_sc_hd.v $(NETLIST)
COMPILE_ARGS += -DGL_TEST -DFUNCTIONAL -DUSE_POWER_PINS -DUNIT_DELAY=
else
PROJECT_SOURCES = tt_um_cokane_soc.v soc_core.v wb_decoder.v cokane_wb.v mac_wb.v picorv32.v mac_hybrid.sv mac_residue7_check.sv signed_residue7.sv secded_decoder.sv secded_encoder.sv
VERILOG_SOURCES = $(addprefix $(SRC_DIR)/,$(PROJECT_SOURCES))
endif
VERILOG_SOURCES += $(CURDIR)/host_tb.v
TOPLEVEL = tb
COCOTB_TEST_MODULES = test_host_inference
COMPILE_ARGS += -I$(SRC_DIR)
ifeq ($(SIM),verilator)
COMPILE_ARGS += --timing -Wno-fatal
else
COMPILE_ARGS += -g2012
endif
PLUSARGS += +firmware=$(FIRMWARE)
include $(shell cocotb-config --makefiles)/Makefile.sim
