#!/usr/bin/env bash
# run_hw_random.sh -- collect the corrected HW-leakage dataset (random operands)
# under controlled conditions (fixed frequency, isolated core, filtering state
# recorded). Produces weight- and distance-model CSVs for regression analysis.
#
#   sudo bash run_hw_random.sh [N_per_hw] [iters]
# defaults: N_per_hw=60, iters=2e9  (~15 min weight + ~25 min distance)
set -u
N="${1:-60}"; ITERS="${2:-2000000000}"; SEED=20261030; CPU=2; HWSTEP=4
SRC=/home/agv/hw_random_ct.c
BIN=/home/agv/hw_random_ct
TS=$(date +%Y%m%dT%H%M%S)
OUT=/home/agv/rapl_revision_2026/results/hw_random_$TS
mkdir -p "$OUT"
[ "$(id -u)" -eq 0 ] || { echo "run as root"; exit 1; }

gcc -O2 -march=native -o "$BIN" "$SRC" || { echo "compile failed"; exit 1; }

# --- pick the PP0 (core) RAPL domain if present, else package ---
RAPL=""
for d in /sys/class/powercap/intel-rapl:0/intel-rapl:0:*; do
  [ -e "$d/name" ] || continue
  if [ "$(cat "$d/name" 2>/dev/null)" = "core" ]; then RAPL="$d/energy_uj"; fi  # exact: not "uncore"
done
[ -n "$RAPL" ] || RAPL=/sys/class/powercap/intel-rapl:0/energy_uj
echo "RAPL domain: $RAPL  ($(cat "$(dirname "$RAPL")/name" 2>/dev/null))"

# --- control DVFS: performance governor + disable turbo (best effort) ---
for g in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do echo performance > "$g" 2>/dev/null; done
echo 1 > /sys/devices/system/cpu/intel_pstate/no_turbo 2>/dev/null \
  || echo 1 > /sys/devices/system/cpu/cpufreq/boost 2>/dev/null
# pin frequency hard: min=max so the core does not downclock between measurements
for c in /sys/devices/system/cpu/cpu*/cpufreq; do
  [ -w "$c/scaling_min_freq" ] && cat "$c/scaling_max_freq" > "$c/scaling_min_freq" 2>/dev/null
done
echo "governor: $(cat /sys/devices/system/cpu/cpu$CPU/cpufreq/scaling_governor 2>/dev/null)  no_turbo=$(cat /sys/devices/system/cpu/intel_pstate/no_turbo 2>/dev/null)"

# --- provenance (MSR / filtering state) ---
modprobe msr 2>/dev/null
{
  echo "# host=$(hostname) date=$(date -Is) cpu_core=$CPU"
  echo "# 0x3a=$(rdmsr -c -0 -p0 0x3a 2>/dev/null) SGX_bit18=$(( ($(rdmsr -c -0 -p0 0x3a)>>18)&1 ))"
  echo "# 0x10a=$(rdmsr -c -0 -p0 0x10a 2>/dev/null)"
  echo "# 0x1a4=$(rdmsr -c -0 -p0 0x1a4 2>/dev/null) ENERGY_FILTERING_bit0=$(( $(rdmsr -c -0 -p0 0x1a4)&1 ))"
  echo "# rapl_domain=$RAPL  N_per_hw=$N iters=$ITERS hw_step=$HWSTEP seed=$SEED"
} | tee "$OUT/provenance.txt"

echo ">> WEIGHT model (steady-state HW)..."
"$BIN" "$N" "$ITERS" "$SEED" weight   "$HWSTEP" "$CPU" "$RAPL" > "$OUT/hw_weight.csv"   2>"$OUT/weight.log"
echo "   rows: $(($(wc -l < "$OUT/hw_weight.csv")-1))"
echo ">> DISTANCE model (switching, vs fixed reference)..."
"$BIN" "$N" "$((ITERS/2))" "$SEED" distance "$HWSTEP" "$CPU" "$RAPL" > "$OUT/hw_distance.csv" 2>"$OUT/distance.log"
echo "   rows: $(($(wc -l < "$OUT/hw_distance.csv")-1))"

echo
echo "Done. CSVs in $OUT (hw_weight.csv, hw_distance.csv) + provenance.txt"
echo "Bring them back for regression + CI analysis."
