`include "dice_define.vh"

module scoreboard_tid_entry
    import dice_pkg::*, 
           dice_frontend_pkg::*;
(
    input logic clk,
    input logic rst_n,
    input logic [REG_NUM-1:0] update_data, // Data to be stored in the entry
    input logic [REG_NUM-1:0] update_mask, // Mask, 1 means update, 0 means keep current value

    // Outputs
    output logic [REG_NUM-1:0] scoreboard_data // Output data from the entry
);

    // Internal storage for the scoreboard entry
    logic [REG_NUM-1:0] entry_data;

    // Update logic
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            entry_data <= '0; // Reset the entry data
        end else begin
            // Apply the update mask to the entry data
            // Mask, 1 means update, 0 means keep current value
            for (int i = 0; i < REG_NUM; i++) begin
                if (update_mask[i]) begin
                    entry_data[i] <= update_data[i]; // Update the bit if mask is set
                end
            end
        end
    end

    // Output the current state of the scoreboard entry
    assign scoreboard_data = entry_data;

endmodule

// want to dispatch thread to check for collision in the scoreboard. 
// scoreboard takes in inputbitmap to get information on the thread and scoreboard holds many bitmaps corresponding to tids for each register
// when tids come in, we read back the bit map and do a bit wise AND to check to see if to see if there is something there. 
// if the collision map does bit-wise OR cannot dispatch the tid and generate a collision.
// if there is no collision, need to reserve the ld dest register. thus ld dest register goes into the scoreboard
// whenever we dispatch tid will update the bitmap to have more 1s and the tid will become 1
// ld dest reg needs fixed logic to update bitmap
// have two write attempts to the bit map. 

module scoreboard
    import dice_pkg::*, 
           dice_frontend_pkg::*;
#(
    parameter int THREADS_PER_SCOREBOARD = 256,
    parameter int SCOREBOARD_TID_WIDTH = $clog2(THREADS_PER_SCOREBOARD)
)(
    input logic clk,
    input logic rst_n,
    
    // Input signals
    input logic [REG_NUM-1:0] input_regs_map,    // Bitmap of current inputs to CGRA
    input logic [SCOREBOARD_TID_WIDTH-1:0]  rd_tid,            // TID to be checked for collision
    input logic rd_valid,                 // Valid signal for read operation
    input logic [SCOREBOARD_TID_WIDTH-1:0]  rsv_tid,           // TID to reserve registers
    input logic rsv_valid,                // Valid signal for reserve operation
    input logic [THREADS_PER_SCOREBOARD-1:0] wb_tid_bitmap,    // Bitmap of TIDs to release registers
    input logic [REG_NUM-1:0]  ld_dest_regs_bitmap,       // Bitmap of registers to be released (0-31: GPR, 32: CR, 33: PR)
    input logic wb_valid,                 // Valid signal for write-back operation
    input logic clear_scoreboard,           // Signal to clear the entire scoreboard (e.g., on new CTA dispatch)
    
    // Output signals
    output logic collision                 // Collision detection result
);

    
    // Internal signals
    logic [REG_NUM-1:0] scoreboard_data [THREADS_PER_SCOREBOARD];   // Data output from each TID entry
    logic [REG_NUM-1:0] update_data [THREADS_PER_SCOREBOARD];       // Update data for each TID entry
    logic [REG_NUM-1:0] update_mask [THREADS_PER_SCOREBOARD];       // Update mask for each TID entry
    logic [REG_NUM-1:0] rd_scoreboard_data;      // Scoreboard data for read TID
    logic [REG_NUM-1:0] collision_check;         // Result of bitwise AND for collision check
    logic        rd_tid_conflict;         // Flag for special case conflict
    
    // Generate scoreboard entries for all TIDs
    genvar i;
    generate
        for (i = 0; i < THREADS_PER_SCOREBOARD; i++) begin : gen_scoreboard_entries
            scoreboard_tid_entry tid_entry (
                .clk(clk),
                .rst_n(rst_n),
                .update_data(update_data[i]),
                .update_mask(update_mask[i]),
                .scoreboard_data(scoreboard_data[i])
            );
        end
    endgenerate
    
    // Logic to determine update data and mask for each TID
    always_comb begin
        // Initialize all entries to no update
        for (int j = 0; j < THREADS_PER_SCOREBOARD; j++) begin
            update_data[j] = '0;
            update_mask[j] = '0;
        end
        
        // Handle reservation (rsv_tid) only when rsv_valid is asserted
        if (rsv_valid) begin
            update_data[rsv_tid] = input_regs_map;
            update_mask[rsv_tid] = input_regs_map;
        end
        
        // Handle write-back releases only when wb_valid is asserted
        if (wb_valid) begin
            for (int j = 0; j < THREADS_PER_SCOREBOARD; j++) begin
                if (wb_tid_bitmap[j]) begin
                    // Release the specific register (set to 0)
                    update_data[j] = update_data[j] & ~ld_dest_regs_bitmap;
                    update_mask[j] = update_mask[j] |  ld_dest_regs_bitmap;
                end
            end
        end
        
        // Handle fusion case: if rsv_tid overlaps with wb_tid_bitmap
        if (rsv_valid && wb_valid && wb_tid_bitmap[rsv_tid]) begin
            // Fuse the operations
            update_data[rsv_tid] = input_regs_map;
            update_mask[rsv_tid] = input_regs_map | ld_dest_regs_bitmap;
            // The register being released will be overwritten to 0 by the reservation data
        end

        // Clear takes highest priority
        if (clear_scoreboard) begin
            for (int j = 0; j < THREADS_PER_SCOREBOARD; j++) begin
                update_data[j] = '0;
                update_mask[j] = '1;  // update all bits to 0
            end
        end
    end
    
    // Read scoreboard data for collision check
    assign rd_scoreboard_data = scoreboard_data[rd_tid];
    
    // Collision detection logic
    always_comb begin
        if (rd_valid) begin
            // Bitwise AND between scoreboard data and input register map
            collision_check = rd_scoreboard_data & input_regs_map;
            
            // Check for special case: wb_tid_bitmap (only when wb_valid)
            rd_tid_conflict = wb_valid && wb_tid_bitmap[rd_tid];
            
            // Set collision if there's any dependency or special case conflict
            collision = (|collision_check) || rd_tid_conflict;
        end else begin
            // No collision when read is not valid
            collision = 1'b0;
        end
    end

endmodule