#!/usr/bin/env bash
# run_sgx_hw_paper.sh -- Hamming-weight experiment EXACTLY as in the paper (S V-B):
#   * inside the SGX enclave (ECALL MOV loop)
#   * PP0 (core) domain, energy read immediately before and after the loop
#   * 5e9 iterations per operand (paper's per-instruction count)
#   * operands spanning HW 0->64 at the figure points {0,16,32,48,64}
#   * measured SEQUENTIALLY in increasing HW order, ONE measurement per HW
#   * raw bracketed energy, NO baseline subtraction (as S V-B reports)
#   sudo bash run_sgx_hw_paper.sh
set -u
PROJ=/home/agv/sgx_mov_hw          # reuses the built in-enclave MOV app
TS=$(date +%Y%m%dT%H%M%S); OUT=/home/agv/rapl_revision_2026/results/sgx_hwpaper_$TS
[ "$(id -u)" -eq 0 ] || { echo "run as root (sudo): PP0 MSR + enclave"; exit 1; }
[ -x "$PROJ/app" ] || { echo "build first: cd $PROJ && make SGX_MODE=HW SGX_DEBUG=1"; exit 1; }
mkdir -p "$OUT"
set +u; source /opt/intel/sgxsdk/environment; set -u
modprobe msr 2>/dev/null
cd "$PROJ"
{ echo "# PAPER-EXACT S V-B: in-enclave MOV, PP0(0x639), 5e9 iters, HW{0,16,32,48,64} sequential single pass, no baseline"
  echo "# host=$(hostname) date=$(date -Is) boot_id=$(cat /proc/sys/kernel/random/boot_id)"
  echo "# 0x1a4=$(rdmsr -c -0 -p0 0x1a4 2>/dev/null) ENERGY_FILTERING_bit0=$(( $(rdmsr -0 -p0 0x1a4 2>/dev/null)&1 ))"
  echo "# 0x3a=$(rdmsr -c -0 -p0 0x3a 2>/dev/null) SGX_bit18=$(( ($(rdmsr -0 -p0 0x3a 2>/dev/null)>>18)&1 ))"; } | tee "$OUT/provenance.txt"
# REPEAT=1 -> one sequential pass over HW 0,16,32,48,64 (round==block when 1 rep)
./app 1 5000000000 > "$OUT/hw_paper.csv" 2>> "$OUT/provenance.txt"
echo "done -> $OUT/hw_paper.csv"
cat "$OUT/hw_paper.csv"
