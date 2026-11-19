// CPU+MAC baseline. All host inputs are synchronous to clk.
// ui[1:0]: byte lane; ui[2]: capture uio_in into memory read-data lane;
// ui[3]: acknowledge external-memory request; ui[4]: show write data (else address);
// ui[5]: show status (overrides ui[4]); ui[7:6]: reserved.
// uo status = {trap, cyc_ext, stb_ext, write_enable, byte_select[3:0]}.
`default_nettype none
module tt_um_cokane_soc (
 input wire [7:0] ui_in, output wire [7:0] uo_out,
 input wire [7:0] uio_in, output wire [7:0] uio_out, output wire [7:0] uio_oe,
 input wire ena, clk, rst_n
);
 wire active_reset_n = rst_n & ena;
 reg [31:0] read_data;
 always @(posedge clk) begin
  if (!active_reset_n) read_data <= 0;
  else if (ui_in[2]) begin
   case (ui_in[1:0])
    0: read_data[7:0] <= uio_in;
    1: read_data[15:8] <= uio_in;
    2: read_data[23:16] <= uio_in;
    3: read_data[31:24] <= uio_in;
   endcase
  end
 end
 wire trap, s_we, cyc_ext, stb_ext, cyc_ck, stb_ck, cyc_per, stb_per;
 wire [31:0] s_adr, s_dat;
 wire [3:0] s_sel;
 soc_core #(.COMPRESSED(0)) u_soc (
  .clk(clk), .rst_n(active_reset_n), .trap(trap),
  .s_adr(s_adr), .s_dat(s_dat), .s_we(s_we), .s_sel(s_sel),
  .cyc_ext(cyc_ext), .stb_ext(stb_ext), .cyc_ck(cyc_ck), .stb_ck(stb_ck),
  .cyc_per(cyc_per), .stb_per(stb_per),
  .dat_ext(read_data), .dat_ck(32'b0), .dat_per(32'b0),
  .ack_ext(ui_in[3] & stb_ext), .ack_ck(cyc_ck & stb_ck), .ack_per(cyc_per & stb_per)
 );
 wire [31:0] host_word = ui_in[4] ? s_dat : s_adr;
 assign uo_out = ui_in[5] ? {trap,cyc_ext,stb_ext,s_we,s_sel} : host_word[8*ui_in[1:0] +: 8];
 assign uio_out = 0;
 assign uio_oe = 0;
 wire unused = &{ui_in[7:6],1'b0};
endmodule
`default_nettype wire
