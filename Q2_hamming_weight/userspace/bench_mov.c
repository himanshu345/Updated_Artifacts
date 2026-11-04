/* bench_mov.c – saturate one core with a single “mov” load instruction
 *
 * Build : gcc -O2 -march=native -o bench_mov bench_mov.c
 * Usage : ./bench_mov <iterations> <64-bit_value_hex>
 * Example (low HW): ./bench_mov 100000000 0x0000000000000000
 * Example (high HW): ./bench_mov 100000000 0xffffffffffffffff
 *
 * The program
 *   1. pins itself to CPU 0,
 *   2. repeatedly executes “movq (%src), %rax” exactly <iterations> times.
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <unistd.h>
#include <sched.h>
#include <inttypes.h>

int main(int argc, char **argv)
{
    if (argc != 3) {
        fprintf(stderr, "Usage: %s <iterations> <64-bit_value_hex>\n", argv[0]);
        return 1;
    }

    /* parse command-line arguments */
    uint64_t iters = strtoull(argv[1], NULL, 10);
    uint64_t val;
    if (sscanf(argv[2], "%" SCNx64, &val) != 1) {
        fprintf(stderr, "Cannot parse hex value \"%s\"\n", argv[2]);
        return 1;
    }

    /* 64-bit operand whose Hamming weight we control */
    static volatile uint64_t src;
    src = val;

    /* pin to core 0 to reduce scheduler noise */
    cpu_set_t set;
    CPU_ZERO(&set);
    CPU_SET(0, &set);
    sched_setaffinity(0, sizeof(set), &set);

    /* tight loop with exactly one load */
    for (uint64_t i = 0; i < iters; i++) {
        asm volatile ("movq (%0), %%rax\n"
                      :
                      : "r"(&src)
                      : "rax");
    }
    return 0;
}
