SIM ?= icarus
TOPLEVEL_LANG = verilog
SRC_DIR = $(CURDIR)/../src
PROJECT_SOURCES = soc_core.v wb_decoder.v cokane_wb.v mac_wb.v picorv32.v mac_hybrid.sv mac_residue7_check.sv signed_residue7.sv secded_decoder.sv secded_encoder.sv
VERILOG_SOURCES = $(addprefix $(SRC_DIR)/,$(PROJECT_SOURCES)) $(CURDIR)/tb.v
TOPLEVEL = tb
COCOTB_TEST_MODULES = test_inference
COMPILE_ARGS += -g2012 -I$(SRC_DIR)
PLUSARGS += +firmware=$(CURDIR)/../verification/inference/firmware.hex
include $(shell cocotb-config --makefiles)/Makefile.sim
