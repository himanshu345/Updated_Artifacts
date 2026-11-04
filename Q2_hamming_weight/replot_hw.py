#!/usr/bin/env python3
"""Regenerate the two in-enclave Hamming-weight figures with neutral titles
(no editorializing trend verdicts). Data is unchanged."""
import csv, glob, os, statistics
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = "/home/himanshu/HDD/Himanshu/RAPL_Consolidated/Asian_Host_Intel_reply/PoC_HammingWeight/sgx_mov_hw"
HW = [0, 16, 32, 48, 64]

# ---------- Figure 1: 4 sequential passes + mean ----------
run_files = sorted(glob.glob(f"{BASE}/results/hw_paper_4runs/run_*.csv"))
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
plt.savefig(f"{BASE}/hw_paper_4runs.png", dpi=150)
plt.close()
print("wrote hw_paper_4runs.png")

# ---------- Figure 2: 100 passes mean (+ per-pass change distribution) ----------
inst = {}
for r in csv.DictReader(open(f"{BASE}/results/hw_paper_100instances/hw_paper100.csv")):
    inst.setdefault(int(r["instance"]), {})[int(r["hamming"])] = float(r["energy_uJ"]) / 1e6
passes = [[inst[k][h] for h in HW] for k in sorted(inst) if all(h in inst[k] for h in HW)]

mean100 = [statistics.mean(p[i] for p in passes) for i in range(len(HW))]
sem100  = [statistics.pstdev(p[i] for p in passes) / (len(passes) ** 0.5) for i in range(len(HW))]
change  = [100.0 * (p[-1] - p[0]) / p[0] for p in passes]   # HW0 -> HW64 percent change

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
for p in passes:
    ax1.plot(HW, p, color="gray", alpha=0.12, linewidth=0.6)
ax1.errorbar(HW, mean100, yerr=sem100, fmt="s-", color="crimson", linewidth=2.5,
             capsize=4, label="mean of 100 passes")
ax1.set_xlabel("operand Hamming weight")
ax1.set_ylabel("in-enclave PP0 energy (M µJ)")
ax1.set_title("In-enclave MOV: 100 sequential passes + mean")
ax1.legend(loc="best", frameon=True)
ax1.grid(True, linestyle="--", alpha=0.4)

ax2.hist(change, bins=20, color="steelblue", edgecolor="white")
ax2.axvline(statistics.mean(change), color="crimson", linestyle="--",
            label=f"mean {statistics.mean(change):+.2f}%")
ax2.set_xlabel("per-pass HW0 → HW64 energy change (%)")
ax2.set_ylabel("count")
ax2.set_title("Distribution of per-pass HW0 → HW64 change")
ax2.legend(loc="best", frameon=True)
ax2.grid(True, linestyle="--", alpha=0.3)
plt.tight_layout()
plt.savefig(f"{BASE}/hw_paper_100instances.png", dpi=150)
plt.close()
print("wrote hw_paper_100instances.png")
print(f"(n_passes={len(passes)}, mean change {statistics.mean(change):+.2f}%)")
