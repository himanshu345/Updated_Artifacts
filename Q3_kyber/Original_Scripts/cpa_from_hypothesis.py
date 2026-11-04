import numpy as np
import csv
import os
Q = 3329
STEP = 100_000
def load_energy(filename):
    energy = []
    with open(filename) as f:
        reader = csv.reader(f)
        next(reader)
        for r in reader:
            energy.append(float(r[1]))
    return np.array(energy, dtype=np.float32)
def cpa_from_hypotheses(H, energy, true_key):
    energy = energy - energy.mean()
    e_norm = np.linalg.norm(energy)
    Hc = H - H.mean(axis=1, keepdims=True)
    H_norm = np.linalg.norm(Hc, axis=1)
    num = Hc @ energy
    denom = H_norm * e_norm
    scores = np.abs(num / denom)
    rank = np.sum(scores > scores[true_key]) + 1
    return rank, scores
ram1 = [124, 2917, 45, 1802, 102, 11, 2045, 98, 1567, 2401, 876, 19, 3104, 221, 1678, 290, 1455, 327, 2019, 1184, 30, 77, 199, 2650, 1842, 909, 2711, 54, 316, 1489, 2304, 997, 611, 1742, 2891, 1864, 1250, 2067, 418, 3129, 81, 1964, 258, 1433, 3250, 709, 187, 2341, 1602, 94, 2798, 1207, 455, 3191, 3190, 880, 1701, 2664, 37, 142, 2999, 1148, 2033, 621, 1875, 301, 2499, 92, 1356, 2870, 540, 1991, 110, 3227, 1684, 733, 255, 2149, 149, 3042, 903, 1761, 60, 2678, 1302, 414, 3210, 2751, 2417, 1550, 704, 28, 2934, 169, 1980, 2566, 1001, 1829, 312, 1447, 2290, 83, 3205, 611, 174, 2671, 1390, 448, 3007, 911, 2054, 121, 1866, 2450, 63, 1588, 2723, 701, 318, 2137, 740, 2902, 91, 333, 1998, 1154, 3061, 471, 832, 1671, 2844, 52, 190, 2309, 1431, 3277, 612, 1759, 104, 790, 198, 3169, 923, 1417, 2442, 71, 158, 2948, 1199, 2090, 503, 3216, 871, 1768, 289, 1350, 2611, 94, 3099, 612, 1834, 418, 2749, 120, 1507, 2976, 682, 213, 3291, 982, 1643, 57, 245, 2012, 1425, 2868, 718, 1879, 336, 3108, 146, 115, 84, 2277, 2910, 491, 178, 3199, 913, 1440, 2675, 62, 1852, 3001, 733, 221, 2134, 1599, 95, 3256, 1187, 176, 2897, 1408, 472, 2071, 320, 2539, 1679, 489, 3121, 911, 144, 2762, 1203, 1986, 401, 3244, 731, 185, 2145, 779, 2994, 67, 1002, 2418, 1466, 329, 1760, 2875, 512, 219, 138, 389, 642, 777, 904, 1111, 1288, 1399, 1512, 1627, 1739, 1855, 1966, 925, 2193, 2317, 2438, 2547, 2661, 2784, 2899, 3015, 3146, 3268]

IDX_LIST=list(range(256))
os.makedirs("results/", exist_ok=True)
for IDX in IDX_LIST:
    print(f"\n[+] CPA for index {IDX}")
    TRUE_KEY = ram1[IDX]
    print(TRUE_KEY)
    trace_file = f"traces/ntt_traces_with_b{IDX}_as_random_a{IDX}_new.csv"
    hyp_file   = f"hypothesis/index{IDX}.npy"
    if not os.path.exists(trace_file):
        print(f"[!] Missing trace file: {trace_file}")
        continue
    if not os.path.exists(hyp_file):
        print(f"[!] Missing hypothesis file: {hyp_file}")
        continue
    energy = load_energy(trace_file)
    H_full = np.load(hyp_file).astype(np.float32)
    out_file = f"results/CPA_index{IDX}_ab_q.csv"
    with open(out_file, "w", newline="") as fcsv:
        writer = csv.writer(fcsv)
        writer.writerow(["Traces", "Rank", "Corr"])
        for n in range(STEP, len(energy) + 1, STEP):
            rank, scores = cpa_from_hypotheses(H_full[:, :n], energy[:n], TRUE_KEY)
            writer.writerow([n, rank, scores[TRUE_KEY]])
            print(f"  Traces={n:7d} | Rank={rank:4d}")
        top10 = np.argsort(scores)[-10:][::-1]
        writer.writerow([])
        writer.writerow(["Top10_keys", "Scores"])
        for k in top10:
            writer.writerow([k, scores[k]])
print("\n✓ CPA completed (FAST)")
