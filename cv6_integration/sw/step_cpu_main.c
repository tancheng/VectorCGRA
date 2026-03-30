#include <stdint.h>
#include "step_packets.h"

#define STEP_BASE        0x40000000u
#define STEP_STATUS      (*(volatile uint32_t *)(STEP_BASE + 0x0004u))
#define STEP_DMA_SRC     (*(volatile uint32_t *)(STEP_BASE + 0x0020u))
#define STEP_DMA_LEN     (*(volatile uint32_t *)(STEP_BASE + 0x0028u))
#define STEP_DMA_CMD     (*(volatile uint32_t *)(STEP_BASE + 0x002Cu))
#define STEP_EXIT        (*(volatile uint32_t *)(STEP_BASE + 0x0030u))

#define STEP_STATUS_DONE_MASK 0x1u
#define STEP_STATUS_BUSY_MASK 0x8u

#define STEP_DMA_CMD_META 0x1u
#define STEP_DMA_CMD_BIT  0x2u

static void wait_dma_idle(void) {
  while (STEP_STATUS & STEP_STATUS_BUSY_MASK) {
  }
}

static void do_dma(const uint32_t *src, uint32_t len, uint32_t cmd) {
  STEP_DMA_SRC = (uint32_t)(uintptr_t)src;
  STEP_DMA_LEN = len;
  STEP_DMA_CMD = cmd;
  wait_dma_idle();
}

int main(void) {
  for (uint32_t i = 0; i < STEP_CMD_COUNT; ++i) {
    const step_host_cmd_t cmd = step_host_cmds[i];
    if (cmd.type == STEP_HOST_CMD_META) {
      do_dma(step_meta_packets[cmd.index], STEP_META_WORDS, STEP_DMA_CMD_META);
    } else if (cmd.type == STEP_HOST_CMD_BIT) {
      do_dma(step_bit_packets[cmd.index], STEP_BIT_WORDS, STEP_DMA_CMD_BIT);
    }
  }

  while ((STEP_STATUS & STEP_STATUS_DONE_MASK) == 0u) {
  }

  STEP_EXIT = 1u;
  for (;;) {
  }
}
