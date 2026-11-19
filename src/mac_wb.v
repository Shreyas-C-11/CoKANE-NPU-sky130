// Wishbone-classic slave wrapper around mac_hybrid. Word registers (adr[4:2]):
// 0 A (W, s8)  1 B (W, s8)  2 CTRL (W: [0]=start [1]=clear)
// 3 STATUS (R) [0]busy [1]done* [2]valid* [4:3]error* [5]corrected* [6]detected* [7]retried* [9:8]retry_count
//   (* sticky, cleared on start/clear)
// 4 ACC (R, sign-extended 24b)
// A start written while the MAC is busy is dropped by the MAC (firmware polls busy first).
module mac_wb (
    input  wire        clk, rst,
    input  wire        cyc, stb, we,
    input  wire [31:0] adr, dat_i,
    input  wire [3:0]  sel,
    output reg  [31:0] dat_o,
    output reg         ack
);
    reg [7:0] a, b;
    reg start, clr;
    wire busy, done, result_valid, ready, corrected, detected, retried;
    wire [1:0] error, retry_count;
    wire signed [23:0] acc;
    reg done_s, valid_s, corr_s, det_s, retr_s;
    reg [1:0] err_s, rc_s;

    mac_hybrid #(.OPERAND_WIDTH(8), .ACC_WIDTH(24), .MAX_RETRIES(2)) u_mac (
        .clk(clk), .rst(rst), .clear(clr), .start(start),
        .operand_a(a), .operand_b(b), .ready(ready), .busy(busy), .done(done),
        .result_valid(result_valid), .error(error), .accumulator(acc),
        .corrected(corrected), .detected(detected), .retried(retried), .retry_count(retry_count));

    wire access = cyc & stb & ~ack;
    always @(posedge clk) begin
        if (rst) begin
            a <= 0; b <= 0; start <= 0; clr <= 0; ack <= 0;
            done_s <= 0; valid_s <= 0; err_s <= 0; corr_s <= 0; det_s <= 0; retr_s <= 0; rc_s <= 0;
        end else begin
            ack <= access; start <= 0; clr <= 0;
            if (access && we && sel[0]) case (adr[4:2])
                3'd0: a <= dat_i[7:0];
                3'd1: b <= dat_i[7:0];
                3'd2: begin
                    start <= dat_i[0]; clr <= dat_i[1];
                    if (dat_i[1:0] != 0) begin
                        done_s <= 0; valid_s <= 0; err_s <= 0; corr_s <= 0; det_s <= 0; retr_s <= 0; rc_s <= 0;
                    end
                end
                default: ;
            endcase
            if (done) begin done_s <= 1; valid_s <= result_valid; err_s <= error; end
            if (corrected) corr_s <= 1;
            if (detected)  det_s  <= 1;
            if (retried)   retr_s <= 1;
            if (retried || done) rc_s <= retry_count;
        end
    end
    always @(*) case (adr[4:2])
        3'd0: dat_o = {24'b0, a};
        3'd1: dat_o = {24'b0, b};
        3'd3: dat_o = {22'b0, rc_s, retr_s, det_s, corr_s, err_s, valid_s, done_s, busy};
        3'd4: dat_o = {{8{acc[23]}}, acc};
        default: dat_o = 32'b0;
    endcase
endmodule
