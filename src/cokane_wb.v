// CoKANE ABI 1.0: 64x6 writable LUT, eight 12-bit partial sums, one adder.
// See NPU_Specs.md. A context is limited to 64 signed six-bit contributions.
`default_nettype none
module cokane_wb (
 input wire clk, rst, cyc, stb, we,
 input wire [31:0] adr, dat_i,
 input wire [3:0] sel,
 output reg [31:0] dat_o,
 output reg ack
);
 localparam [2:0] IDLE=0, READ_LUT=1, ACCUMULATE=2, FINALIZE=3, POOL=4;
 localparam [7:0] E_BUSY=1, E_STATE=2, E_CONFIG=3, E_DATA=4,
                  E_ADDRESS=5, E_COMMAND=6, E_INPUT=7;
 reg [2:0] state;
 reg active, done, error, result_valid, pool_valid;
 reg [7:0] error_code;
 reg [3:0] batch, lane, result_count;
 reg [6:0] terms, terms_done;
 reg [2:0] input_bits;
 reg [31:0] compute_cycles, elapsed_cycles;
 reg [5:0] lut_addr;
 reg signed [5:0] lut [0:63]; // No reset: initialization is enforced by a mask.
 reg [63:0] lut_written;
 reg [5:0] inputs [0:7];
 reg [7:0] input_written;
 reg signed [11:0] psum [0:7];
 reg signed [5:0] results [0:7];
 reg signed [5:0] pooled [0:1];
 reg [1:0] pool_count;
 reg signed [5:0] lut_value;
 wire busy = state != IDLE;
 wire access = cyc && stb && !ack;
 wire aligned = adr[1:0] == 0 && adr[27:8] == 0;
 wire wr = access && we && sel[0];
 wire abort_request = wr && aligned && adr[7:0]==8'h08 && dat_i[7:0]==8'd4;
 wire [11:0] contribution = {{6{lut_value[5]}},lut_value};
 wire signed [11:0] updated_sum = psum[lane[2:0]] + $signed(contribution);
 reg inputs_ready;
 integer v, n, k;
 always @* begin
  inputs_ready = 1;
  for (n=0;n<8;n=n+1)
   if (n < batch && (!input_written[n] || !lut_written[inputs[n]])) inputs_ready=0;
 end
 reg signed [5:0] pool_max;
 always @* begin
  pool_max = 6'sb100000;
  for (k=0;k<4;k=k+1)
   if ($signed(results[{lane[0],2'b00}+k]) > pool_max)
    pool_max = results[{lane[0],2'b00}+k];
 end
 always @(posedge clk) begin
  if (rst) begin
   ack<=0; state<=IDLE; active<=0; done<=0; error<=0; error_code<=0;
   result_valid<=0; pool_valid<=0; batch<=8; lane<=0; terms<=1; terms_done<=0;
   input_bits<=6; compute_cycles<=0; elapsed_cycles<=0; lut_addr<=0;
   lut_written<=0; input_written<=0; result_count<=0; pool_count<=0; lut_value<=0;
   for (v=0;v<8;v=v+1) begin psum[v]<=0; results[v]<=0; end
   for (v=0;v<2;v=v+1) pooled[v]<=0;
  end else begin
   ack <= access;
   if (busy && compute_cycles!=32'hffffffff) compute_cycles<=compute_cycles+1;
   if (active && elapsed_cycles!=32'hffffffff) elapsed_cycles<=elapsed_cycles+1;
   case (state)
    READ_LUT: begin lut_value<=lut[inputs[lane[2:0]]]; state<=ACCUMULATE; end
    ACCUMULATE: begin
     psum[lane[2:0]]<=updated_sum;
     if (lane==batch-1) begin
      state<=IDLE; terms_done<=terms_done+1; input_written<=0;
     end else begin lane<=lane+1; state<=READ_LUT; end
    end
    FINALIZE: begin
     if (psum[lane[2:0]] > 12'sd31) results[lane[2:0]]<=6'sd31;
     else if (psum[lane[2:0]] < -12'sd32) results[lane[2:0]]<=-6'sd32;
     else results[lane[2:0]]<=psum[lane[2:0]][5:0];
     if (lane==batch-1) begin
      state<=IDLE; active<=0; result_valid<=1; result_count<=batch; done<=1;
     end else lane<=lane+1;
    end
    POOL: begin
     pooled[lane[0]]<=pool_max;
     if ((result_count==4) || lane==1) begin
      state<=IDLE; pool_valid<=1; pool_count<=result_count==4 ? 1 : 2; done<=1;
     end else lane<=1;
    end
    default: ;
   endcase
   if (wr) begin
    if (abort_request) begin
     state<=IDLE; active<=0; done<=0; error<=0; error_code<=0;
     result_valid<=0; pool_valid<=0; result_count<=0; pool_count<=0;
     terms_done<=0; input_written<=0; lane<=0; compute_cycles<=0; elapsed_cycles<=0;
     for (v=0;v<8;v=v+1) psum[v]<=0;
    end else if (busy) begin error<=1; error_code<=E_BUSY; end
    else if (!aligned) begin error<=1; error_code<=E_ADDRESS; end
    else case (adr[7:0])
     8'h08: case (dat_i[7:0])
      1: if (active || error) begin error<=1; error_code<=E_STATE; end
         else begin
          active<=1; done<=0; result_valid<=0; pool_valid<=0; result_count<=0; pool_count<=0;
          terms_done<=0; input_written<=0; compute_cycles<=0; elapsed_cycles<=0;
          for (v=0;v<8;v=v+1) psum[v]<=0;
         end
      2: if (!active || error || terms_done>=terms) begin error<=1; error_code<=E_STATE; end
         else if (!inputs_ready) begin error<=1; error_code<=E_DATA; end
         else begin lane<=0; state<=READ_LUT; end
      3: if (!active || error || terms_done!=terms) begin error<=1; error_code<=E_STATE; end
         else begin lane<=0; state<=FINALIZE; done<=0; end
      5: begin error<=0; error_code<=0; end
      6: if (error || !result_valid || (result_count!=4 && result_count!=8)) begin error<=1; error_code<=E_STATE; end
         else begin lane<=0; state<=POOL; done<=0; pool_valid<=0; pool_count<=0; end
      7: lut_written<=0;
      default: begin error<=1; error_code<=E_COMMAND; end
     endcase
     8'h0c: if (active || dat_i[7:0]<1 || dat_i[7:0]>8) begin error<=1; error_code<=E_CONFIG; end
             else batch<=dat_i[3:0];
     8'h10: if (active || dat_i[7:0]<1 || dat_i[7:0]>64) begin error<=1; error_code<=E_CONFIG; end
             else terms<=dat_i[6:0];
     8'h20: if (dat_i[7:6]!=0) begin error<=1; error_code<=E_CONFIG; end else lut_addr<=dat_i[5:0];
     8'h24: if (active || (dat_i[7:0]!=4 && dat_i[7:0]!=6)) begin error<=1; error_code<=E_CONFIG; end
             else input_bits<=dat_i[2:0];
     8'h28: begin lut[lut_addr]<=dat_i[5:0]; lut_written[lut_addr]<=1; lut_addr<=lut_addr+1'b1; end
     8'h40,8'h44,8'h48,8'h4c,8'h50,8'h54,8'h58,8'h5c:
      if (input_bits==4 && dat_i[5:4]!=0) begin error<=1; error_code<=E_INPUT; end
      else begin inputs[adr[4:2]]<=dat_i[5:0]; input_written[adr[4:2]]<=1; end
     default: begin error<=1; error_code<=E_ADDRESS; end
    endcase
   end
  end
 end
 always @* begin
  dat_o=0;
  if (aligned) case (adr[7:0])
   8'h00: dat_o=32'h434b0100;
   8'h04: dat_o={16'b0,error_code,2'b0,pool_valid,result_valid,error,done,active,busy};
   8'h0c: dat_o={28'b0,batch};
   8'h10: dat_o={25'b0,terms};
   8'h14: dat_o={25'b0,terms_done};
   8'h18: dat_o=compute_cycles;
   8'h1c: dat_o=elapsed_cycles;
   8'h20: dat_o={26'b0,lut_addr};
   8'h24: dat_o={29'b0,input_bits};
   8'h28: if (lut_written[lut_addr]) dat_o={{26{lut[lut_addr][5]}},lut[lut_addr]};
   8'h2c: dat_o={28'b0,result_count};
   8'h30: dat_o={30'b0,pool_count};
   8'h40,8'h44,8'h48,8'h4c,8'h50,8'h54,8'h58,8'h5c:
    if (input_written[adr[4:2]]) dat_o={26'b0,inputs[adr[4:2]]};
   8'h80,8'h84,8'h88,8'h8c,8'h90,8'h94,8'h98,8'h9c:
    dat_o={{20{psum[adr[4:2]][11]}},psum[adr[4:2]]};
   8'hc0,8'hc4,8'hc8,8'hcc,8'hd0,8'hd4,8'hd8,8'hdc:
    if (result_valid && {1'b0,adr[4:2]}<result_count) dat_o={{26{results[adr[4:2]][5]}},results[adr[4:2]]};
   8'he0,8'he4:
    if (pool_valid && {1'b0,adr[2]}<pool_count) dat_o={{26{pooled[adr[2]][5]}},pooled[adr[2]]};
   default: ;
  endcase
 end
 wire unused = &{1'b0,adr[31:28],dat_i[31:8],sel[3:1]};
endmodule
`default_nettype wire
