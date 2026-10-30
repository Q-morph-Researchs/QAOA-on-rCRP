# Results: classical companion study for the rCRP IBM QAOA experiment

Package: `QAOA_Classical_Companion_2026_10_16_v1` (16 Oct 2026). The completed IBM study was read, never changed.
Every number below comes from a saved file in this package. "Optimal" always means the relocation count proven by the new MILP in part A.

## Verdicts

| Part | Verdict | Evidence |
|---|---|---|
| A. Independent MILP | **PASS.** HiGHS proves the optimum on all 5 bays: 1, 2, 1, 2, 2. All 5 match the claimed optima. Every MILP solution was rebuilt into moves that replay legally with exactly that many relocations. | `A_milp/A_summary.json`, `A_milp/<bay>__plain.json` |
| B. Greedy rerun | **PASS.** The fixed greedy rule produced legal plans with the optimal count on all 5 bays. | `B_greedy/B_summary.json`, `B_greedy/<bay>.json` |
| C. Matched SA | **Done.** 39 of 40 runs ended with an optimal legal plan. The miss was one QUBO run on random-S3T4C7-32 (seed 1), which found 2 relocations where 1 is optimal. | `C_sa/C_summary.json`, `C_sa/runs/`, `C_sa/traces/` |
| D. Calibration bridge | **PASS, with one correction to the brief.** All 40 jobs match their angle record, circuit files, compiled circuit and raw results, and the recomputed rates equal `summary.csv`. The correction: only 13 of the 40 jobs used `v3` prep files. Jobs 01–26 used `v1` and job 27 used `v2`. The angles are identical in every version. | `D_calibration/CALIBRATION_BRIDGE.md`, `D_calibration/calibration_bridge.json` |
| E. Reproducibility | **PASS.** All 12 unit tests pass. A clean rerun in a fresh folder gave byte-identical results (7 of 7 fingerprints match). Input hashes, environment and logs are saved. | `TEST_LEDGER.md`, `logs/`, `INPUT_HASHES.sha256` |

## A. Independent exact MILP (Galle et al. 2018 CRP-I, SciPy 1.18.1 / HiGHS 1.12.0)

This is new code. It does not import any QAOA file. The solver was given no incumbent, no bound and no known optimum, and the MIP gap was set to 0.

| Bay | Variables | Constraints (plain / with preprocessing) | MILP objective | Dual bound | Gap | Nodes | Runtime (s) | Replay of rebuilt plan | Own exact BFS | Claimed | Match |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---|
| random-S3T4C6-21 | 142 | 578 / 651 | 1 | 1 | 0 | 0 | 0.006 | legal, 1 reloc. | 1 | 1 | yes |
| random-S3T4C6-24 | 142 | 578 / 651 | 2 | 2 | 0 | 0 | 0.002 | legal, 2 reloc. | 2 | 2 | yes |
| random-S3T4C7-32 | 212 | 963 / 1,088 | 1 | 1 | 0 | 0 | 0.003 | legal, 1 reloc. | 1 | 1 | yes |
| random-S4T3C6-16 | 140 | 584 / 653 | 2 | 2 | 0 | 0 | 0.002 | legal, 2 reloc. | 2 | 2 | yes |
| data3-3-8 | 408 | 2,152 / 2,424 | 2 | 2 | 0 | 0 | 0.005 | legal, 2 reloc. | 2 | 2 | yes |

- The data3-3-8 model has 408 variables, the same number Galle's own results file reports for this benchmark class (`Results/3-3_Results.csv`). Galle's file also lists optimum 2 for this instance.
- The plain model and the model with Galle's optional preprocessing give the same objective on every bay.
- Nodes = 0 means HiGHS proved optimality at the root. These bays are very easy for an exact solver.

## B. Deterministic greedy

The rule and tie-break were fixed before the run. They are written at the top of `code/greedy.py` and in every `B_greedy/<bay>.json`:

- Retrieve the target if it is on top.
- Otherwise move the top blocker to a "safe" stack (empty, or holding only larger numbers), choosing the one with the lowest smallest number.
- If no safe stack exists, choose the stack with the highest smallest number.
- Ties go to the lowest stack index.

The rule was checked against the optimum only after all plans existed.

| Bay | Greedy relocations | Moves | Replay | MILP optimum | Gap |
|---|---:|---:|---|---:|---:|
| random-S3T4C6-21 | 1 | 7 | legal | 1 | 0 |
| random-S3T4C6-24 | 2 | 8 | legal | 2 | 0 |
| random-S3T4C7-32 | 1 | 8 | legal | 1 | 0 |
| random-S4T3C6-16 | 2 | 8 | legal | 2 | 0 |
| data3-3-8 | 2 | 11 | legal | 2 | 0 |

The greedy rule took about 6–9 microseconds per bay (mean over 1,000 identical calls).

## C. Matched simulated annealing (new protocol, not the old 40,960-evaluation SA)

The protocol was written and hashed before any run: `C_sa/PROTOCOL_PREREGISTERED.json`, SHA-256 `8d92846b…e7ed`.

- **Search space.** For each hardware pairing, SA works on the exact n-bit register that was measured on IBM, with that pairing's own energy divided by its energy scale.
- **Moves.** Single-bit flips with Metropolis acceptance.
- **Temperature.** A fixed geometric schedule from T = 1.0 down to 0.01.
- **Seeds and budget.** Seeds 0–4 with numpy PCG64. Each seed evaluates exactly 2,000 candidates: 1 initial state plus 1,999 proposals.
- **Selection.** The selected plan is the legal candidate with the fewest replayed relocations, the same rule the QAOA study used for shots.

| Bay | Encoding | Bits | Runs optimal (of 5) | Selected relocations by seed | Legal candidates (of 10,000) | Legal + optimal candidates | IBM legal shots | IBM optimal shots |
|---|---|---:|---:|---|---:|---:|---:|---:|
| random-S3T4C6-21 | predicate | 8 | 5 | 1,1,1,1,1 | 27.98% | 7.93% | 13.68% | 3.54% |
| random-S3T4C6-21 | QUBO | 12 | 5 | 1,1,1,1,1 | 43.03% | 25.99% | 15.68% | 6.28% |
| random-S3T4C6-24 | QUBO | 12 | 5 | 2,2,2,2,2 | 13.58% | 5.19% | 4.70% | 0.69% |
| random-S3T4C6-24 | predicate | 8 | 5 | 2,2,2,2,2 | 16.45% | 5.10% | 3.75% | 1.11% |
| random-S3T4C7-32 | predicate | 9 | 5 | 1,1,1,1,1 | 25.74% | 10.48% | 3.91% | 0.68% |
| random-S3T4C7-32 | QUBO | 15 | **4** | 1,**2**,1,1,1 | 29.97% | 13.63% | 3.87% | 1.73% |
| random-S4T3C6-16 | predicate | 8 | 5 | 2,2,2,2,2 | 21.64% | 20.80% | 8.15% | 7.27% |
| data3-3-8 | predicate | 12 | 5 | 2,2,2,2,2 | 21.22% | 7.53% | 1.16% | 0.34% |
| **All** | | | **39 / 40** | | | | | |

How to read this table:

- **The budgets are matched by count only.** "2,000 SA evaluations" and "2,000 QAOA shots" are the same number of candidates. They are not the same physical or computational cost.
- **SA samples are not independent.** SA candidates form a correlated Markov chain, while IBM shots are independent samples. The per-candidate fractions describe where SA spent its budget. They are not a like-for-like sampling rate.
- **What the table does show.** On these small bays, a plain classical SA with the same candidate count found optimal plans in 39 of 40 runs, and its candidates were legal or optimal more often than the IBM shots. This is a statement about this budget on these bays only. It is not a general ranking.
- **Decoder check.** Every SA candidate was decoded with the hardware study's decoder and double-checked against this package's own CRP-I constraint rows and its own replay. All 80,000 checks agreed.

## D. Calibration bridge (summary; full table in `D_calibration/CALIBRATION_BRIDGE.md`)

| Bay | Encoding | Angle ID | Calibration-record hash (first 16) | Prep versions used | Compiled 2-qubit gates | Legal (recomputed) | Optimal (recomputed) |
|---|---|---|---|---|---:|---:|---:|
| random-S3T4C6-21 | predicate | loo:random-S3T4C6-21:p2 | 7141ca750658e92f | v1 ×5 | 158 | 13.68% | 3.54% |
| random-S3T4C6-21 | QUBO | fresh:galle:p2 | af42ad798424230e | v1 ×5 | 228 | 15.68% | 6.28% |
| random-S3T4C6-24 | QUBO | fresh:galle:p2 | af42ad798424230e | v1 ×5 | 235 | 4.70% | 0.69% |
| random-S3T4C6-24 | predicate | loo:random-S3T4C6-24:p2 | cdf70d7b47420638 | v1 ×5 | 188 | 3.75% | 1.11% |
| random-S3T4C7-32 | predicate | loo:random-S3T4C7-32:p2 | 2b223e34af6896d7 | v1 ×5 | 237 | 3.91% | 0.68% |
| random-S3T4C7-32 | QUBO | fresh:galle:p2 | af42ad798424230e | v1, v2, v3×3 | 372 | 3.87% | 1.73% |
| random-S4T3C6-16 | predicate | loo:random-S4T3C6-16:p2 | 7be4dee9213019a6 | v3 ×5 | 276 | 8.15% | 7.27% |
| data3-3-8 | predicate | loo:data3-3-8:p2 | 78cbcdb5264b2dc5 | v3 ×5 | 418 | 1.16% | 0.34% |

What was checked for each of the 40 jobs:

- **Angles.** The job's angles exactly equal the angles.json record (float equality).
- **Files.** The logical, compiled and check files have the hashes the job record names.
- **Circuits.** Both saved circuits reproduce this package's own p = 2 QAOA output distribution at those angles. The worst difference was 7.7 × 10⁻¹⁶. Moving every angle by 0.01 rad changes the distribution by 1.3 × 10⁻⁴ to 2.6 × 10⁻³, so this test can tell different angles apart.
- **Raw data.** The raw counts equal the saved shots.
- **Rates.** Re-decoding every shot gives exactly the registry and `summary.csv` legal and optimal counts.

Run settings confirmed from the records: no error mitigation, 2,000 shots per job, and a total of 120.0 QPU seconds.

The brief's compiled gate table matches every version. Two things were also checked:

- **QUBO angles.** The `fresh:galle:p2` record hash equals the `angle_hash` in the selection-provenance file.
- **Leave-one-out angles.** Each predicate LOO record excludes its own bay from training.

## What these results do and do not support

- **Supported.** The five IBM bays' optima (1, 2, 1, 2, 2) are now confirmed by an independent MILP solver and by a separate exact search. A simple greedy rule and a matched-count SA both reach these optima, the SA in 39 of 40 runs. The IBM results file set is internally consistent with its calibration records and circuits.
- **Not supported, and not claimed:**
  - quantum advantage;
  - QAOA beating greedy, SA, MILP or exact search, which it does not on these bays;
  - hardware scalability to 12–20 containers;
  - a causal comparison between the QUBO and predicate encodings. They used different angle policies: a common fresh vector versus instance-specific leave-one-out angles.
