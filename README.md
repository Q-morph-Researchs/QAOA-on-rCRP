# Fixed-angle QAOA for small restricted Container Relocation Problems on IBM Quantum hardware

Code, IBM hardware data and results for the study by **Radin Baghbanian** and **Barman Alibeigi** (equal contribution).

> **Paper:** *Fixed-Angle Quantum Approximate Optimization Algorithm (QAOA) for Small Restricted Container Relocation Problems on IBM Quantum Hardware: A Comparison with Random Sampling and Classical Methods.* Submitted to the *Journal of High School Science* (2026).
>
> **This release:** v1.0, https://github.com/Q-morph-Researchs/QAOA-on-rCRP/releases/tag/v1.0

## The study in one paragraph

Five small container bays (6–9 containers) were written as QAOA problems in two exact ways, a QUBO-based encoding and a predicate-based encoding. Eight bay–encoding pairings were run on IBM's 156-qubit `ibm_fez` processor at depth *p* = 2, with angles fixed in advance and no error mitigation: 40 jobs, 80,000 shots. Every shot was decoded into crane moves and checked. QAOA produced legal plans more often than exact uniform random sampling in every job, but an exact MILP model and a greedy rule solved every bay, and simulated annealing beat QAOA on every pairing. The study does **not** claim quantum advantage.

## What's in this repository

| Folder | What's in it |
|---|---|
| [`code/`](code) | All the code: the study program `Sim9_2.py` (encodings, circuits, IBM job handling, decoder), the classical solvers, the simulations, the analysis scripts, the independent decoder check and the post-hoc angle study |
| [`ibm_hardware_data/`](ibm_hardware_data) | The raw results of all 40 IBM jobs (measured counts, shots, job records), the compiled circuits that ran, IBM's calibration snapshots and the frozen angles |
| [`results/`](results) | Every results table, the full results database, the classical, simulation and post-hoc results, and the decoder check |
| [`protocols/`](protocols) | The study protocols and run plan, written on 10 October 2026, before any hardware job |

Every folder has a plain-text `ABOUT_THIS_FOLDER.txt` explaining what's in it and what to open first.

## Where to find each part of the paper

| Paper | File |
|---|---|
| Table 1 (the five bays) | `results/database/instances.csv` |
| Table 3 (circuit resources) | `results/tables/circuit_resources.csv` |
| Table 4, Figures 2–3 (hardware rates) | `results/tables/Summary_by_bay.csv` |
| Table 5 (classical comparison) | `results/classical/RESULTS.md` |
| Table 6, Figure 4 (ideal, noise model, hardware) | `results/tables/ideal_noise_hardware_comparison.csv` |
| Appendix Table A1 (frozen angles) | `ibm_hardware_data/frozen_angles.json`, `results/database/preparations.csv` |
| Appendix Tables A2–A3 (hardware settings, all 40 jobs) | `ibm_hardware_data/`, `results/tables/all_job_rates.csv` |
| Appendix Table A4 (physical qubits, calibrated errors, ESP) | `results/simulation/noise_models/*/audit.json`, `code/analysis/esp.py` |
| Appendix Table A5 (exploratory statistics) | `results/tables/Summary_by_bay.csv` |
| Appendix Table A6 (post-hoc angles and depth) | `results/posthoc/Table_A6.md` |
| Appendix Table A7 (resource estimates, 12–20 containers) | `results/tables/resource_scaling.json` |
| Appendix B.4 (decoder validation) | `results/decoder_check/` |
| Everything in one spreadsheet | `results/tables/rCRP_IBM_Results_Sorted.xlsx` |

## Names used in the files

| In the files | In the paper |
|---|---|
| `random-S3T4C6-21` | Bay A |
| `random-S3T4C6-24` | Bay B |
| `random-S3T4C7-32` | Bay C |
| `random-S4T3C6-16` | Bay D |
| `data3-3-8` | Bay E |
| `galle` | QUBO-based encoding (named after Galle et al.'s model) |
| `predicate` | Predicate-based encoding |
| "accepted" | legal plan |
| "replay-optimal" | optimal plan |
| `v1` / `v2` / `v3` | circuit preparations: jobs 1–26 / job 27 / jobs 28–40 |

## About the code

The scripts are kept exactly as they were run, so some of them still point to folders on our own computers and won't run unchanged on yours. They're here so you can read exactly how every number was produced. The packages we used are in `requirements.txt` (Python 3.12). The IBM account name and instance ID have been removed from the records, and no credentials are included.

## Check that the files are intact

```bash
python3 verify_files.py
```

This checks the SHA-256 hash of every file against `MANIFEST_SHA256.json`.

## License and citation

- **Code** (`.py`): MIT License, see `LICENSE`.
- **Data, results and documents:** CC BY 4.0, see `LICENSE-DATA.md`.

Use GitHub's **"Cite this repository"** button, or cite:

>   Alibeigi B. & Baghbanian R. (2026). *Fixed-angle QAOA for small restricted Container Relocation Problems on IBM Quantum hardware: Code and data* (Version 1.0). GitHub. https://github.com/Q-morph-Researchs/QAOA-on-rCRP/releases/tag/v1.0
