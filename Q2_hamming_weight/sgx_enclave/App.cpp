/* App.cpp -- in-enclave operand Hamming-weight energy sweep (paper S V-B).
 *
 * For each of the 5 paper Hamming weights (0,16,32,48,64), measured SEQUENTIALLY
 * in increasing order, REPEAT times each: read the PP0 energy MSR (0x639) before
 * and after an ECALL that runs a MOV-load loop inside the enclave, and record the
 * energy delta (scaled by the RAPL energy unit from MSR 0x606) -- exactly the
 * in-enclave PP0 measurement the paper describes.
 *
 * Run as root (MSR read needs /dev/cpu/N/msr):
 *     sudo ./app [REPEAT] [ITERS]     defaults: REPEAT=100 ITERS=15000000000
 * CSV (hamming,rep,run_order,energy_uJ) is written to stdout.
 */
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <fcntl.h>
#include <unistd.h>
#include "sgx_urts.h"
#include "Enclave_u.h"

#define ENCLAVE_FILE "enclave.signed.so"
#define MSR_RAPL_POWER_UNIT   0x606
#define MSR_PP0_ENERGY_STATUS 0x639
#define CPU 0

static uint64_t read_msr(uint32_t reg) {
    char path[64];
    snprintf(path, sizeof(path), "/dev/cpu/%d/msr", CPU);
    int fd = open(path, O_RDONLY);
    if (fd < 0) { perror("open /dev/cpu/N/msr (need root + modprobe msr)"); exit(1); }
    uint64_t data = 0;
    if (pread(fd, &data, sizeof(data), reg) != sizeof(data)) { perror("pread msr"); exit(1); }
    close(fd);
    return data;
}

int main(int argc, char **argv) {
    unsigned repeat = (argc > 1) ? (unsigned)strtoul(argv[1], NULL, 10) : 100;
    uint64_t iters  = (argc > 2) ? strtoull(argv[2], NULL, 10) : 5000000000ULL;

    const uint64_t ops[5] = {
        0x0000000000000000ULL,  /* HW 0  */
        0x000000000000FFFFULL,  /* HW 16 */
        0x00000000FFFFFFFFULL,  /* HW 32 */
        0x0000FFFFFFFFFFFFULL,  /* HW 48 */
        0xFFFFFFFFFFFFFFFFULL,  /* HW 64 */
    };
    const int hw[5] = {0,16,32,48,64};

    sgx_enclave_id_t eid = 0;
    sgx_launch_token_t token = {0};
    int updated = 0;
    sgx_status_t st = sgx_create_enclave(ENCLAVE_FILE, SGX_DEBUG_FLAG, &token, &updated, &eid, NULL);
    if (st != SGX_SUCCESS) { fprintf(stderr, "sgx_create_enclave failed: 0x%x\n", st); return 1; }

    unsigned ei = (unsigned)((read_msr(MSR_RAPL_POWER_UNIT) >> 8) & 0x1F);
    double unit = 1.0 / (double)(1ULL << ei);     /* energy unit in joules/tick */
    fprintf(stderr, "# in-enclave PP0 MOV HW sweep; repeat=%u iters=%llu energy_unit=%.3e J/tick\n",
            repeat, (unsigned long long)iters, unit);

    /* Round-robin ("5 goes"): each round cycles through all 5 HW levels once,
     * so the `repeat` measurements of each HW are spread across the whole run
     * (interleaved), averaging out per-HW thermal drift -- unlike blocked
     * sequential collection where run-order == HW-order. */
    printf("hamming,round,run_order,energy_uJ\n");
    int order = 0;
    for (unsigned r = 1; r <= repeat; r++) {
        for (int k = 0; k < 5; k++) {
            uint64_t e1 = read_msr(MSR_PP0_ENERGY_STATUS) & 0xFFFFFFFFULL;
            ecall_mov_loop(eid, iters, ops[k]);
            uint64_t e2 = read_msr(MSR_PP0_ENERGY_STATUS) & 0xFFFFFFFFULL;
            uint64_t d = (e2 >= e1) ? (e2 - e1) : (e2 + 0x100000000ULL - e1);  /* 32-bit wrap */
            double uj = (double)d * unit * 1e6;
            printf("%d,%u,%d,%.0f\n", hw[k], r, order, uj);
            fflush(stdout);
            order++;
        }
        fprintf(stderr, "  round %u/%u done\n", r, repeat);
    }

    sgx_destroy_enclave(eid);
    return 0;
}
