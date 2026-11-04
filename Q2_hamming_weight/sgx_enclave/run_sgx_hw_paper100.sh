#!/usr/bin/env bash
# run_sgx_hw_paper100.sh -- repeat the PAPER-EXACT S V-B pass many times.
# Each INSTANCE = one sequential in-enclave MOV pass over HW {0,16,32,48,64}
# (PP0 MSR, 5e9 iters/operand, no baseline). COOL seconds idle between instances.
# All instances appended to one CSV: instance,hamming,run_order,energy_uJ
#   sudo bash run_sgx_hw_paper100.sh [INSTANCES] [COOL_s] [ITERS]   def 100 1 5e9
set -u
INSTANCES="${1:-100}"; COOL="${2:-1}"; ITERS="${3:-5000000000}"
PROJ=/home/agv/sgx_mov_hw
TS=$(date +%Y%m%dT%H%M%S); OUT=/home/agv/rapl_revision_2026/results/sgx_hwpaper100_$TS
[ "$(id -u)" -eq 0 ] || { echo "run as root (sudo): PP0 MSR + enclave"; exit 1; }
[ -x "$PROJ/app" ] || { echo "build first in $PROJ"; exit 1; }
mkdir -p "$OUT"
set +u; source /opt/intel/sgxsdk/environment; set -u
modprobe msr 2>/dev/null
{ echo "# PAPER-EXACT S V-B x$INSTANCES instances; in-enclave MOV, PP0(0x639), ITERS=$ITERS, HW{0,16,32,48,64} sequential, COOL=${COOL}s between instances, no baseline"
  echo "# host=$(hostname) date=$(date -Is) boot_id=$(cat /proc/sys/kernel/random/boot_id)"
  echo "# 0x1a4=$(rdmsr -c -0 -p0 0x1a4 2>/dev/null) ENERGY_FILTERING_bit0=$(( $(rdmsr -0 -p0 0x1a4 2>/dev/null)&1 ))"
  echo "# 0x3a=$(rdmsr -c -0 -p0 0x3a 2>/dev/null) SGX_bit18=$(( ($(rdmsr -0 -p0 0x3a 2>/dev/null)>>18)&1 ))"; } | tee "$OUT/provenance.txt"
CSV="$OUT/hw_paper100.csv"
echo "instance,hamming,run_order,energy_uJ" > "$CSV"
cd "$PROJ"
for ((i=1;i<=INSTANCES;i++)); do
  sleep "$COOL"
  ./app 1 "$ITERS" 2>>"$OUT/run.log" \
    | awk -F, -v inst="$i" 'NR>1 && $1 ~ /^[0-9]+$/ {print inst","$1","$3","$4}' >> "$CSV"
  echo "instance $i/$INSTANCES done @ $(date +%H:%M:%S)  (rows so far $(($(wc -l < "$CSV")-1)))"
done
echo "DONE -> $CSV ($(($(wc -l < "$CSV")-1)) rows = $INSTANCES instances x 5 HW)"
