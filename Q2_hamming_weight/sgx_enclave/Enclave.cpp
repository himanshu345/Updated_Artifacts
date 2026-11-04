#include "Enclave_t.h"
#include <stdint.h>

/* One MOV-load of `src` per iteration, identical to the userspace bench_mov
 * primitive but executed inside the SGX enclave (paper S V-B methodology). */
void ecall_mov_loop(uint64_t iters, uint64_t operand)
{
    static volatile uint64_t src;
    src = operand;
    for (uint64_t i = 0; i < iters; i++) {
        asm volatile ("movq (%0), %%rax\n"
                      :
                      : "r"(&src)
                      : "rax");
    }
}
