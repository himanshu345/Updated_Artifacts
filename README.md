# Intel Response — Artifact Bundle

Supporting artifacts for `Intel_Response` / `main.pdf`. Every file here is referenced
by the response document. Machine for all data: Lenovo ThinkCentre M920t, Intel
Core i7-8700 (Coffee Lake), microcode 0xFA, Ubuntu 20.04 / Linux 5.15.0-139. SGX
enabled and locked (CPU-enforced RAPL energy filtering, INTEL-SA-00389).

## figures/  — all figures in the PDF
| File | Where in PDF |
|------|--------------|
| `msr_sgx_filtering.png` | Q1, Figure 1 — live MSR capture (SGX enabled; `0xBC` state) |
| `rapl_filtering.png`    | Q1 §1.1, Figure 2 — RAPL filtering mechanism (SGX-Enable OR Energy-Filtering-Enable) |
| `hw_paper_4runs.png`    | Q2, Figure 3 — in-enclave MOV, 4 sequential passes |
| `hw_paper_100instances.png` | Q2, Figure 4 — 100 passes + per-pass change distribution |
| `kyber_setup_diagram.png` | Q3, Figure 5 — per-index CPA setup |
| `kyber_rank_convergence.png` | Q3 — fresh index-0 true-key rank vs. traces (value model) |
| `rapl_filtering_1ms_update.png` | Q4 — Intel advisory excerpt (highlighted: update rate stays ~1ms under filtering) |

## Q2_hamming_weight/ — data behind the Q2 Results table

### sgx_enclave/  (in-enclave MOV, PP0 MSR, 5e9 iters/operand, filtering active)
| File | Table row |
|------|-----------|
| `Enclave.cpp`, `Enclave.edl`, `App.cpp` | in-enclave harness (ECALL MOV loop) |
| `run_sgx_hw_paper.sh` | generator for the 4 sequential passes |
| `results/hw_paper_4runs/run_*.csv` | **Sequential pass, runs 1–4** |
| `hw_paper_4runs.png` | figure for the 4 passes |
| `run_sgx_hw_paper100.sh` | generator for the 100-pass run |
| `results/hw_paper_100instances/hw_paper100.csv` | **Mean of 100 passes** |
| `hw_paper_100instances.png` | figure for the 100 passes |

### userspace/  (bench_mov + powercap sysfs)
| File | Table row | Verified |
|------|-----------|----------|
| `bench_mov.c`, `rapl-reader.c`, `Makefile` | userspace harness | — |
| `run_hw_random.sh` + `hw_random_ct.c`; data `hw_weight_core.csv` (weight model → table values), `hw_distance_core.csv` (distance model) | **Randomized operands (0–64 step 4), PP0, 2e9** | ✅ HW0..64 = 11.24/11.31/11.25/11.29/11.21 M µJ (from `hw_weight_core.csv`) |
| `run_hw0_hw64.sh` + `bench_mov.c`; data `hw0_hw64_drift_demo/hw0.csv`, `hw64.csv`, `hw0_hw64_plot.png` | **Sequential blocked (HW0, HW64), 1.5e10, package** | ✅ 41.31 / 42.30 M µJ |
| `run_hw_cool.sh <HW>` + `bench_mov.c`; data `separate_blocks_cold/hw{0,16,32,64}/hw*_cool.csv` | **Separate blocks (HW0,16,32,64; HW48 not collected), 1.5e10, package** — each weight collected as its own cold block (cooldown), 100 reps | ✅ 37.06 / 37.80 / 38.05 / 37.91 M µJ |

## Collection & plotting scripts (one per experiment)
| Script | Collects |
|--------|----------|
| `sgx_enclave/run_sgx_hw_paper.sh` | SGX 4 sequential passes |
| `sgx_enclave/run_sgx_hw_paper100.sh` | SGX mean of 100 passes |
| `userspace/run_hw_random.sh` (`hw_random_ct.c`) | userspace randomized operands (row 1) |
| `userspace/run_hw0_hw64.sh` (`bench_mov.c`) | userspace HW0/HW64 sequential blocked (row 2) |
| `userspace/run_hw_cool.sh` (`bench_mov.c`) | userspace separate cold blocks (row 3) |
| `replot_hw.py` | regenerates `hw_paper_4runs.png` and `hw_paper_100instances.png` from the SGX CSVs |

All Q2 Results-table rows are backed by data **and** a collection script in this bundle.

## Q3_kyber/ — CRYSTALS-Kyber CPA (value/identity model)
Target: the base-case Montgomery product `m0 = s_i · b mod q` (q=3329). Leakage model
is the **value** `(k·b) mod q`, NOT its Hamming weight.

| Path | Contents |
|------|----------|
| `Original_Scripts/pwmtraces.py` | trace collection (per index: T=1e6 traces, M=100 PWMs/trace; operand `(b,0)`/`(0,b)`) |
| `Original_Scripts/precompute_hypothesis.py` | builds value hypothesis `(K*b) % Q` (the `hw()` helper is present but unused) |
| `Original_Scripts/cpa_from_hypothesis.py` | CPA: correlates energy with the value hypothesis |
| `Original_Scripts/mean_rank.py`, `Original_Scripts/rank_wise_bar.py` | rank aggregation / plots |
| `fresh_reproduction_index0_SGXon_filtered/` | **filtered** (SGX ON) index-0 run: `ntt_traces_index0_SGXon_filtered.csv` (1e6) + `CPA_index0_SGXon_filtered.csv` (rank→11/3329) + README |
| `fresh_reproduction_index0_SGXoff_unfiltered/` | **unfiltered** (SGX OFF, separate boot) index-0 run: `ntt_traces_index0_SGXoff_unfiltered.csv` (1e6) + `filtered_vs_unfiltered_rank.csv` + `cpa_fast.py` + README. Reaches rank-25 at ~2e5 traces vs ~5e5 filtered (~2.5× fewer) |
| `Original_Sample_Traces/` | 3 representative full-size (1e6-row) trace files (indices 0–2) |
| `Original_results/CPA_index*.csv` | per-index rank-vs-traces CPA results (all 256 indices) |
| `figures/mean_rank_convergence.png`, `rank_threshold_results.png` | original Kyber result figures |

**Scale:** T=1e6 traces per index × 256 indices = 2.56e8 measurements (2.56e10 base-case
multiplies); no full decapsulations. Wall-clock ≈ 2.6 min/index, ≈ 11 h for all 256
indices (measured on the i7-8700).

**NOTE — complete trace set:** the full 256-index raw traces (`PoC_Kyber/full_traces/`,
~2.6 GB) are NOT copied into this bundle to keep it portable. The new index-0 traces and
3 sample-index traces above are representative; the full set is available on request /
on the lab machine. (Say the word to include it here.)

## Q4_fingerprinting/ — sampling cadence + fingerprinting attacks
Filtering was active (SGX-enforced, Q1). Per Intel's advisory the RAPL update rate
stays ~1ms under filtering (`figures/rapl_filtering_1ms_update.png`), so reading
distinct 1ms/5ms samples does not imply the mitigation was off.

| Path | Contents |
|------|----------|
| `website/main_6sites.cpp`, `run_collect_6sites.sh`, `Makefile` | website collector: 1ms sampling, 1000 samples/trace (1s window); 300 traces/site (paper: 10000/site) |
| `website/fresh_reproduction_6site/traces/*.csv` | fresh 6-site traces (300 traces/site) |
| `website/fresh_reproduction_6site/confusion_6site.png` | confusion matrix (z-scored 1-NN: 31.8% vs 16.7% chance) |
| `model/collect_dnn_traces.py`, `extract_and_classify.py`, `run_collect_dnn.sh`, `dnn_fp_check.py` | DNN-architecture fingerprinting (14 archs, 5ms) |
| `model/fresh_reproduction/feature_dataset_fresh.csv`, `dnn_confusion_fresh_LORO.png` | fresh leave-one-run-out result (66.7% vs 7.1% chance) |

The ~1ms update cadence is established from Intel's advisory
(`figures/rapl_filtering_1ms_update.png`, which states the update rate stays ~1ms under
filtering) and from the website traces themselves (~99% of adjacent 1ms samples are
distinct updates).

**Key point:** ~1ms update cadence + filtered values (SGX enabled) still leak enough for
both attacks — website ~2x chance, model ~9x chance.
