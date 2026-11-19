// CPU + Wishbone decoder + MAC wrapper. EXT / COKANE / PERIPH are exported as Wishbone slave ports (filled later).
module soc_core #(parameter COMPRESSED = 0) (
    input  wire clk, rst_n,
    output wire trap,
    output wire [31:0] s_adr, s_dat,
    output wire s_we,
    output wire [3:0] s_sel,
    output wire cyc_ext, stb_ext, cyc_ck, stb_ck, cyc_per, stb_per,
    input  wire [31:0] dat_ext, dat_ck, dat_per,
    input  wire ack_ext, ack_ck, ack_per
);
    wire rst = ~rst_n;
    wire [31:0] m_adr, m_dat_o, m_dat_i;
    wire m_we, m_stb, m_cyc, m_ack;
    wire [3:0] m_sel;
    wire [31:0] dat_mac;
    wire cyc_mac, stb_mac, ack_mac;

    picorv32_wb #(
        .ENABLE_COUNTERS(0), .ENABLE_COUNTERS64(0), .ENABLE_REGS_16_31(0), .ENABLE_REGS_DUALPORT(1),
        .TWO_STAGE_SHIFT(0), .BARREL_SHIFTER(0), .CATCH_MISALIGN(0), .CATCH_ILLINSN(0),
        .ENABLE_MUL(0), .ENABLE_DIV(0), .ENABLE_IRQ(0), .COMPRESSED_ISA(COMPRESSED),
        .PROGADDR_RESET(32'h0000_0000), .STACKADDR(32'h0000_0000)
    ) u_cpu (
        .trap(trap), .wb_rst_i(rst), .wb_clk_i(clk),
        .wbm_adr_o(m_adr), .wbm_dat_o(m_dat_o), .wbm_dat_i(m_dat_i), .wbm_we_o(m_we), .wbm_sel_o(m_sel),
        .wbm_stb_o(m_stb), .wbm_ack_i(m_ack), .wbm_cyc_o(m_cyc),
        .irq(32'b0), .eoi()
    );

    wb_decoder u_dec (
        .cyc(m_cyc), .stb(m_stb), .we(m_we), .adr(m_adr), .dat_m2s(m_dat_o), .sel(m_sel),
        .dat_s2m(m_dat_i), .ack(m_ack), .s_adr(s_adr), .s_dat(s_dat), .s_we(s_we), .s_sel(s_sel),
        .cyc_ext(cyc_ext), .stb_ext(stb_ext), .cyc_ck(cyc_ck), .stb_ck(stb_ck),
        .cyc_mac(cyc_mac), .stb_mac(stb_mac), .cyc_per(cyc_per), .stb_per(stb_per),
        .dat_ext(dat_ext), .dat_ck(dat_ck), .dat_mac(dat_mac), .dat_per(dat_per),
        .ack_ext(ack_ext), .ack_ck(ack_ck), .ack_mac(ack_mac), .ack_per(ack_per)
    );

    mac_wb u_macwb (
        .clk(clk), .rst(rst), .cyc(cyc_mac), .stb(stb_mac), .we(s_we), .adr(s_adr), .dat_i(s_dat),
        .sel(s_sel), .dat_o(dat_mac), .ack(ack_mac)
    );
endmodule
