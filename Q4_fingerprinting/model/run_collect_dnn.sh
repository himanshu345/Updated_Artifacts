#!/usr/bin/env bash
# run_collect_dnn.sh -- build+launch the §VI DNN trace re-collection on agv.
#   sudo bash run_collect_dnn.sh [RUNS] [EPOCHS] [INTERVAL_s]
#   defaults: RUNS=10 EPOCHS=10 INTERVAL=0.025  (matches the paper / originals)
set -u
RUNS="${1:-10}"; EPOCHS="${2:-10}"; INT="${3:-0.025}"
TS=$(date +%Y%m%dT%H%M%S)
OUT=/home/agv/dnn_collect/run_$TS
[ "$(id -u)" -eq 0 ] || { echo "run as root (sudo) -- package RAPL is root-only"; exit 1; }
mkdir -p "$OUT"
echo "output -> $OUT ; runs=$RUNS epochs=$EPOCHS interval=${INT}s"
nohup python3 /home/agv/dnn_collect/collect_dnn_traces.py \
      --out "$OUT" --runs "$RUNS" --epochs "$EPOCHS" --interval "$INT" \
      > "$OUT/collect.log" 2>&1 &
echo "PID $! ; tail -f $OUT/collect.log"
