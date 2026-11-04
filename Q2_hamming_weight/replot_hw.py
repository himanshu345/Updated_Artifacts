#!/usr/bin/env python3
"""Regenerate the in-enclave Hamming-weight figures from the shipped SGX CSVs.
Paths are resolved relative to this script, so it works anywhere the bundle is cloned.

Outputs (into sgx_enclave/):
  hw_paper_4runs.png        -- 4 sequential in-enclave passes + mean (run 3 emphasized)
  hw_paper_100instances.png -- distribution of per-pass HW0->HW64 energy change (100 passes)
"""
import csv, glob, os, statistics
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "sgx_enclave")          # data + figures live here
HW = [0, 16, 32, 48, 64]

# ---------- Figure 1: 4 sequential passes + mean ----------
run_files = sorted(glob.glob(os.path.join(BASE, "results", "hw_paper_4runs", "run_*.csv")))
runs = []
for f in run_files:
    d = {}
    for r in csv.DictReader(open(f)):
        d[int(r["hamming"])] = float(r["energy_uJ"]) / 1e6
    runs.append([d[h] for h in HW])

mean = [statistics.mean(runs[j][i] for j in range(len(runs))) for i in range(len(HW))]
sem  = [statistics.pstdev(runs[j][i] for j in range(len(runs))) / (len(runs) ** 0.5) for i in range(len(HW))]

plt.figure(figsize=(8, 5))
for i, y in enumerate(runs, 1):
    if i == 3:
        plt.plot(HW, y, "o-", color="green", alpha=1.0, linewidth=2.5,
                 markersize=7, zorder=5, label="run 3")
    else:
        plt.plot(HW, y, "o-", alpha=0.35, linewidth=1, label=f"run {i}")
plt.errorbar(HW, mean, yerr=sem, fmt="s-", color="black", linewidth=2.5,
             capsize=4, label="mean of 4 runs")
plt.xlabel("operand Hamming weight")
plt.ylabel("in-enclave PP0 energy (M µJ)")
plt.title("In-enclave MOV: 4 sequential passes (PP0, $5\\times10^{9}$ iters/operand)")
plt.legend(loc="best", frameon=True)
plt.grid(True, linestyle="--", alpha=0.4)
plt.tight_layout()
plt.savefig(os.path.join(BASE, "hw_paper_4runs.png"), dpi=150)
plt.close()
print("wrote hw_paper_4runs.png")

# ---------- Figure 2: 100 passes -- per-pass HW0->HW64 change distribution ----------
inst = {}
for r in csv.DictReader(open(os.path.join(BASE, "results", "hw_paper_100instances", "hw_paper100.csv"))):
    inst.setdefault(int(r["instance"]), {})[int(r["hamming"])] = float(r["energy_uJ"]) / 1e6
passes = [[inst[k][h] for h in HW] for k in sorted(inst) if all(h in inst[k] for h in HW)]
change = [100.0 * (p[-1] - p[0]) / p[0] for p in passes]     # HW0 -> HW64 percent change
m = statistics.mean(change)

plt.figure(figsize=(7, 5))
plt.hist(change, bins=20, color="steelblue", edgecolor="white")
plt.axvline(m, color="crimson", linestyle="--", label=f"mean {m:+.2f}%")
plt.xlabel(r"per-pass HW0 $\rightarrow$ HW64 energy change (%)")
plt.ylabel("count")
plt.title("In-enclave MOV, 100 sequential passes:\n"
          "distribution of per-pass HW0$\\rightarrow$HW64 change")
plt.legend(loc="upper right", frameon=True)
plt.grid(True, linestyle="--", alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(BASE, "hw_paper_100instances.png"), dpi=150)
plt.close()
print(f"wrote hw_paper_100instances.png  (n_passes={len(passes)}, mean={m:+.2f}%)")
