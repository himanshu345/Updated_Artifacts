Fresh reproduction of the CRYSTALS-Kyber CPA, index 0 (2026-10-31) — FILTERED.
Traces newly collected on agvtemp25 with Intel SGX enabled (IA32_FEATURE_CONTROL
0x3A bit18 = 1 -> CPU-enforced filtered RAPL, INTEL-SA-00389); PP0/core domain,
1,000,000 traces, num_mults=100, via the unmodified pwmtraces.py (IDX_LIST=[0]).
Hypothesis + CPA run with the unmodified precompute_hypothesis.py /
cpa_from_hypothesis.py (value model H = (k*b) mod q). True key ram1[0] = 124.

Rank of true key vs #traces:
  100k->939, 200k->149, 300k->109, 400k->29, 500k->14, 600k->19,
  700k->11, 800k->11, 900k->11, 1M->11   (out of 3329)

=> monotonic recovery to rank 11/3329 (within the paper's rank-25 bucket).
Confirms the value-model CPA attack reproduces on freshly collected (filtered) data.

Files:
  ntt_traces_index0_SGXon_filtered.csv  (new filtered traces)
  CPA_index0_SGXon_filtered.csv         (rank-vs-traces result)

Counterpart: ../fresh_reproduction_index0_SGXoff_unfiltered/ (SGX-disabled boot).
