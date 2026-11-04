import csv
import os
import matplotlib.pyplot as plt

RESULTS_DIR = "results/"
TRACE_TARGET = 1_000_000

thresholds = [5, 11, 25, 50, 100, 250]
counts = {t: 0 for t in thresholds}

# ======================
# Collect ranks @ 1M
# ======================
for idx in range(256):
    fname = f"CPA_index{idx}_ab_q.csv"
    path = os.path.join(RESULTS_DIR, fname)

    if not os.path.exists(path):
        continue

    with open(path, newline="") as f:
        reader = csv.reader(f)
        header = next(reader)

        for row in reader:
            if not row or row[0] == "Top10_keys":
                break

            traces = int(row[0])
            rank   = int(row[1])

            if traces == TRACE_TARGET:
                for t in thresholds:
                    if rank <= t:
                        counts[t] += 1
                break

# ======================
# Bar plot
# ======================
labels = [f"<= {t}" for t in thresholds]
values = [counts[t] for t in thresholds]

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 12,
})

plt.figure(figsize=(6.5, 4))

bars = plt.bar(labels, values)

plt.ylabel("Number of keys")
plt.xlabel("Rank threshold")
plt.title("Key Rank Distribution after 1M Traces")

plt.grid(axis="y", linestyle="--", linewidth=0.6, alpha=0.6)
plt.tight_layout()
plt.savefig("rank_thresholds_1M.pdf")
plt.show()
