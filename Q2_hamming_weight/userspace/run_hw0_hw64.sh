#!/usr/bin/env bash
# Collect energy for HW0 (0x0) and HW64 (0xFFFFFFFFFFFFFFFF) INDEPENDENTLY.
# Each operand measured in its own block, its own before/after RAPL read,
# written to a separate CSV. 15e9 iters (paper), package domain, pinned to CPU2.
#   sudo bash run_hw0_hw64.sh [REPEAT]      # default 100 (~17 min)
COOL="${1:-120}";
set -u
REPEAT="${1:-100}"; ITERS=15000000000; CPU=2
RAPL=/sys/class/powercap/intel-rapl:0/energy_uj         # package
BIN=/home/agv/bench_mov
TS=$(date +%Y%m%dT%H%M%S); OUT=/home/agv/rapl_revision_2026/results/hw0_hw64_$TS
mkdir -p "$OUT"
[ "$(id -u)" -eq 0 ] || { echo "run as root"; exit 1; }
modprobe msr 2>/dev/null
{ echo "# HW0 vs HW64 independent; host=$(hostname) date=$(date -Is) ITERS=$ITERS REPEAT=$REPEAT domain=package"
  echo "# 0x1a4=$(rdmsr -c -0 -p0 0x1a4) ENERGY_FILTERING_bit0=$(( $(rdmsr -c -0 -p0 0x1a4)&1 ))"; } | tee "$OUT/provenance.txt"

collect(){ # $1=operand_hex  $2=hw_label  $3=outfile
  echo "run,energy_uJ" > "$3"
  for ((i=1;i<=REPEAT;i++)); do
    e0=$(cat $RAPL); taskset -c $CPU "$BIN" $ITERS "$1"; e1=$(cat $RAPL)
    echo "$i,$((e1-e0))" >> "$3"; sleep 0.1
  done
  echo "  HW$2 done -> $3"
}

sleep "$COOL"
echo ">> collecting HW0  (operand 0x0) independently ..."
collect 0x0000000000000000 0 "$OUT/hw0_new_cool.csv"
sleep "$COOL"
echo ">> collecting HW16  (operand 0xFFFF) independently ..."
collect 0x000000000000FFFF 16 "$OUT/hw16_new_cool.csv"
sleep "$COOL"
echo ">> collecting HW32  (operand 0xFFFFFFFF) independently ..."
collect 0x00000000FFFFFFFF 32 "$OUT/hw32_new_cool.csv"
sleep "$COOL"
echo ">> collecting HW48  (operand 0xFFFFFFFFFFFF) independently ..."
collect 0x0000FFFFFFFFFFFF 48 "$OUT/hw48_new_cool.csv"
sleep "$COOL"
echo ">> collecting HW64 (operand 0xFFFFFFFFFFFFFFFF) independently ..."
collect 0xFFFFFFFFFFFFFFFF 64 "$OUT/hw64_new_cool.csv"
sleep "$COOL"
echo "Done. Files: $OUT/hw0_new.csv , $OUT/hw64_new.csv"
