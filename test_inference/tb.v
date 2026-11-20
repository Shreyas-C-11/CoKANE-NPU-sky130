`timescale 1ns/1ps
// Simulation-only external RAM. It replaces the *host*, not the CPU/NPU RTL.
module tb;
 reg clk=0, rst_n=0;
 always #25 clk=~clk;
 initial begin repeat(8) @(negedge clk); rst_n=1; end
 wire trap, s_we, cyc_ext, stb_ext, cyc_ck, stb_ck, cyc_per, stb_per;
 wire [31:0] s_adr, s_dat, dat_ck;
 wire [3:0] s_sel;
 wire ack_ck;
 reg ack_ext=0;
 reg [31:0] mem [0:65535];
 reg [31:0] mem_addr=0, mem_data=0, lfsr=32'h21738213;
 reg [3:0] mem_sel=0;
 reg mem_we=0, pending=0;
 reg [2:0] delay_count=0;
 reg [63:0] cycles=0, external_reads=0, external_writes=0, wait_cycles=0;
 reg [63:0] npu_reads=0,npu_writes=0;
 reg [63:0] hardware_phase_cycles=0, cpu_reference_cycles=0;
 reg finished=0, fault=0;
 reg [31:0] completion=0;
 reg [1023:0] image_file;
 integer i;
 initial begin
  for (i=0;i<65536;i=i+1) mem[i]=0;
  if (!$value$plusargs("firmware=%s",image_file)) $fatal(1,"Missing firmware image");
  $readmemh(image_file,mem);
 end
 soc_core #(.COMPRESSED(0)) u_soc (
  .clk(clk),.rst_n(rst_n),.trap(trap),.s_adr(s_adr),.s_dat(s_dat),.s_we(s_we),.s_sel(s_sel),
  .cyc_ext(cyc_ext),.stb_ext(stb_ext),.cyc_ck(cyc_ck),.stb_ck(stb_ck),.cyc_per(cyc_per),.stb_per(stb_per),
  .dat_ext(mem[mem_addr[17:2]]),.dat_ck(dat_ck),.dat_per(32'b0),
  .ack_ext(ack_ext),.ack_ck(ack_ck),.ack_per(cyc_per&stb_per));
 cokane_wb u_cokane (.clk(clk),.rst(~rst_n),.cyc(cyc_ck),.stb(stb_ck),.we(s_we),
  .adr(s_adr),.dat_i(s_dat),.sel(s_sel),.dat_o(dat_ck),.ack(ack_ck));
 always @(posedge clk) begin
  if (rst_n && !finished) begin
   cycles<=cycles+1;
   if (trap) begin fault<=1;finished<=1; end
   if (cyc_ck && stb_ck && !ack_ck) begin
    if (s_we) npu_writes<=npu_writes+1;
    else npu_reads<=npu_reads+1;
   end
   ack_ext<=0;
   lfsr<={lfsr[30:0],lfsr[31]^lfsr[21]^lfsr[1]^lfsr[0]};
   if (!pending && cyc_ext && stb_ext && !ack_ext) begin
    if (s_adr>=32'h40000) begin fault<=1;finished<=1; end
    mem_addr<=s_adr;mem_data<=s_dat;mem_sel<=s_sel;mem_we<=s_we;
    delay_count<={1'b0,lfsr[1:0]};pending<=1;
   end else if (pending) begin
    if (delay_count!=0) begin delay_count<=delay_count-1;wait_cycles<=wait_cycles+1; end
    else begin
     pending<=0;ack_ext<=1;
     if (mem_we) begin
      external_writes<=external_writes+1;
      for (i=0;i<4;i=i+1) if(mem_sel[i]) mem[mem_addr[17:2]][8*i+:8]<=mem_data[8*i+:8];
      if (mem_addr==32'h30004 && mem_sel==15 && mem_data==4) hardware_phase_cycles<=cycles+1;
      if (mem_addr==32'h30004 && mem_sel==15 && mem_data==5) cpu_reference_cycles<=cycles+1-hardware_phase_cycles;
      if (mem_addr==32'h30000 && mem_sel==15 && mem_data!=0) begin
       completion<=mem_data;finished<=1;
      end
     end else external_reads<=external_reads+1;
    end
   end
  end
 end
endmodule
