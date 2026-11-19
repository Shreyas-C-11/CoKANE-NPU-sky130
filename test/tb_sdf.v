`timescale 1ns/1ps
module tb_sdf;
 reg clk=0, rst_n=0, ena=1;
 reg [7:0] ui_in=0,uio_in=0;
 wire [7:0] uo_out,uio_out,uio_oe;
 supply1 VPWR; supply0 VGND;
 reg [31:0] memory[0:4095];
 reg [31:0] address,value,old_word;
 reg [7:0] status;
 integer boot,iteration,lane,j,transactions;
 real half_period=25.0;
 real settle=15.0;
 reg [4095:0] program_path;
 tt_um_cokane_soc user_project(.clk(clk),.rst_n(rst_n),.ena(ena),.ui_in(ui_in),.uo_out(uo_out),.uio_in(uio_in),.uio_out(uio_out),.uio_oe(uio_oe),.VPWR(VPWR),.VGND(VGND));
 task fail;
  input [511:0] message;
  begin $display("SDF_FIRMWARE_FAIL %0s time=%0t",message,$time); $finish; end
 endtask
 task tick;
  input [7:0] control,data;
  begin clk=0;ui_in=control;uio_in=data;#(half_period);clk=1;#(half_period);
   if(uio_oe!==0) fail("Host pins driven");
  end
 endtask
 task peek;
  input [7:0] control;
  output [7:0] response;
  begin clk=0;ui_in=control;#(settle);response=uo_out;end
 endtask
 task read_word;
  input write_data;
  output [31:0] word;
  integer b;
  reg [7:0] response;
  begin word=0;
   for(b=0;b<4;b=b+1)begin peek(b|(write_data?16:0),response);word=word|({24'b0,response}<<(8*b));end
  end
 endtask
 initial begin
  if(!$value$plusargs("PROGRAM=%s",program_path))fail("Missing PROGRAM");
  if($test$plusargs("FAST"))begin half_period=0.1;settle=0.1;end
  for(j=0;j<4096;j=j+1)memory[j]=0;
  $readmemh(program_path,memory);
  #10;
  for(boot=0;boot<2;boot=boot+1)begin: boot_run
   rst_n=(boot==1);ena=(boot==0);
   for(j=0;j<5;j=j+1)tick(0,0);
   rst_n=1;ena=1;transactions=0;
   for(iteration=0;iteration<150000;iteration=iteration+1)begin
    peek(32,status);
    if((^status)===1'bx)fail("Unknown status");
    if(status[7])fail("CPU trap");
    if((status&8'h60)==8'h60)begin
     read_word(0,address);
     if(address[31:14]!=0)fail("Unexpected host address");
     for(j=0;j<(transactions%4);j=j+1)tick(0,0);
     if(status[4])begin
      read_word(1,value);old_word=memory[address>>2];
      for(lane=0;lane<4;lane=lane+1)if(status[lane])old_word=(old_word&~(32'hff<<(8*lane)))|(value&(32'hff<<(8*lane)));
      memory[address>>2]=old_word;
     end else begin
      value=memory[address>>2];
      for(lane=0;lane<4;lane=lane+1)tick(4|lane,(value>>(8*lane))&255);
     end
     tick(8,0);tick(0,0);transactions=transactions+1;
     if(status[4]&&address==32'h1000)begin
      if(memory[1024]!==32'h600d600d)fail("Bad firmware signature");
      if(memory[1025]!==32'h1234ab78)fail("Bad memory byte-write result");
      $display("SDF_BOOT_PASS boot=%0d transactions=%0d",boot,transactions);
      disable boot_run;
     end
    end else tick(0,0);
   end
   fail("Firmware timeout");
  end
  $display("SDF_FIRMWARE_PASS");$finish;
 end
 initial begin #100000000;fail("Global timeout");end
endmodule
