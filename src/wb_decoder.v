// Single-master Wishbone decoder. adr[31:28]: 0=EXT (flash/PSRAM ctrl) 1=COKANE 2=MAC 4=PERIPH.
// Any other region acks immediately and reads 0 (CPU never hangs).
module wb_decoder (
    input  wire        cyc, stb, we,
    input  wire [31:0] adr, dat_m2s,
    input  wire [3:0]  sel,
    output wire [31:0] dat_s2m,
    output wire        ack,
    output wire [31:0] s_adr, s_dat,
    output wire        s_we,
    output wire [3:0]  s_sel,
    output wire        cyc_ext, stb_ext, cyc_ck, stb_ck, cyc_mac, stb_mac, cyc_per, stb_per,
    input  wire [31:0] dat_ext, dat_ck, dat_mac, dat_per,
    input  wire        ack_ext, ack_ck, ack_mac, ack_per
);
    wire sx = (adr[31:28] == 4'h0);
    wire sc = (adr[31:28] == 4'h1);
    wire sm = (adr[31:28] == 4'h2);
    wire sp = (adr[31:28] == 4'h4);
    wire miss = ~(sx | sc | sm | sp);
    assign s_adr = adr; assign s_dat = dat_m2s; assign s_we = we; assign s_sel = sel;
    assign cyc_ext = cyc & sx;  assign stb_ext = stb & sx;
    assign cyc_ck  = cyc & sc;  assign stb_ck  = stb & sc;
    assign cyc_mac = cyc & sm;  assign stb_mac = stb & sm;
    assign cyc_per = cyc & sp;  assign stb_per = stb & sp;
    assign ack = cyc & stb & ((sx & ack_ext) | (sc & ack_ck) | (sm & ack_mac) | (sp & ack_per) | miss);
    assign dat_s2m = ({32{sx}} & dat_ext) | ({32{sc}} & dat_ck) | ({32{sm}} & dat_mac) | ({32{sp}} & dat_per);
endmodule
