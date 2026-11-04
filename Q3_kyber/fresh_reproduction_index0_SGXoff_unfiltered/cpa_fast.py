#!/usr/bin/env python3
"""Fast CPA: chunked hypothesis + incremental Pearson. Value model (K*b)%q, rank of true key."""
import numpy as np, pandas as pd, csv, sys, time
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

base = "/home/himanshu/HDD/Himanshu/RAPL_Consolidated/Asian_Host_Intel_reply/PoC_Kyber"
log = "/tmp/claude-1008/-home-himanshu/0fad18d5-390f-4d1f-982b-6bdddea8c8a6/scratchpad/cpa_fast.progress"
open(log, "w").close()
off = run(f"{base}/fresh_reproduction_index0_SGXOFF/ntt_traces_with_b0_as_random_a0_new.csv", "OFF", log)
on  = run(f"{base}/fresh_reproduction_index0/ntt_traces_with_b0_as_random_a0_new.csv", "ON ", log)

with open("/tmp/claude-1008/-home-himanshu/0fad18d5-390f-4d1f-982b-6bdddea8c8a6/scratchpad/cpa_compare.csv","w",newline="") as f:
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
