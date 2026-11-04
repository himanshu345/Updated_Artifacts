/* rapl-reader.c – poll Intel RAPL energy counter as fast as possible
 *
 * Builds:   gcc -O2 -march=native -o rapl-reader rapl-reader.c -lrt
 * Usage  :  sudo ./rapl-reader 500000   # 0.5 million samples
 *
 * The program prints µJ values plus a UNIX-epoch timestamp (ns).
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <time.h>
#include <fcntl.h>
#include <unistd.h>

static inline uint64_t rdtsc(void) {
    unsigned int lo, hi;
    asm volatile ("rdtsc" : "=a"(lo), "=d"(hi));
    return ((uint64_t)hi << 32) | lo;
}

/* nanosecond timestamp via CLOCK_MONOTONIC_RAW */
static inline uint64_t nsec_now(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC_RAW, &ts);
    return ((uint64_t)ts.tv_sec * 1e9) + ts.tv_nsec;
}

int main(int argc, char **argv)
{
    if (argc != 2) {
        fprintf(stderr, "Usage: %s <samples>\n", argv[0]);
        return 1;
    }
    const uint64_t max_samples = strtoull(argv[1], NULL, 10);

    const char *rapl = "/sys/class/powercap/intel-rapl:0/energy_uj";
    int fd = open(rapl, O_RDONLY);
    if (fd < 0) { perror("open"); return 1; }

    char buf[32];
    uint64_t t0 = rdtsc();         /* for info only */
    for (uint64_t i = 0; i < max_samples; i++) {
        lseek(fd, 0, SEEK_SET);
        ssize_t n = read(fd, buf, sizeof(buf)-1);
        if (n <= 0) { perror("read"); break; }
        buf[n] = 0;
        uint64_t ts = nsec_now();
        printf("%s %lu\n", buf, ts);
    }
    uint64_t t1 = rdtsc();
    fprintf(stderr, "TSC diff = %lu\n", t1 - t0);
    close(fd);
    return 0;
}
