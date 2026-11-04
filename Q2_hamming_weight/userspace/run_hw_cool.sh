#!/usr/bin/env bash
# Collect traces for one Hamming weight on a COOL machine (same config as the
# HW0 cold run): cooldown, then REPEAT reps of bench_mov, wrap-corrected delta.
#   sudo bash run_hw_cool.sh <HW> [REPEAT] [COOLDOWN_SEC]   defaults: 100 180
# HW must be one of 0 8 16 24 32 40 48 56 64
set -u
HW="${1:?usage: run_hw_cool.sh <HW 0..64 step8> [REPEAT] [COOLDOWN]}"
REPEAT="${2:-100}"; COOL="${3:-180}"; ITERS=15000000000; CPU=2
case "$HW" in
  0) OP=0x0000000000000000;; 8) OP=0x00000000000000FF;; 16) OP=0x000000000000FFFF;;
  24) OP=0x0000000000FFFFFF;; 32) OP=0x00000000FFFFFFFF;; 40) OP=0x000000FFFFFFFFFF;;
  48) OP=0x0000FFFFFFFFFFFF;; 56) OP=0x00FFFFFFFFFFFFFF;; 64) OP=0xFFFFFFFFFFFFFFFF;;
  *) echo "HW must be 0/8/16/24/32/40/48/56/64"; exit 1;; esac
RAPLDIR=/sys/class/powercap/intel-rapl:0; RAPL=$RAPLDIR/energy_uj; MAXR=$(cat $RAPLDIR/max_energy_range_uj)
BIN=/home/agv/bench_mov; FQ=/sys/devices/system/cpu/cpu$CPU/cpufreq/scaling_cur_freq
TS=$(date +%Y%m%dT%H%M%S); OUT=/home/agv/rapl_revision_2026/results/hw${HW}_cool_$TS; mkdir -p "$OUT"
[ "$(id -u)" -eq 0 ] || { echo "run as root"; exit 1; }
echo "HW=$HW operand=$OP  cooling ${COOL}s (stay idle)..."; sleep "$COOL"
echo "run,energy_uJ,freq_khz" > "$OUT/hw${HW}_cool.csv"
for ((i=1;i<=REPEAT;i++)); do
  e0=$(cat $RAPL); taskset -c $CPU "$BIN" $ITERS "$OP"; e1=$(cat $RAPL); f=$(cat $FQ 2>/dev/null)
  if [ "$e1" -ge "$e0" ]; then d=$((e1-e0)); else d=$((e1 + MAXR - e0)); fi
  echo "$i,$d,$f" >> "$OUT/hw${HW}_cool.csv"; sleep 0.1
done
echo "Done -> $OUT/hw${HW}_cool.csv  ($(($(wc -l < "$OUT/hw${HW}_cool.csv")-1)) rows)"
