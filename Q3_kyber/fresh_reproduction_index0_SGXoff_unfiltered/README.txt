Kyber index-0 CPA — UNFILTERED (SGX DISABLED) reproduction
===========================================================
Collected on agv (i7-8700) in a SEPARATE boot with Intel SGX DISABLED in BIOS,
so RAPL reports UNFILTERED energy (IA32_FEATURE_CONTROL 0x3A bit18 = 0;
IA32_MISC_PACKAGE_CTLS 0xBC bit0 = 0). Same harness as the filtered run
(pwmtraces.py, IDX_LIST=[0], 1e6 traces, M=100). True key = ram1[0] = 124.

This is the counterpart to ../fresh_reproduction_index0_SGXon_filtered/
(the SGX-enabled / filtered run that the rest of the response uses).

Files:
  ntt_traces_index0_SGXoff_unfiltered.csv  — 1e6 unfiltered traces (b, energy)
  filtered_vs_unfiltered_rank.csv          — rank-vs-traces, unfiltered vs filtered
  cpa_fast.py                              — value-model CPA used for both curves

Result (value model H = (k*b) mod q): unfiltered reaches the rank-25 success
threshold at ~2e5 traces vs ~5e5 for filtered (~2.5x fewer); both plateau in the
low-teens. Filtering raises the trace cost but does not prevent recovery.
See figures/kyber_filtered_vs_unfiltered.png.
