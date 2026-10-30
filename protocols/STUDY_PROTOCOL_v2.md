# Study protocol v2 — predicate focus with a size ladder (10 October 2026)

Version 2 replaces v1 for all new runs. `STUDY_PROTOCOL.md` (v1) stays unchanged as the record of what was planned first. Everything in v1 still applies unless this file changes it.

## Why it changed

Radin's research question is how QAOA's feasibility changes as bays grow, not only how one encoding behaves on small bays. On 10 October 2026 Radin decided:

- **Predicate QAOA is the single method used in every experiment**: angle transfer, noise and hardware.
- **QUBO is kept only as a resource comparison.** No QUBO simulation or hardware run.
- **Hybrid is dropped from experiments.** Its resource counts stay for an appendix.

## The three parts of the study

1. **Size and encoding after routing (done; no QPU).** QUBO, hybrid and predicate p=2 circuits for all 15 bays were compiled for FakeFez (optimisation level 3, seed 11). Results: `prep/encoding_resource_survey_FakeFez.json` and `.png`. These are resource counts, not runs. The QUBO and hybrid circuits were not checked against the baseline here, because they are not run.
2. **A predicate size ladder (local runs done; hardware pending).** Five bays of increasing compiled size on FakeFez, seed 11:

| Role | Bay | Qubits | Compiled two-qubit gates |
|---|---|---|---|
| Pilot | random-S3T4C6-21 | 8 | 158 |
| Ladder | random-S3T4C6-24 | 8 | 188 |
| Ladder | random-S3T4C7-32 | 9 | 237 |
| Ladder | random-S4T3C6-16 | 8 | 276 |
| Beyond the 400-gate limit | data3-3-8 | 12 | 418 |

   The beyond-limit bay was chosen by a rule declared before its noisy simulation (`config/selection_rule_v2.json`): the predicate bay with the smallest compiled size above 400.
3. **The main analysis plot:** the gain over matched random guessing (accepted rate ÷ uniform accepted rate, and the same for replay-optimal plans), plotted against compiled two-qubit gate count, for the ideal, noisy-simulation and hardware arms.

## What stays the same as v1

The circuit checks A–C, the frozen leave-one-out angles, and the 5 jobs × 2,000 shots per arm. Also: no mitigation in the primary run, the pilot goes first, no automatic resubmission, approval is required before any QPU job, and the known optimum is used only for scoring.

## Hardware stopping rule added in v2

The ladder runs in order of size. If a bay's hardware accepted-plan rate is not above its matched uniform control (the 95% intervals overlap), the next larger bays are **still run**. This keeps the size curve complete and avoids stopping on a result, and the cost is small.

## Budget

25 jobs in total (5 bays × 5 jobs). Estimated 50–125 s of QPU time, with caps of 30 s per job and 300 s overall (`config/usage_estimate_v2.json`).
