# Calibration bridge: IBM jobs to angles, circuits and results

**Verdict: ALL CHECKS PASS** (40 jobs, 8 pairings, tolerance 1e-09).

`study/` below means `/Users/radin/Downloads/QAOA_Sim9_2_IBM_Repaired_2026_10_12/studies/ibm_live_guide_1`. Machine-readable version: `calibration_bridge.json`. The IBM instance CRN and account name are deliberately not copied here.

## Source files

| File | SHA-256 |
|---|---|
| `/Users/radin/Downloads/QAOA_Quantum_Hardware_revised_2026_10_09_v2/release_evidence/calibration/angles.json` | `2aa449cd3e22ca36f932e93f40d47ad653a1d49a8cf957bbf10f773178529ac9` |
| `/Users/radin/Downloads/QAOA_Quantum_Hardware_revised_2026_10_09_v2/release_evidence/calibration_checks/calibration_selection_provenance.json` | `79f741b1e5b381c85f68d15989ee49b18e6cfc0a1fd50102e39bbb5e1a685a3f` |
| `/Users/radin/Downloads/QAOA_Quantum_Hardware_revised_2026_10_09_v2/release_evidence/calibration_checks/calibration_ledger.json` | `c1239d74b1f3bf449a814403099aaa9ba9b4bcc591eadf2d6f06e15b0d12858f` |
| `/Users/radin/Downloads/QAOA_Sim9_2_IBM_Repaired_2026_10_12/Sim9_2.py` | `bbd2c4473ac4540d8770d02191e505dd6c204dda4f3bac7a6085dc14b9a6dec0` |
| `/Users/radin/Downloads/QAOA_Sim9_2_IBM_Repaired_2026_10_12/studies/ibm_live_guide_1/summary.csv` | `e460821d86ab03e138912f89fce39c83674bf3121aeedecc9a18790af5e439fd` |
| `/Users/radin/Downloads/QAOA_Sim9_2_IBM_Repaired_2026_10_12/studies/ibm_live_guide_1/study.json` | `c0f9122be5ed9d53fdfe8811e36a27a811351aa63f8f1a7dad073aee0106cec8` |

Sim9_2.py hash unchanged during the audit: True.

## Important correction to the brief

The brief says the angles used are stored in `prep/<case>__<method>/v3/prep.json`. That is only true for 13 of 40 jobs. Each job's registry record names the prep version it actually used: jobs 01-26 used **v1** (prepared 12 Oct), job 27 used **v2** (14 Oct) and jobs 28-40 used **v3** (16 Oct). The angle vector and the compiled two-qubit gate count are identical in v1, v2 and v3 for every pairing, but the compiled circuit files (and their hashes) differ, so the bridge below follows each job to its own version.

## Pairings

### random-S3T4C6-21 / predicate

- Logical qubits: 8; independent MILP optimum: 1 relocations
- Angle ID: `loo:random-S3T4C6-21:p2`; vector `[gamma_1, gamma_2, beta_1, beta_2]` = `[0.18047204389825558, 0.3402714873349897, -0.5522082029399951, -0.2607101873221711]`
- Angle source: `/Users/radin/Downloads/QAOA_Quantum_Hardware_revised_2026_10_09_v2/release_evidence/calibration/angles.json` (file SHA-256 `2aa449cd3e22ca36f932e93f40d47ad653a1d49a8cf957bbf10f773178529ac9`)
- Calibration-record hash (canonical JSON of the entry): `7141ca750658e92f00be5f28311bd739027ba83a7823a685128b23361f92dcbd`
- Selection: componentwise median, simultaneous sign canonicalization on gamma0; rounding: none; historical full precision
- Prep versions used by the 5 jobs: [1] (on disk: [1, 2, 3]); compiled two-qubit gates: {'1': 158}
- Pairing checks: angles_json_sha_equals_sha_embedded_in_Sim9_2 = True, calibration_vector_equals_Sim9_2_embedded_vector = True, predicate_LOO_excludes_own_bay = True, five_jobs = True, recomputed_rates_equal_summary_csv = True, all_job_checks_pass = True
- Final rates over 10,000 shots, recomputed from `states.npy`: legal **13.68%**, optimal **3.54%** (summary.csv: 13.68% / 3.54%; uniform random in summary.csv: 4.13% / 1.25%)

| Job | IBM job ID | Prep | Logical circuit SHA-256 (first 16) | Compiled ISA SHA-256 (first 16) | Raw result SHA-256 (first 16) | Legal / optimal (recomputed = registry) | Max diff ISA vs own QAOA | All checks |
|---|---|---|---|---|---|---|---|---|
| 01 rep1 | `db6hn1qmb58s738brlqg` | v1 | `0ba0dbfeca2adf1b` | `ab6afd9b3061ead4` | `49ce91f78f48ffd7` | 290/74 = 290/74 | 4.9e-16 | PASS |
| 02 rep2 | `db6hqgg4qg6s73c4r2o0` | v1 | `0ba0dbfeca2adf1b` | `ab6afd9b3061ead4` | `3a88cb08219cd504` | 272/83 = 272/83 | 4.9e-16 | PASS |
| 03 rep3 | `db6ht1imb58s738bru1g` | v1 | `0ba0dbfeca2adf1b` | `ab6afd9b3061ead4` | `008c6bd68a9e6a17` | 256/73 = 256/73 | 4.9e-16 | PASS |
| 04 rep4 | `db6hus04qg6s73c4r9o0` | v1 | `0ba0dbfeca2adf1b` | `ab6afd9b3061ead4` | `82026679ba492fff` | 270/62 = 270/62 | 4.9e-16 | PASS |
| 05 rep5 | `db6i302mb58s738bs8kg` | v1 | `0ba0dbfeca2adf1b` | `ab6afd9b3061ead4` | `62548ca530f8c89e` | 280/62 = 280/62 | 4.9e-16 | PASS |

### random-S3T4C6-21 / QUBO (Galle CRP-I)

- Logical qubits: 12; independent MILP optimum: 1 relocations
- Angle ID: `fresh:galle:p2`; vector `[gamma_1, gamma_2, beta_1, beta_2]` = `[0.647, -2.595, -0.409, 0.211]`
- Angle source: `/Users/radin/Downloads/QAOA_Quantum_Hardware_revised_2026_10_09_v2/release_evidence/calibration/angles.json` (file SHA-256 `2aa449cd3e22ca36f932e93f40d47ad653a1d49a8cf957bbf10f773178529ac9`)
- Calibration-record hash (canonical JSON of the entry): `af42ad798424230eca8db833783b3ed7f60640588315e95656633d1d06cb0577`; equals selection-provenance `angle_hash`: True
- Selection: maximum mean log legal amplification among 8 wrapped candidates plus median; validate separately; rounding: 3 decimal places; preserved historical evaluated vector
- Prep versions used by the 5 jobs: [1] (on disk: [1, 2, 3]); compiled two-qubit gates: {'1': 228}
- Pairing checks: provenance_angle_hash_equals_record_hash = True, angles_json_sha_equals_sha_embedded_in_Sim9_2 = True, calibration_vector_equals_Sim9_2_embedded_vector = True, five_jobs = True, recomputed_rates_equal_summary_csv = True, all_job_checks_pass = True
- Final rates over 10,000 shots, recomputed from `states.npy`: legal **15.68%**, optimal **6.28%** (summary.csv: 15.68% / 6.28%; uniform random in summary.csv: 4.98% / 1.50%)

| Job | IBM job ID | Prep | Logical circuit SHA-256 (first 16) | Compiled ISA SHA-256 (first 16) | Raw result SHA-256 (first 16) | Legal / optimal (recomputed = registry) | Max diff ISA vs own QAOA | All checks |
|---|---|---|---|---|---|---|---|---|
| 06 rep1 | `db6i8bcvf2bc73d19mlg` | v1 | `2e622e6a27b754ea` | `d23d2895ae21aa41` | `df2687c223be7a3e` | 322/134 = 322/134 | 1.3e-16 | PASS |
| 07 rep2 | `db6i9fqmb58s738bsi10` | v1 | `2e622e6a27b754ea` | `d23d2895ae21aa41` | `b5890aad53f0a5e6` | 309/109 = 309/109 | 1.3e-16 | PASS |
| 08 rep3 | `db6ibe04qg6s73c4rur0` | v1 | `2e622e6a27b754ea` | `d23d2895ae21aa41` | `45fc761fc2408883` | 314/138 = 314/138 | 1.3e-16 | PASS |
| 09 rep4 | `db6iddslf4us73c5eb3g` | v1 | `2e622e6a27b754ea` | `d23d2895ae21aa41` | `646c9a5956c41cc7` | 320/126 = 320/126 | 1.3e-16 | PASS |
| 10 rep5 | `db6ier2mb58s738bsq60` | v1 | `2e622e6a27b754ea` | `d23d2895ae21aa41` | `b77b7c947d1ddd3a` | 303/121 = 303/121 | 1.3e-16 | PASS |

### random-S3T4C6-24 / QUBO (Galle CRP-I)

- Logical qubits: 12; independent MILP optimum: 2 relocations
- Angle ID: `fresh:galle:p2`; vector `[gamma_1, gamma_2, beta_1, beta_2]` = `[0.647, -2.595, -0.409, 0.211]`
- Angle source: `/Users/radin/Downloads/QAOA_Quantum_Hardware_revised_2026_10_09_v2/release_evidence/calibration/angles.json` (file SHA-256 `2aa449cd3e22ca36f932e93f40d47ad653a1d49a8cf957bbf10f773178529ac9`)
- Calibration-record hash (canonical JSON of the entry): `af42ad798424230eca8db833783b3ed7f60640588315e95656633d1d06cb0577`; equals selection-provenance `angle_hash`: True
- Selection: maximum mean log legal amplification among 8 wrapped candidates plus median; validate separately; rounding: 3 decimal places; preserved historical evaluated vector
- Prep versions used by the 5 jobs: [1] (on disk: [1, 2, 3]); compiled two-qubit gates: {'1': 235}
- Pairing checks: provenance_angle_hash_equals_record_hash = True, angles_json_sha_equals_sha_embedded_in_Sim9_2 = True, calibration_vector_equals_Sim9_2_embedded_vector = True, five_jobs = True, recomputed_rates_equal_summary_csv = True, all_job_checks_pass = True
- Final rates over 10,000 shots, recomputed from `states.npy`: legal **4.70%**, optimal **0.69%** (summary.csv: 4.70% / 0.69%; uniform random in summary.csv: 2.55% / 0.97%)

| Job | IBM job ID | Prep | Logical circuit SHA-256 (first 16) | Compiled ISA SHA-256 (first 16) | Raw result SHA-256 (first 16) | Legal / optimal (recomputed = registry) | Max diff ISA vs own QAOA | All checks |
|---|---|---|---|---|---|---|---|---|
| 11 rep1 | `db6j3804qg6s73c4stn0` | v1 | `bbf557220a3916ca` | `784b8cfafc9985b6` | `7e0a361756ef9dc6` | 103/17 = 103/17 | 2.9e-17 | PASS |
| 12 rep2 | `db6jj7svf2bc73d1bfc0` | v1 | `bbf557220a3916ca` | `784b8cfafc9985b6` | `6539b3ae223c0ca8` | 81/9 = 81/9 | 2.9e-17 | PASS |
| 13 rep3 | `db6jk14lf4us73c5ft0g` | v1 | `bbf557220a3916ca` | `784b8cfafc9985b6` | `1ac82b17259621f1` | 87/13 = 87/13 | 2.9e-17 | PASS |
| 14 rep4 | `db6jl104qg6s73c4tkp0` | v1 | `bbf557220a3916ca` | `784b8cfafc9985b6` | `bec62ff3a760be85` | 100/15 = 100/15 | 2.9e-17 | PASS |
| 15 rep5 | `db6jls2mb58s738bub4g` | v1 | `bbf557220a3916ca` | `784b8cfafc9985b6` | `403061cba6680141` | 99/15 = 99/15 | 2.9e-17 | PASS |

### random-S3T4C6-24 / predicate

- Logical qubits: 8; independent MILP optimum: 2 relocations
- Angle ID: `loo:random-S3T4C6-24:p2`; vector `[gamma_1, gamma_2, beta_1, beta_2]` = `[0.18047204389825558, 0.3402714873349897, -0.5645835545486001, -0.2665598289545603]`
- Angle source: `/Users/radin/Downloads/QAOA_Quantum_Hardware_revised_2026_10_09_v2/release_evidence/calibration/angles.json` (file SHA-256 `2aa449cd3e22ca36f932e93f40d47ad653a1d49a8cf957bbf10f773178529ac9`)
- Calibration-record hash (canonical JSON of the entry): `cdf70d7b474206387dce4717f8dcddcc6ef00192832ee3e1be5ebd508b6af3c5`
- Selection: componentwise median, simultaneous sign canonicalization on gamma0; rounding: none; historical full precision
- Prep versions used by the 5 jobs: [1] (on disk: [1, 2, 3]); compiled two-qubit gates: {'1': 188}
- Pairing checks: angles_json_sha_equals_sha_embedded_in_Sim9_2 = True, calibration_vector_equals_Sim9_2_embedded_vector = True, predicate_LOO_excludes_own_bay = True, five_jobs = True, recomputed_rates_equal_summary_csv = True, all_job_checks_pass = True
- Final rates over 10,000 shots, recomputed from `states.npy`: legal **3.75%**, optimal **1.11%** (summary.csv: 3.75% / 1.11%; uniform random in summary.csv: 2.28% / 0.69%)

| Job | IBM job ID | Prep | Logical circuit SHA-256 (first 16) | Compiled ISA SHA-256 (first 16) | Raw result SHA-256 (first 16) | Legal / optimal (recomputed = registry) | Max diff ISA vs own QAOA | All checks |
|---|---|---|---|---|---|---|---|---|
| 16 rep1 | `db6jngqmb58s738bucv0` | v1 | `2e6245fa9c274a79` | `0bef3b52c7e10d4c` | `459ac2eb2925b513` | 66/19 = 66/19 | 2.8e-16 | PASS |
| 17 rep2 | `db6joi4vf2bc73d1bld0` | v1 | `2e6245fa9c274a79` | `0bef3b52c7e10d4c` | `5ab7a778183a9403` | 81/26 = 81/26 | 2.8e-16 | PASS |
| 18 rep3 | `db6jq284qg6s73c4tqgg` | v1 | `2e6245fa9c274a79` | `0bef3b52c7e10d4c` | `ade042286d04d065` | 81/26 = 81/26 | 2.8e-16 | PASS |
| 19 rep4 | `db6kd1klf4us73c5gpb0` | v1 | `2e6245fa9c274a79` | `0bef3b52c7e10d4c` | `46bfefc8f31499a4` | 70/20 = 70/20 | 2.8e-16 | PASS |
| 20 rep5 | `db6kduslf4us73c5gqdg` | v1 | `2e6245fa9c274a79` | `0bef3b52c7e10d4c` | `d98f4c8965d4b2ae` | 77/20 = 77/20 | 2.8e-16 | PASS |

### random-S3T4C7-32 / predicate

- Logical qubits: 9; independent MILP optimum: 1 relocations
- Angle ID: `loo:random-S3T4C7-32:p2`; vector `[gamma_1, gamma_2, beta_1, beta_2]` = `[0.18047204389825558, 0.3402714873349897, -0.5522082029399951, -0.2665598289545603]`
- Angle source: `/Users/radin/Downloads/QAOA_Quantum_Hardware_revised_2026_10_09_v2/release_evidence/calibration/angles.json` (file SHA-256 `2aa449cd3e22ca36f932e93f40d47ad653a1d49a8cf957bbf10f773178529ac9`)
- Calibration-record hash (canonical JSON of the entry): `2b223e34af6896d7c67a469e25d5cb93d68be660f0553ce53f0ed4e1b5c9eee8`
- Selection: componentwise median, simultaneous sign canonicalization on gamma0; rounding: none; historical full precision
- Prep versions used by the 5 jobs: [1] (on disk: [1, 2, 3]); compiled two-qubit gates: {'1': 237}
- Pairing checks: angles_json_sha_equals_sha_embedded_in_Sim9_2 = True, calibration_vector_equals_Sim9_2_embedded_vector = True, predicate_LOO_excludes_own_bay = True, five_jobs = True, recomputed_rates_equal_summary_csv = True, all_job_checks_pass = True
- Final rates over 10,000 shots, recomputed from `states.npy`: legal **3.91%**, optimal **0.68%** (summary.csv: 3.91% / 0.68%; uniform random in summary.csv: 2.39% / 0.78%)

| Job | IBM job ID | Prep | Logical circuit SHA-256 (first 16) | Compiled ISA SHA-256 (first 16) | Raw result SHA-256 (first 16) | Legal / optimal (recomputed = registry) | Max diff ISA vs own QAOA | All checks |
|---|---|---|---|---|---|---|---|---|
| 21 rep1 | `db6kfbamb58s738bv87g` | v1 | `c3e1bf523eed6a61` | `23eb754ed2d9e564` | `93ce487f273b5741` | 83/11 = 83/11 | 1.5e-16 | PASS |
| 22 rep2 | `db6kgfqmb58s738bv9ag` | v1 | `c3e1bf523eed6a61` | `23eb754ed2d9e564` | `4069fd1f5d16e95b` | 66/12 = 66/12 | 1.5e-16 | PASS |
| 23 rep3 | `db6khlamb58s738bvah0` | v1 | `c3e1bf523eed6a61` | `23eb754ed2d9e564` | `4e7fc20c00f05c52` | 76/11 = 76/11 | 1.5e-16 | PASS |
| 24 rep4 | `db6kic2mb58s738bvb90` | v1 | `c3e1bf523eed6a61` | `23eb754ed2d9e564` | `c59ede252cf10e33` | 82/23 = 82/23 | 1.5e-16 | PASS |
| 25 rep5 | `db6kjfqmb58s738bvcj0` | v1 | `c3e1bf523eed6a61` | `23eb754ed2d9e564` | `027c25987dc4a7a6` | 84/11 = 84/11 | 1.5e-16 | PASS |

### random-S3T4C7-32 / QUBO (Galle CRP-I)

- Logical qubits: 15; independent MILP optimum: 1 relocations
- Angle ID: `fresh:galle:p2`; vector `[gamma_1, gamma_2, beta_1, beta_2]` = `[0.647, -2.595, -0.409, 0.211]`
- Angle source: `/Users/radin/Downloads/QAOA_Quantum_Hardware_revised_2026_10_09_v2/release_evidence/calibration/angles.json` (file SHA-256 `2aa449cd3e22ca36f932e93f40d47ad653a1d49a8cf957bbf10f773178529ac9`)
- Calibration-record hash (canonical JSON of the entry): `af42ad798424230eca8db833783b3ed7f60640588315e95656633d1d06cb0577`; equals selection-provenance `angle_hash`: True
- Selection: maximum mean log legal amplification among 8 wrapped candidates plus median; validate separately; rounding: 3 decimal places; preserved historical evaluated vector
- Prep versions used by the 5 jobs: [1, 2, 3] (on disk: [1, 2, 3]); compiled two-qubit gates: {'1': 372, '2': 372, '3': 372}
- Pairing checks: provenance_angle_hash_equals_record_hash = True, angles_json_sha_equals_sha_embedded_in_Sim9_2 = True, calibration_vector_equals_Sim9_2_embedded_vector = True, five_jobs = True, recomputed_rates_equal_summary_csv = True, all_job_checks_pass = True
- Final rates over 10,000 shots, recomputed from `states.npy`: legal **3.87%**, optimal **1.73%** (summary.csv: 3.87% / 1.73%; uniform random in summary.csv: 2.44% / 0.73%)

| Job | IBM job ID | Prep | Logical circuit SHA-256 (first 16) | Compiled ISA SHA-256 (first 16) | Raw result SHA-256 (first 16) | Legal / optimal (recomputed = registry) | Max diff ISA vs own QAOA | All checks |
|---|---|---|---|---|---|---|---|---|
| 26 rep1 | `db6kkrkvf2bc73d1cl4g` | v1 | `85ad43eb457bc9c5` | `0b91b9321ccee7c5` | `aa7ee9bc5b39c7a5` | 52/22 = 52/22 | 2.7e-17 | PASS |
| 27 rep2 | `db7u1o2raffc73fb9tjg` | v2 | `85ad43eb457bc9c5` | `c2982d71b553bc0b` | `c36add0c3a63246e` | 91/51 = 91/51 | 2.7e-17 | PASS |
| 28 rep3 | `db8ura0b3g5c73eh1ce0` | v3 | `85ad43eb457bc9c5` | `19bd91a35c64271c` | `f70adc16dab95aaf` | 80/35 = 80/35 | 2.4e-17 | PASS |
| 29 rep4 | `db8v4mheukqs73arcge0` | v3 | `85ad43eb457bc9c5` | `19bd91a35c64271c` | `98d951976958e6a0` | 79/31 = 79/31 | 2.4e-17 | PASS |
| 30 rep5 | `db8v5alckpjs73b1otdg` | v3 | `85ad43eb457bc9c5` | `19bd91a35c64271c` | `9c507b7af5dae094` | 85/34 = 85/34 | 2.4e-17 | PASS |

### random-S4T3C6-16 / predicate

- Logical qubits: 8; independent MILP optimum: 2 relocations
- Angle ID: `loo:random-S4T3C6-16:p2`; vector `[gamma_1, gamma_2, beta_1, beta_2]` = `[0.18047204389825558, 0.3421377912084009, -0.5645835545486001, -0.2665598289545603]`
- Angle source: `/Users/radin/Downloads/QAOA_Quantum_Hardware_revised_2026_10_09_v2/release_evidence/calibration/angles.json` (file SHA-256 `2aa449cd3e22ca36f932e93f40d47ad653a1d49a8cf957bbf10f773178529ac9`)
- Calibration-record hash (canonical JSON of the entry): `7be4dee9213019a614f70d9216adcb1beae9744a253b6b671a182c61d9e983ae`
- Selection: componentwise median, simultaneous sign canonicalization on gamma0; rounding: none; historical full precision
- Prep versions used by the 5 jobs: [3] (on disk: [1, 2, 3]); compiled two-qubit gates: {'3': 276}
- Pairing checks: angles_json_sha_equals_sha_embedded_in_Sim9_2 = True, calibration_vector_equals_Sim9_2_embedded_vector = True, predicate_LOO_excludes_own_bay = True, five_jobs = True, recomputed_rates_equal_summary_csv = True, all_job_checks_pass = True
- Final rates over 10,000 shots, recomputed from `states.npy`: legal **8.15%**, optimal **7.27%** (summary.csv: 8.15% / 7.27%; uniform random in summary.csv: 3.93% / 3.10%)

| Job | IBM job ID | Prep | Logical circuit SHA-256 (first 16) | Compiled ISA SHA-256 (first 16) | Raw result SHA-256 (first 16) | Legal / optimal (recomputed = registry) | Max diff ISA vs own QAOA | All checks |
|---|---|---|---|---|---|---|---|---|
| 31 rep1 | `db8v5se94fic73eu5rq0` | v3 | `cb2dcbc60ed91fda` | `b27622f11a052267` | `8484ce9593284d03` | 184/165 = 184/165 | 7.6e-16 | PASS |
| 32 rep2 | `db8v6g8b3g5c73eh200g` | v3 | `cb2dcbc60ed91fda` | `b27622f11a052267` | `aca6c81c38462237` | 167/151 = 167/151 | 7.6e-16 | PASS |
| 33 rep3 | `db8v8k9eukqs73arcm1g` | v3 | `cb2dcbc60ed91fda` | `b27622f11a052267` | `1b8b4997e3cc811c` | 157/143 = 157/143 | 7.6e-16 | PASS |
| 34 rep4 | `db8v9jheukqs73arco8g` | v3 | `cb2dcbc60ed91fda` | `b27622f11a052267` | `d41c8408973c6024` | 155/140 = 155/140 | 7.6e-16 | PASS |
| 35 rep5 | `db8va48b3g5c73eh26d0` | v3 | `cb2dcbc60ed91fda` | `b27622f11a052267` | `d1eaeaef40d8da7f` | 152/128 = 152/128 | 7.6e-16 | PASS |

### data3-3-8 / predicate

- Logical qubits: 12; independent MILP optimum: 2 relocations
- Angle ID: `loo:data3-3-8:p2`; vector `[gamma_1, gamma_2, beta_1, beta_2]` = `[0.1890154920164095, 0.34828050608427163, -0.5522082029399951, -0.2533214357321605]`
- Angle source: `/Users/radin/Downloads/QAOA_Quantum_Hardware_revised_2026_10_09_v2/release_evidence/calibration/angles.json` (file SHA-256 `2aa449cd3e22ca36f932e93f40d47ad653a1d49a8cf957bbf10f773178529ac9`)
- Calibration-record hash (canonical JSON of the entry): `78cbcdb5264b2dc54ea4900da41915b2e09ac1d7d15977ee96e56b37bacfbf15`
- Selection: componentwise median, simultaneous sign canonicalization on gamma0; rounding: none; historical full precision
- Prep versions used by the 5 jobs: [3] (on disk: [1, 2, 3]); compiled two-qubit gates: {'3': 418}
- Pairing checks: angles_json_sha_equals_sha_embedded_in_Sim9_2 = True, calibration_vector_equals_Sim9_2_embedded_vector = True, predicate_LOO_excludes_own_bay = True, five_jobs = True, recomputed_rates_equal_summary_csv = True, all_job_checks_pass = True
- Final rates over 10,000 shots, recomputed from `states.npy`: legal **1.16%**, optimal **0.34%** (summary.csv: 1.16% / 0.34%; uniform random in summary.csv: 0.53% / 0.18%)

| Job | IBM job ID | Prep | Logical circuit SHA-256 (first 16) | Compiled ISA SHA-256 (first 16) | Raw result SHA-256 (first 16) | Legal / optimal (recomputed = registry) | Max diff ISA vs own QAOA | All checks |
|---|---|---|---|---|---|---|---|---|
| 36 rep1 | `db8vcne94fic73eu68t0` | v3 | `20d8f99ba8f2b4c1` | `66eb9446078a4ba5` | `5130e327eedd2354` | 21/8 = 21/8 | 8.5e-17 | PASS |
| 37 rep2 | `db8vd68b3g5c73eh2djg` | v3 | `20d8f99ba8f2b4c1` | `66eb9446078a4ba5` | `50858c571838daf4` | 38/11 = 38/11 | 8.5e-17 | PASS |
| 38 rep3 | `db8vdie94fic73eu6b30` | v3 | `20d8f99ba8f2b4c1` | `66eb9446078a4ba5` | `43c338679d69d6b5` | 13/0 = 13/0 | 8.5e-17 | PASS |
| 39 rep4 | `db8ve6e94fic73eu6cb0` | v3 | `20d8f99ba8f2b4c1` | `66eb9446078a4ba5` | `8510d2521dd86d71` | 23/6 = 23/6 | 8.5e-17 | PASS |
| 40 rep5 | `db8vek8b3g5c73eh2h50` | v3 | `20d8f99ba8f2b4c1` | `66eb9446078a4ba5` | `7ffd11945801b4e8` | 21/9 = 21/9 | 8.5e-17 | PASS |

## What each job check means

- `registry_theta_equals_calibration_vector`, `prep_theta_equals_calibration_vector`: exact float equality of the job's and the prep file's angles with the angles.json record.
- `isa_file_sha_equals_prep_and_registry`, `logical_file_sha_equals_prep`, `check_file_sha_equals_prep`: the circuit files on disk are the ones the job record names.
- `logical_circuit_matches_own_qaoa_at_calibration_angles`, `isa_circuit_matches_own_qaoa_at_calibration_angles`: the ideal output distribution of the saved circuit (compiled ISA circuit simulated on its active qubits) equals this package's own p=2 QAOA statevector at the calibration angles, within 1e-9.
- `perturbed_angles_are_distinguishable`: moving every angle by 0.01 rad changes the distribution by far more than the tolerance, so the match above is meaningful.
- `states_sha_equals_registry`, `raw_counts_equal_states`, `shots_2000`: raw results are intact and consistent.
- `recomputed_legal_equals_registry`, `recomputed_optimal_equals_registry`: every shot was re-decoded; legality was double-checked against this package's own CRP-I rows and own replay; optimal = replayed relocations equal the part-A MILP optimum.
- `isa_identity_confirmed_by_job`: the registry says IBM's returned job input equalled the frozen ISA circuit (recorded at run time; not re-queried, no IBM access used here).
- `no_mitigation`: dynamical decoupling, gate twirling and measurement twirling were off.

## Flags

None.
