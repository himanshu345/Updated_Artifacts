#!/usr/bin/env bash
# run_collect_6sites.sh -- build + launch the 6-site WF collection on agv.
#   sudo bash run_collect_6sites.sh [num_traces]      (default 300)
set -u
N="${1:-300}"
SRC=/home/agv/wf_collect/main_6sites.cpp
BIN=/home/agv/wf_collect/main_6sites
TS=$(date +%Y%m%dT%H%M%S)
OUT=/home/agv/wf_collect/run_$TS
[ "$(id -u)" -eq 0 ] || { echo "run as root (sudo)"; exit 1; }
mkdir -p "$OUT"
g++ -O2 -o "$BIN" "$SRC" || { echo "build failed"; exit 1; }
echo "built $BIN; output -> $OUT ; num_traces=$N"
cd "$OUT"
nohup "$BIN" "$N" > "$OUT/collect.log" 2>&1 &
echo "PID $! ; tail -f $OUT/collect.log"
