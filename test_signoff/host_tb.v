`timescale 1ns/1ps
// Simulation-only host speaking the *public pins* of the unchanged chip.
module tb;
 reg clk=0,rst_n=0,ena=1;
 reg [7:0] ui_in=32,uio_in=0;
 wire [7:0] uo_out,uio_out,uio_oe;
`ifdef GL_TEST
 wire VPWR=1'b1,VGND=1'b0;
`endif
 tt_um_cokane_soc user_project(
`ifdef GL_TEST
  .VPWR(VPWR),.VGND(VGND),
`endif
  .clk(clk),.rst_n(rst_n),.ena(ena),.ui_in(ui_in),.uio_in(uio_in),
  .uo_out(uo_out),.uio_out(uio_out),.uio_oe(uio_oe));
 always #25 clk=~clk;
 initial begin repeat(8) @(negedge clk); rst_n=1; end
 reg [31:0] mem [0:65535];
 reg [1023:0] image_file;
 integer j,lane=0,state=0;
 reg [31:0] address=0,word_data=0;
 reg writing=0;
 reg [3:0] byte_sel=0;
 reg finished=0,fault=0;
 reg [63:0] cycles=0,reads=0,writes=0;
 initial begin
  for(j=0;j<65536;j=j+1) mem[j]=0;
  if(!$value$plusargs("firmware=%s",image_file)) $fatal(1,"Missing firmware");
  $readmemh(image_file,mem);
 end
 always @(posedge clk) if(rst_n && !finished) cycles<=cycles+1;
 // Inputs change on falling edges, data is captured by the chip on rising edges.
 always @(negedge clk) begin
  if(!rst_n) begin ui_in=32;uio_in=0;state=0;lane=0; end
  else begin
   if(uio_oe!==8'b0 || uio_out!==8'b0) begin fault=1;finished=1; end
   case(state)
    0: begin
     if(uo_out[7]) begin fault=1;finished=1; end
     if(uo_out[6:5]==2'b11) begin
      writing=uo_out[4];byte_sel=uo_out[3:0];address=0;
      lane=0;ui_in=0;state=1;
     end
    end
    1: begin
     address[8*lane+:8]=uo_out;
     if(lane==3) begin
      if(address>=32'h40000) begin fault=1;finished=1; end
      lane=0;
      if(writing) begin word_data=0;ui_in=16;state=2; end
      else begin
       word_data=mem[address[17:2]];uio_in=word_data[7:0];ui_in=4;state=3;
       if(!finished) reads=reads+1;
      end
     end else begin lane=lane+1;ui_in=lane; end
    end
    2: begin
     word_data[8*lane+:8]=uo_out;
     if(lane==3) begin
      for(j=0;j<4;j=j+1) if(byte_sel[j]) mem[address[17:2]][8*j+:8]=word_data[8*j+:8];
      if(!finished) writes=writes+1;
      if(address==32'h30004 && byte_sel==15 && word_data==4) finished=1;
      if(address==32'h30000 && byte_sel==15 && word_data==32'hbad00bad) begin fault=1;finished=1; end
      ui_in=8;state=4;
     end else begin lane=lane+1;ui_in=16|lane; end
    end
    3: begin
     // The preceding rising edge captured this lane. Ack only after lane 3.
     if(lane==3) begin ui_in=8;state=4; end
     else begin lane=lane+1;uio_in=word_data[8*lane+:8];ui_in=4|lane; end
    end
    4: begin ui_in=32;state=5; end
    5: begin ui_in=32;state=0; end
    default: begin fault=1;finished=1;ui_in=32;state=0; end
   endcase
  end
 end
endmodule
