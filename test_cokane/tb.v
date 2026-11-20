`timescale 1ns/1ps
module tb;
 reg clk=0, rst=1, cyc=0, stb=0, we=0;
 reg [31:0] adr=0, dat_i=0;
 reg [3:0] sel=0;
 wire [31:0] dat_o;
 wire ack;
 cokane_wb dut(.*);
endmodule
