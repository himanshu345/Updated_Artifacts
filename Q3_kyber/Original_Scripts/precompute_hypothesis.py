import numpy as np
import csv
import os
# ======================
# Kyber parameters
# ======================
Q = 3329
R = 4096
POWER = 12
N_BAR = 3327
# ======================
# Montgomery (vectorized)
# ======================
def montgomery_vec(a, b):
    t = a * b
    m = (t * N_BAR) & (R - 1)
    u = (t + m * Q) >> POWER
    return np.where(u > Q, u - Q, u)
# ======================
# Hamming Weight (vectorized)
# ======================
def hw(x):
    x = x.astype(np.uint16)
    return np.unpackbits(x[..., None].view(np.uint8), axis=-1).sum(axis=-1)
# ======================
# Load b values
# ======================
def load_b_vals(filename):
    b = []
    with open(filename) as f:
        reader = csv.reader(f)
        next(reader)
        for r in reader:
            b.append(int(r[0]))
    return np.array(b, dtype=np.int32)
# ======================
# Secrets (omega)
# ======================
ome1 = [
    3052, 443, 1093, 1075, 513, 1463, 1927, 546, 606, 2468, 2392, 2179,
    3132, 2274, 1077, 2107, 1149, 2537, 646, 1610, 2487, 2284, 1477,
    2939, 1824, 1133, 278, 2043, 1945, 615, 1297, 1233, 134, 1985,
    1298, 2833, 1194, 446, 1195, 1154, 476, 741, 934, 3008, 2559,
    270, 813, 2490, 3045, 1656, 1373, 2989, 550, 2185, 846, 2026,
    1331, 960, 24, 1781, 1078, 2951, 1525, 3172
]
omega = ome1 * 5
# ======================
# Main
# ======================
IDX_LIST=list(range(256))
os.makedirs("hypotheses", exist_ok=True)
K = np.arange(Q, dtype=np.int32)
for IDX in IDX_LIST:
    trace_file = f"traces/ntt_traces_with_b{IDX}_as_random_a{IDX}_new.csv"

    if not os.path.exists(trace_file):
        print(f"[!] Skipping index {IDX} (trace file missing)")
        continue

    trace_file = f"ntt_traces_with_b{IDX}_as_random_a{IDX}_new.csv"
    b_vals = load_b_vals(trace_file)

    # ---------- ab_q ----------
    val = (K[:, None] * b_vals[None, :]) % Q
    os.makedirs("hypothesis", exist_ok=True)
    np.save(f"hypotheses/index{IDX}.npy", val.astype(np.int16))
    print("    saved ab_q (val)")
print("\n✓ All hypotheses stored (value)")

