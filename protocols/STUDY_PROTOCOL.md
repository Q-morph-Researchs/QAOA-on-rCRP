# Study protocol — IBM hardware study of the rCRP QAOA solver, v1

Version 1, written 10 October 2026 before any noisy simulation of the study cases and before any QPU job. Changes go into a new versioned file; this one is not edited after hardware data exists.

## Question

How do accepted-plan quality and sampling success change between (1) ideal simulation, (2) a simulation with an IBM device noise model, and (3) the same small rCRP QAOA circuit run on a real IBM quantum processor?

The hardware arm is **"hardware execution with simulation-trained angles"**. It is not hardware-trained QAOA. A real-chip run does not by itself show quantum advantage, scaling, novelty or publication readiness. Poor results are valid results.

## Frozen inputs (not changed by this study)

- Baseline: `QAOA_Quantum_Hardware_revised_2026_10_09_v2`, active manifest SHA-256 `8d0212d4…472068`, verified by every script before it runs.
- Model: predicate encoding, Pauli-Z synthesis, local cutoff 5, built by the baseline's own `Problem`/`ModelAdapter`; its `model_id` must equal the sealed one.
- Circuit: the baseline's own `PredicateModel.circuit(p=2, scale=W, 'pauli')`: Hadamards, then for each layer the phase `exp(-iγE/W)` as CX-ladder/RZ/CX-ladder Pauli-Z terms and an `RX(2β)` mixer, then measurement of the decision register. All 15 study bays have **zero scratch qubits**, so there is no uncomputation step to check on hardware.
- Angles: leave-one-out transferred angles `loo:<bay>:p2` from `release_evidence/calibration/angles.json`, cross-checked against the sealed active copy. No optimiser, no retuning.
- Decoder and scoring: the baseline's `evaluation_table` decoder (certificate + physical replay) and the independent `replay_moves` check on every reported plan.

## Required circuit checks (all must pass before any submission)

- **A.** Gate-level circuit statevector equals the baseline energy-table simulation (`paper_sim.qaoa_probs`): max probability difference ≤ 1e-9. This checks phase sign, mixer, angle order and bit order.
- **B.** Accepted, replay-optimal and energy-ground probabilities recomputed from the gate circuit equal the sealed release values (relative difference ≤ 1e-9).
- **C.** The compiled ISA circuit, reduced to its active physical qubits and read through its measurement map, has the same ideal output distribution as the logical circuit (≤ 1e-9). This checks layout, routing, basis translation and measurement mapping. It is repeated on the **live** target on the day of the run (`src/compile_live.py`); a failure blocks submission.

## Compilation

- Fake devices (offline snapshots): FakeFez (Heron r2, 156 qubits) and FakeTorino (Heron r1, 133 qubits).
- `generate_preset_pass_manager(optimization_level=3, seed_transpiler=s)` for s = 11, 12, 13. **Seed 11 is the primary circuit that is run.** Seeds 12 and 13 are recorded only to show how much compilation alone varies; they are not run, so there is no seed cherry-picking.
- Recorded: physical qubit layout, depth, two-qubit depth, two-qubit and one-qubit gate counts, all operation counts, compile time.

## Case selection

Declared in `config/selection_rule.json` (hashed in `ledger/events.jsonl` before any compilation): practicality threshold of ≤ 400 compiled two-qubit gates (FakeFez, median of the three seeds); the pilot is the smallest candidate; up to three further study bays span the uniform replay-optimal probability (lowest, median, highest). No noisy or hardware success rate is used.

## Arms and shot plan

For each selected bay, five arms, all with the same frozen angles and the same scoring:

| Arm | What it is | Data kind |
|---|---|---|
| `ideal_logical` | samples from the exact ideal distribution | simulation |
| `ideal_isa` | compiled circuit through the local Runtime `SamplerV2` on a noiseless Aer simulator (tests the submission code path) | simulation |
| `noisy_fake` | compiled circuit through local `SamplerV2` on FakeFez (snapshot noise model) | simulation |
| `uniform` | matched-budget uniform random bitstrings | classical control |
| `hardware` | compiled-for-live-target circuit on a real IBM QPU | **hardware** (pending approval) |

**Shot plan: 5 batches × 2,000 shots = 10,000 shots per arm per bay.** Each batch is a separate job, so between-batch variation can be measured; shots inside one job are not treated as independent experiments.

Precision target: the 95% interval half-width for the pooled accepted-plan rate should be ≤ 0.01 (absolute). With rates near 0.2, 10,000 shots give about ±0.008 from shot noise alone; the between-batch standard error is reported separately and may be larger on hardware. This lets us tell a hardware accepted rate apart from uniform guessing (about 0.05 on the pilot) and from the ideal rate (about 0.26 on the pilot) if the true differences are larger than about 0.02.

Mitigation: **none** for the primary run (dynamical decoupling off, gate and measurement twirling off, no readout correction). Any mitigated run is a separate, declared, extra-cost arm.

Random streams: every new local batch uses a recorded PCG64 seed derived from SHA-256 of (arm, bay, label, batch). Old baseline streams are not reused.

## Outcomes reported (kept separate)

- accepted (decoded, physically replayed, complete) plan rate, with 95% Wilson interval;
- replay-optimal plan rate (known optimum used **only** here, after sampling);
- best and median relocation counts among accepted plans;
- certificate-feasible count, energy-ground count, mean penalised energy;
- the reported plan (legal sample with the fewest replayed relocations), its independent replay, and whether a batch had no valid plan;
- between-batch mean, SD and SE.

Failed batches and no-valid-plan batches stay in the results. Anything averaged over successful batches only is labelled as conditional.

## Costs recorded separately

Planned shots, executed shots, pilot cost, failed/cancelled job cost, mitigation overhead (none planned), local simulator work, compilation time, preprocessing (energy table, used only for scoring), and IBM-reported QPU usage per job. Equal shot counts do not mean equal run time.

## Hardware stopping rules

- Run the pilot first (one bay, 5 jobs). Inspect only pipeline health (jobs completed, bit width, parsing, replay), not whether it "looks good", before running the study bays.
- Jobs run serially in a Batch. No automatic resubmission. A job with an uncertain outcome is retrieved by its saved job id, never resubmitted as a new experiment. A genuinely failed job is recorded with its cost and replaced once, labelled as a replacement.
- Stop if the approved QPU-time budget would be exceeded.

## Interpretation limits

A device noise model omits some real errors (for example drift, crosstalk and leakage), so noisy-simulation results are expected to look better than hardware. A gap between arms does not by itself identify a physical cause. The comparison to the old 40,960-sample baseline is not like-for-like; matched 10,000-shot uniform controls are the fair comparison here.
