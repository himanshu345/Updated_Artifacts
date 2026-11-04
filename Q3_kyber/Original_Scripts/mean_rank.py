import csv
import os
import numpy as np
from collections import defaultdict

# ======================
# Parameters
# ======================
RESULTS_DIR = "results"
START_IDX = 0
END_IDX   = 255

# ======================
# Storage: traces -> list of ranks
# ======================
ranks_per_trace = defaultdict(list)

# ======================
# Read all CSVs
# ======================
for idx in range(START_IDX, END_IDX + 1):
    fname = f"CPA_index{idx}_ab_q.csv"
    path = os.path.join(RESULTS_DIR, fname)

    if not os.path.exists(path):
        print(f"[!] Missing {fname}, skipping")
        continue

    with open(path, newline="") as f:
        reader = csv.reader(f)
        header = next(reader)

        for row in reader:
            if not row or row[0] == "Top10_keys":
                break

            traces = int(row[0])
            rank   = int(row[1])

            ranks_per_trace[traces].append(rank)

# ======================
# Compute mean ranks
# ======================
out_file = os.path.join(RESULTS_DIR, "mean_rank_vs_traces_0_255.csv")

with open(out_file, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Traces", "MeanRank", "StdRank", "NumFiles"])

    for traces in sorted(ranks_per_trace.keys()):
        ranks = np.array(ranks_per_trace[traces], dtype=np.float64)
        writer.writerow([
            traces,
            ranks.mean(),
            ranks.std(),
            len(ranks)
        ])

print(f"\n✓ Mean rank computed and saved to:\n  {out_file}")
