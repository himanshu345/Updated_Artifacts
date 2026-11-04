/* hw_random_ct.c -- methodologically sound operand Hamming-weight leakage test.
 *
 * Fixes the design flaws of the contiguous-pattern sweep:
 *   - MANY RANDOM operands per HW level (random bit positions), so Hamming
 *     weight is decorrelated from integer magnitude and bit position.
 *   - Two leakage models:
 *       weight   : load the SAME random operand repeatedly (steady-state HW).
 *       distance : alternate operand with a fixed reference each iteration so
 *                  bits actually toggle (Hamming-DISTANCE / switching model);
 *                  we then regress energy vs HD = popcount(operand XOR ref).
 *   - Fisher-Yates-shuffled interleaved schedule (kills monotonic drift).
 *   - Core pinning; per-measurement CPU-frequency logging (control for DVFS).
 *   - Every measurement is its own CSV row for downstream regression + CIs.
 *
 * Build : gcc -O2 -march=native -o hw_random_ct hw_random_ct.c
 * Usage : sudo ./hw_random_ct <N_per_hw> <iters> <seed> <weight|distance> \
 *                             <hw_step> <cpu> <rapl_energy_uj_path>
 * Example: sudo ./hw_random_ct 60 2000000000 20261030 weight 4 2 \
 *            /sys/class/powercap/intel-rapl:0/intel-rapl:0:0/energy_uj
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sched.h>
#include <time.h>
#include <fcntl.h>
#include <inttypes.h>

static volatile uint64_t gsrc, gref, gop;   /* operands held in memory */

static uint64_t sm_state;
static uint64_t splitmix64(void){
    uint64_t z = (sm_state += 0x9E3779B97F4A7C15ULL);
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
    return z ^ (z >> 31);
}
/* uniform 64-bit value with EXACTLY w bits set, random positions */
static uint64_t rand_operand_hw(int w){
    int idx[64]; for(int i=0;i<64;i++) idx[i]=i;
    for(int i=0;i<w;i++){
        int j = i + (int)(splitmix64() % (uint64_t)(64 - i));
        int t=idx[i]; idx[i]=idx[j]; idx[j]=t;
    }
    uint64_t v=0; for(int i=0;i<w;i++) v |= (1ULL<<idx[i]);
    return v;
}
static inline void loop_weight(uint64_t it){
    for(uint64_t i=0;i<it;i++)
        asm volatile("movq (%0), %%rax\n"::"r"(&gsrc):"rax");
}
static inline void loop_distance(uint64_t it){
    for(uint64_t i=0;i<it;i++){
        asm volatile("movq (%0), %%rax\n"::"r"(&gref):"rax");
        asm volatile("movq (%0), %%rax\n"::"r"(&gop):"rax");
    }
}
static inline uint64_t read_rapl(int fd){
    char b[32]; if(lseek(fd,0,SEEK_SET)<0){perror("lseek");exit(1);}
    ssize_t n=read(fd,b,sizeof(b)-1); if(n<=0){perror("read");exit(1);}
    b[n]=0; return strtoull(b,NULL,10);
}
static uint64_t read_max_range(const char*p){
    char rp[600]; snprintf(rp,sizeof(rp),"%s",p);
    char*s=strrchr(rp,'/'); if(!s){fprintf(stderr,"bad rapl path\n");exit(1);}
    snprintf(s+1,sizeof(rp)-(s+1-rp),"max_energy_range_uj");
    FILE*f=fopen(rp,"r"); if(!f){perror("max_energy_range_uj");exit(1);}
    uint64_t r=0; if(fscanf(f,"%"SCNu64,&r)!=1){fprintf(stderr,"parse range\n");exit(1);}
    fclose(f); return r;
}
static inline uint64_t edelta(uint64_t a,uint64_t b,uint64_t m){return b>=a?b-a:b+m-a;}
static long read_freq_khz(int cpu){
    char p[128]; snprintf(p,sizeof(p),
        "/sys/devices/system/cpu/cpu%d/cpufreq/scaling_cur_freq",cpu);
    FILE*f=fopen(p,"r"); if(!f) return -1;
    long v=-1; if(fscanf(f,"%ld",&v)!=1) v=-1; fclose(f); return v;
}

int main(int argc,char**argv){
    int    N      = argc>1?atoi(argv[1]):60;
    uint64_t iters= argc>2?strtoull(argv[2],NULL,10):2000000000ULL;
    sm_state      = argc>3?strtoull(argv[3],NULL,10):(uint64_t)time(NULL);
    const char*mode=argc>4?argv[4]:"weight";
    int    hwstep = argc>5?atoi(argv[5]):4;
    int    cpu    = argc>6?atoi(argv[6]):2;
    const char*rp = argc>7?argv[7]:"/sys/class/powercap/intel-rapl:0/energy_uj";
    int dist = (strcmp(mode,"distance")==0);

    cpu_set_t set; CPU_ZERO(&set); CPU_SET(cpu,&set);
    if(sched_setaffinity(0,sizeof(set),&set)!=0) perror("sched_setaffinity");
    int fd=open(rp,O_RDONLY); if(fd<0){perror("open rapl");return 1;}
    uint64_t maxr=read_max_range(rp);

    /* HW levels: 0, step, ..., 64 (always include 64) */
    int levels[80],nl=0;
    for(int w=0;w<=64;w+=hwstep) levels[nl++]=w;
    if(levels[nl-1]!=64) levels[nl++]=64;

    /* fixed reference for distance mode (record it) */
    uint64_t ref = dist ? rand_operand_hw(32) : 0;

    /* pre-generate N random operands per level */
    uint64_t *ops = malloc((size_t)nl*N*sizeof(uint64_t));
    for(int L=0;L<nl;L++) for(int k=0;k<N;k++) ops[L*N+k]=rand_operand_hw(levels[L]);

    /* shuffled interleaved schedule over all (level,operand) measurements */
    int total=nl*N; int*sched=malloc((size_t)total*sizeof(int));
    for(int i=0;i<total;i++) sched[i]=i;
    for(int i=total-1;i>0;i--){ int j=(int)(splitmix64()%(uint64_t)(i+1));
        int t=sched[i]; sched[i]=sched[j]; sched[j]=t; }

    fprintf(stderr,"# mode=%s N_per_hw=%d levels=%d iters=%"PRIu64
            " cpu=%d seed_ref=0x%016"PRIx64" rapl=%s maxrange=%"PRIu64"\n",
            mode,N,nl,iters,cpu,ref,rp,maxr);
    printf("mode,operand_hex,ref_hex,hamming,hamming_distance,run_idx,energy_uJ,elapsed_ns,freq_khz\n");

    for(int s=0;s<total;s++){
        int id=sched[s]; int L=id/N; uint64_t op=ops[id];
        int hw=levels[L];
        int hd=dist ? __builtin_popcountll(op^ref) : hw;
        struct timespec t0,t1;
        if(dist){ gref=ref; gop=op; } else { gsrc=op; }
        clock_gettime(CLOCK_MONOTONIC_RAW,&t0);
        uint64_t e0=read_rapl(fd);
        if(dist) loop_distance(iters); else loop_weight(iters);
        uint64_t e1=read_rapl(fd);
        clock_gettime(CLOCK_MONOTONIC_RAW,&t1);
        uint64_t ns=(uint64_t)(t1.tv_sec-t0.tv_sec)*1000000000ULL+(t1.tv_nsec-t0.tv_nsec);
        printf("%s,0x%016"PRIx64",0x%016"PRIx64",%d,%d,%d,%"PRIu64",%"PRIu64",%ld\n",
               mode,op,ref,hw,hd,s,edelta(e0,e1,maxr),ns,read_freq_khz(cpu));
        fflush(stdout);
    }
    free(ops); free(sched); close(fd);
    return 0;
}
