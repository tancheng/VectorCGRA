

#include "xaxidma.h"
#include "xparameters.h"
#include "xil_cache.h"
#include "xil_types.h"
#include "xil_printf.h"
#include "sleep.h"
#include <stdlib.h>
#include <string.h>
#include <xaxidma_hw.h>

#define DMA_LENGTH         64       // 64 bytes
#define DMA_DEV_ID         0x0

static XAxiDma AxiDma;

u32 tx_config[][6] = {
    {0x00000000, 0x00000000, 0x00000000, 0x01500000, 0x01800000, 0x00000000},
    {0x00000000, 0x00000000, 0x00000000, 0x01700800, 0x01800000, 0x00000000},
    {0x00000000, 0x00000000, 0x00000000, 0x01901000, 0x01800000, 0x00000000},
    {0x00000000, 0x00000000, 0x00000000, 0x01B01800, 0x01800000, 0x00000000},
    {0x00000000, 0x00000000, 0x00000000, 0x01D02000, 0x01800000, 0x00000000},
    {0x00000000, 0x00000000, 0x00000000, 0x01F02800, 0x01800000, 0x00000000},
    {0x00000000, 0x00000000, 0x00000000, 0x00500000, 0x01000000, 0x00000000},
    {0x00000000, 0x00000000, 0x00000000, 0x00500000, 0x00E00000, 0x00000000},
    {0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000},
    {0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x01C00000, 0x00000000},
    {0x00000000, 0x00000000, 0x00000000, 0x00500000, 0x01000000, 0x00001000},
    {0x00000000, 0x00000000, 0x00000000, 0x00500000, 0x00E00000, 0x00001000},
    {0x00000000, 0x00000000, 0xD1000800, 0x00000188, 0x00600000, 0x00001000},
    {0x00000001, 0x00000000, 0xD1000800, 0x00000188, 0x00600000, 0x00001000},
    {0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00001000},
    {0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x01C00000, 0x00001000},
    {0x00000000, 0x00000000, 0x00000000, 0x00500000, 0x01000000, 0x00002000},
    {0x00000000, 0x00000000, 0x00000000, 0x00500000, 0x00E00000, 0x00002000},
    {0x00000000, 0x00000000, 0xD1000002, 0x000001A8, 0x00600000, 0x00002000},
    {0x00000001, 0x00000000, 0xD1000002, 0x000001A8, 0x00600000, 0x00002000},
    {0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00002000},
    {0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x01C00000, 0x00002000},
    {0x00000000, 0x00000000, 0x00000000, 0x00500000, 0x01000000, 0x00003000},
    {0x00000000, 0x00000000, 0x00000000, 0x00500000, 0x00E00000, 0x00003000},
    {0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00003000},
    {0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x01C00000, 0x00003000},
    {0x00000000, 0x00000000, 0x00000000, 0x00500000, 0x01000000, 0x00004000},
    {0x00000000, 0x00000000, 0x00000000, 0x00500000, 0x00E00000, 0x00004000},
    {0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00004000},
    {0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x01C00000, 0x00004000},
    {0x00000000, 0x00000000, 0x00000000, 0x00500000, 0x01000000, 0x00005000},
    {0x00000000, 0x00000000, 0x00000000, 0x00500000, 0x00E00000, 0x00005000},
    {0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00005000},
    {0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x01C00000, 0x00005000},
    {0x00000000, 0x00000000, 0x00000000, 0x00500000, 0x01000000, 0x00006000},
    {0x00000000, 0x00000000, 0x00000000, 0x00500000, 0x00E00000, 0x00006000},
    {0x00000000, 0x00000000, 0xD1001020, 0x00000328, 0x00600000, 0x00006000},
    {0x00000001, 0x00000000, 0xD1001020, 0x00000328, 0x00600000, 0x00006000},
    {0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00006000},
    {0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x01C00000, 0x00006000},
    {0x00000000, 0x00000000, 0x00000000, 0x00500000, 0x01000000, 0x00007000},
    {0x00000000, 0x00000000, 0x00000000, 0x00500000, 0x00E00000, 0x00007000},
    {0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00007000},
    {0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x01C00000, 0x00007000},
    {0x00000000, 0x00000000, 0x00000000, 0x00500000, 0x01000000, 0x00008000},
    {0x00000000, 0x00000000, 0x00000000, 0x00500000, 0x00E00000, 0x00008000},
    {0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00008000},
    {0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x01C00000, 0x00008000},
    {0x00000000, 0x00000000, 0x00000000, 0x00500000, 0x01000000, 0x00009000},
    {0x00000000, 0x00000000, 0x00000000, 0x00500000, 0x00E00000, 0x00009000},
    {0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00009000},
    {0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x01C00000, 0x00009000},
    {0x00000000, 0x00000000, 0x00000000, 0x00500000, 0x01000000, 0x0000A000},
    {0x00000000, 0x00000000, 0x00000000, 0x00500000, 0x00E00000, 0x0000A000},
    {0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x0000A000},
    {0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x01C00000, 0x0000A000},
    {0x00000000, 0x00000000, 0x00000000, 0x00500000, 0x01000000, 0x0000B000},
    {0x00000000, 0x00000000, 0x00000000, 0x00500000, 0x00E00000, 0x0000B000},
    {0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x0000B000},
    {0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x01C00000, 0x0000B000},
    {0x00000000, 0x00000000, 0x00000000, 0x00500000, 0x01000000, 0x0000C000},
    {0x00000000, 0x00000000, 0x00000000, 0x00500000, 0x00E00000, 0x0000C000},
    {0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x0000C000},
    {0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x01C00000, 0x0000C000},
    {0x00000000, 0x00000000, 0x00000000, 0x00500000, 0x01000000, 0x0000D000},
    {0x00000000, 0x00000000, 0x00000000, 0x00500000, 0x00E00000, 0x0000D000},
    {0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x0000D000},
    {0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x01C00000, 0x0000D000},
    {0x00000000, 0x00000000, 0x00000000, 0x00500000, 0x01000000, 0x0000E000},
    {0x00000000, 0x00000000, 0x00000000, 0x00500000, 0x00E00000, 0x0000E000},
    {0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x0000E000},
    {0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x01C00000, 0x0000E000},
    {0x00000000, 0x00000000, 0x00000000, 0x00500000, 0x01000000, 0x0000F000},
    {0x00000000, 0x00000000, 0x00000000, 0x00500000, 0x00E00000, 0x0000F000},
    {0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x0000F000},
    {0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x01C00000, 0x0000F000},
    {0x00000000, 0x00000000, 0x00000000, 0x00008000, 0x01400000, 0x00000000}
};

u32 rx_config[][6] = {
    {0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x01C00000, 0x00200000},
    {0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x01C00000, 0x00201000},
    {0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x01C00000, 0x00202000},
    {0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x01C00000, 0x00203000},
    {0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x01C00000, 0x00204000},
    {0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x01C00000, 0x00205000},
    {0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x01C00000, 0x00206000},
    {0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x01C00000, 0x00207000},
    {0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x01C00000, 0x00208000},
    {0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x01C00000, 0x00209000},
    {0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x01C00000, 0x0020A000},
    {0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x01C00000, 0x0020B000},
    {0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x01C00000, 0x0020C000},
    {0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x01C00000, 0x0020D000},
    {0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x01C00000, 0x0020E000},
    {0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x01C00000, 0x0020F000},
    {0x00000000, 0x00000000, 0x00000000, 0x00008000, 0x01600000, 0x00010000}
};


/*
0010
0110
1010
1110
*/
int main()
{
    // Transfer Sizes
    int num_tx_rows = sizeof(tx_config) / sizeof(tx_config[0]);
    int num_rx_rows = sizeof(rx_config) / sizeof(rx_config[0]);
    int num_cols = 6;
    int TX_TRANSFER_SIZE = num_tx_rows * num_cols;
    int RX_TRANSFER_SIZE = num_rx_rows * num_cols;
    int dtype_size = sizeof(u32);

    // Globals
    int Status;
    u32 *TxBuffer, *RxBuffer;

    // Polling Timeout
    int timeout = 10000000U;
    
    xil_printf("\r\n--- AXI DMA Simple Mode Test ---\r\n");
    
    // Initialize DMA
    XAxiDma_Config *CfgPtr = XAxiDma_LookupConfig(DMA_DEV_ID);
    if (!CfgPtr) {
        xil_printf("No config found for DMA\r\n");
        return XST_FAILURE;
    }
    
    xil_printf("=== Detailed DMA Configuration Check ===\r\n");
    
    // Print detailed configuration info
    xil_printf("DMA Device ID: %d\r\n", DMA_DEV_ID);
    xil_printf("DMA Base Address: 0x%08X\r\n", CfgPtr->BaseAddr);
    xil_printf("DMA Has SG: %s\r\n", CfgPtr->HasStsCntrlStrm ? "YES" : "NO");
    xil_printf("MM2S Data Width: %d\r\n", CfgPtr->Mm2SDataWidth);
    xil_printf("S2MM Data Width: %d\r\n\n", CfgPtr->S2MmDataWidth);
    
    Status = XAxiDma_CfgInitialize(&AxiDma, CfgPtr);
    if (Status != XST_SUCCESS) {
        xil_printf("DMA Init Failed\r\n");
        return XST_FAILURE;
    }
    
    if (XAxiDma_HasSg(&AxiDma)) {
        xil_printf("DMA not in simple mode\r\n");
        return XST_FAILURE;
    }
   
    Status = XAxiDma_Selftest(&AxiDma);
    if (Status != XST_SUCCESS) {
        xil_printf("DMA Self Test Failed\r\n");
        return XST_FAILURE;
    }   
    xil_printf("DMA Self Test Passed\r\n");
    
    // DMA initialized successfully in simple mode
    xil_printf("DMA configured for simple transfers\r\n");
    
    // Use proper DDR addresses (typically starting at 0x00000000)
    #define TX_DDR_ADDR  0x01000000  // offset in DDR
    #define RX_DDR_ADDR  0x02000000  // offset in DDR
    
    TxBuffer = (u32 *)TX_DDR_ADDR;
    RxBuffer = (u32 *)RX_DDR_ADDR;

    // Reset Before running
    // Xil_Out32(RESET_BASEADDR, 0x0);  // Assert reset
    // usleep(100);
    // Xil_Out32(RESET_BASEADDR, 0x1);  // Deassert reset

    XAxiDma_IntrDisable(&AxiDma, XAXIDMA_IRQ_ALL_MASK, XAXIDMA_DEVICE_TO_DMA);
    XAxiDma_IntrDisable(&AxiDma, XAXIDMA_IRQ_ALL_MASK, XAXIDMA_DMA_TO_DEVICE);

    // XAxiDma_IntrAckIrq(&AxiDma, XAXIDMA_IRQ_ALL_MASK, XAXIDMA_DEVICE_TO_DMA);
    // XAxiDma_IntrAckIrq(&AxiDma, XAXIDMA_IRQ_ALL_MASK, XAXIDMA_DMA_TO_DEVICE);
    
    xil_printf("=== TESTING with minimal transfer ===\r\n");
    xil_printf("TxBuffer: 0x%08X, RxBuffer: 0x%08X\r\n", TX_DDR_ADDR, RX_DDR_ADDR);
    
    // Initialize minimal data
    xil_printf("TX Rows: %d, TX Cols: %d\r\n", num_tx_rows, num_cols);
    for (int i = 0; i < num_tx_rows; i++) {
        for (int j = 0; j < num_cols; j++) {
            TxBuffer[i * num_cols + j] = tx_config[i][num_cols - j - 1];
        }
    }

    // Initial TX data
    xil_printf("Initial TX Buffer contents: \r\n");
    for (int i = 0; i < TX_TRANSFER_SIZE; i++) {
        if (i > 0 && i % 6 == 0)
            xil_printf("\n");
        xil_printf("%08X ", TxBuffer[i]);
    }
    xil_printf("\r\n");

    // Reset RX
    for (int i = 0; i < RX_TRANSFER_SIZE; i++) {
        RxBuffer[i] = 0;
    }
    // Initial RX data
    xil_printf("Initial RX Buffer contents: \r\n");
    for (int i = 0; i < RX_TRANSFER_SIZE; i++) {
        if (i > 0 && i % 6 == 0)
            xil_printf("\n");
        xil_printf("%08X ", RxBuffer[i]);
    }
    xil_printf("\r\n");
    
    // Flush caches - use TRANSFER_SIZE
    Xil_DCacheFlushRange((UINTPTR)TxBuffer, TX_TRANSFER_SIZE * dtype_size);
    Xil_DCacheFlushRange((UINTPTR)RxBuffer, RX_TRANSFER_SIZE * dtype_size);
    
    // Start RX first - SAME SIZE
    Status = XAxiDma_SimpleTransfer(&AxiDma, (UINTPTR)RxBuffer,
                                     RX_TRANSFER_SIZE*dtype_size, XAXIDMA_DEVICE_TO_DMA);
    if (Status != XST_SUCCESS) {
        xil_printf("RX transfer setup failed\r\n");
        goto cleanup;
    }
    xil_printf("RX transfer started\r\n");
    
    // Then TX - SAME SIZE
    Status = XAxiDma_SimpleTransfer(&AxiDma, (UINTPTR)TxBuffer,
                                     TX_TRANSFER_SIZE*dtype_size, XAXIDMA_DMA_TO_DEVICE);
    if (Status != XST_SUCCESS) {
        xil_printf("TX transfer setup failed\r\n");
        goto cleanup;
    }
    xil_printf("TX transfer started\r\n");
    
    // Polling with timeout
    xil_printf("\nStart Polling...\r\n");
    
    // Wait for S2MM first
    while (timeout) {
        if (!(XAxiDma_Busy(&AxiDma, XAXIDMA_DEVICE_TO_DMA)) &&
            !(XAxiDma_Busy(&AxiDma, XAXIDMA_DMA_TO_DEVICE))) {
            break;
        }
        timeout--;
        usleep(1U);
    }

    if (timeout <= 0) {
        xil_printf("[FAILED] DMA Timeout\n");
        for (int i = 0; i < RX_TRANSFER_SIZE; i++) {
            if (i > 0 && i % 6 == 0)
                xil_printf("\n");
            xil_printf("%08X ", RxBuffer[i]);
        }
        goto cleanup;
    }
    
    // Invalidate RX buffer - use TRANSFER_SIZE
    Xil_DCacheInvalidateRange((UINTPTR)RxBuffer, RX_TRANSFER_SIZE*dtype_size);
    
    // Compare result - use TRANSFER_SIZE
    xil_printf("Verifying transfer...\r\n");
    xil_printf("RX Buffer contents: \r\n");
    for (int i = 0; i < RX_TRANSFER_SIZE; i++) {
        if (i > 0 && i % 6 == 0)
            xil_printf("\n");
        xil_printf("%08X ", RxBuffer[i]);
    }
    xil_printf("\r\n");

    // Validate Calculated Values
    for (int i = 0; i < num_rx_rows; i++) {
        for (int j = 0; j < num_cols; j++) {
            u32 rx_calc_val = RxBuffer[i * num_cols + j];
            u32 rx_config_val = rx_config[i][num_cols - j - 1];
            if (rx_calc_val != rx_config_val) {
                xil_printf("Mismatch at %d: Calc=%08X, Expected=%08X\r\n",
                            i * num_cols + j, rx_calc_val, rx_config_val);
                goto cleanup;
            }
        }
    }
    xil_printf("DMA Transfer PASSED\r\n");
    
cleanup:
    // Don't free - we're using fixed addresses
    free(TxBuffer);
    free(RxBuffer);
    xil_printf("\nDMA Cleaning Up\r\n");
    return 0;
}