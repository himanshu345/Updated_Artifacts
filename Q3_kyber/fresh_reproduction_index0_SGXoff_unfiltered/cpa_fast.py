#!/usr/bin/env python3
"""Fast CPA: chunked hypothesis + incremental Pearson. Value model (K*b)%q, rank of true key."""
import numpy as np, pandas as pd, csv, sys, time, os
Q = 3329; STEP = 100_000; TRUE = 124
K = np.arange(Q, dtype=np.int64)

def run(trace, label, log):
    t0 = time.time()
    df = pd.read_csv(trace)
    b = df.iloc[:, 0].to_numpy(np.int64)
    e = df.iloc[:, 1].to_numpy(np.float64)
    N = len(e)
    sHe = np.zeros(Q); sH = np.zeros(Q); sH2 = np.zeros(Q)
    sE = 0.0; sE2 = 0.0; n = 0
    out = []
    for start in range(0, N, STEP):
        end = min(start + STEP, N)
        bc = b[start:end]; ec = e[start:end]
        H = (K[:, None] * bc[None, :]) % Q           # (Q, chunk) int64
        Hf = H.astype(np.float64)
        sHe += Hf @ ec
        sH  += Hf.sum(axis=1)
        sH2 += (Hf * Hf).sum(axis=1)
        sE  += ec.sum(); sE2 += (ec * ec).sum(); n = end
        cov = n * sHe - sH * sE
        vH  = n * sH2 - sH * sH
        vE  = n * sE2 - sE * sE
        scores = np.abs(cov) / np.sqrt(vH * vE)
        rank = int(np.sum(scores > scores[TRUE]) + 1)
        out.append((n, rank))
        with open(log, "a") as f:
            f.write(f"{label}: Traces={n:7d}  Rank={rank:4d}  (+{time.time()-t0:.0f}s)\n")
    return out

HERE = os.path.dirname(os.path.abspath(__file__))   # fresh_reproduction_index0_SGXoff_unfiltered/
Q3   = os.path.dirname(HERE)                         # Q3_kyber/
log  = os.path.join(HERE, "cpa_fast.progress")
open(log, "w").close()
off = run(os.path.join(HERE, "ntt_traces_index0_SGXoff_unfiltered.csv"), "OFF", log)
on  = run(os.path.join(Q3, "fresh_reproduction_index0_SGXon_filtered",
                       "ntt_traces_index0_SGXon_filtered.csv"), "ON ", log)

with open(os.path.join(HERE, "filtered_vs_unfiltered_rank.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["Traces","Rank_SGXoff_unfiltered","Rank_SGXon_filtered"])
    for (nn, ro), (_, ri) in zip(off, on): w.writerow([nn, ro, ri])

def firsthit(rows, thr):
    for nn, r in rows:
        if r <= thr: return nn
    return None
with open(log, "a") as f:
    f.write("\nDONE\n")
    for thr in (25, 10, 1):
        f.write(f"traces to rank<= {thr}:  OFF={firsthit(off,thr)}  ON={firsthit(on,thr)}\n")
