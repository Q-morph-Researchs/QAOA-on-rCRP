# Data collection and quantitative analysis

## 1. What was collected, how, and why

This is an empirical small-instance hardware study, with a separate classical companion. The population directly described is the five selected bays and eight tested encoding/bay combinations. These bays are not a random or representative sample of all port layouts. Four were generated within the project and one is a published benchmark. Do not describe all five as published benchmarks or generalize the findings to industrial bays.

For each combination, the recorded protocol specified five IBM jobs with 2,000 measurements (shots) each. The study therefore contains 40 jobs and 80,000 measured bit strings. Circuit depth was p=2, with angles fixed within each combination. This tests repeated execution of a frozen circuit; it does not measure a hardware optimization loop. The predicate and QUBO angle-selection procedures differ.

The pipeline was: define bay and encoding; select and freeze angles; build logical circuit; compile for ibm_fez; perform circuit identity checks; submit the planned job; retrieve IBM results; save measurement arrays, histograms, job receipts and accounting; decode the measurements; replay candidate plans; compare relocation counts with the stored optimum for scoring only.

The collection techniques serve distinct purposes:

| Technique | Why use it? | Evidence collected |
|---|---|---|
| Repeated jobs | Reveal run-to-run variation that a single pooled histogram hides | Five separately identified jobs per combination |
| Fixed shots and frozen settings | Make the execution protocol consistent within a combination | 2,000 shots/job, p=2, angles, options and source hashes |
| Raw measurement preservation | Allow independent recounting and alternative analysis | Ordered saved state arrays and bit-string histograms |
| Preparation versioning | Link each hardware job to the circuit it actually used | Per-job version, theta, logical/compiled files and hashes |
| Legal-plan replay | Test whether a decoded bit string corresponds to a valid physical solution | Move sequences, legality and relocation counts |
| Exact classical confirmation | Establish a scoring reference for optimality | Companion MILP, exact search and replay evidence |
| Complete accounting | Avoid retaining only strong outcomes | All 40 planned completed attempts, including zero-optimum jobs; QPU charge |
| Independent remote check | Confirm local records agree with IBM's retained job data | Corrected release: 40 matching remote circuits, backends, shot counts and histograms |

The first qualifying completed result was retained according to the study's attempt rule. There were no replacement attempts in the completed 40-job set. Optima must be described as evaluation references, not optimization targets supplied to answer selection or stopping. Hashes establish file consistency; they alone do not prove when a protocol was created or that no earlier tuning occurred.

Execution occurred across several days and preparation versions. Jobs 1-26 used v1, job 27 used v2, and jobs 28-40 used v3. The original order was grouped rather than a randomized, interleaved hardware trial. Device drift, execution date, layout and angle policy can confound differences between encodings. These are design limits, not database errors.

No new QPU measurements were collected for this database. Its analyses were specified after the outcomes were known and must be labelled post-hoc/descriptive. For a future confirmatory study, freeze the analysis before submission, select bays under an explicit rule, randomize/interleave execution where feasible, preserve backend calibration snapshots, and predefine retry and cost rules.

## 2. Recommended quantitative measures

Use the encoding/bay combination as the main reporting unit. Show all five job-level points beside the pooled rate. Keep the five bays separate; 80,000 shots are not 80,000 independently sampled problems.

### Primary: success of a complete 2,000-shot run

Run success = 1 if at least one legal optimal plan occurs, otherwise 0. Report successful jobs/5 for each combination, plus a Wilson 95% interval. This matches the practical question: did the run find an optimum within its budget? Five runs give very imprecise estimates: even 5/5 is not proof of 100% future success. Use the same best-feasible selection definition for SA, with the explicit warning that equal candidate counts do not equal cost.

### Secondary: legal and optimal sample rates

- Legal rate = legal shots / all shots.
- Optimal rate = legal optimal shots / all shots.
- Conditional optimal rate = optimal shots / legal shots; undefined if no shot is legal.

The denominator for the main rates includes invalid shots. Reporting only the conditional rate hides failures. Report pooled counts, percentages, Wilson intervals, and each job's rate. Wilson intervals treat observations as Bernoulli trials under an independent, common-probability approximation; they do not cover hardware drift or between-job heterogeneity.

### Variation and uncertainty

The database reports the standard deviation and range of the five job-level optimal rates. An exploratory percentile bootstrap resamples entire jobs within each combination (10,000 resamples; fixed seed 20261016). It does not resample 10,000 individual shots as if these erased batch effects. With only five nonrandomized jobs, the bootstrap is fragile and cannot correct confounding or estimate performance on unseen bays. Present it as a sensitivity analysis, not stronger proof than the design permits.

### Difference from uniform sampling

Report both absolute percentage-point difference and relative lift:

    difference = 100 * (QAOA optimal rate - uniform optimal rate)
    lift = QAOA optimal rate / uniform optimal rate

Lift is undefined when the uniform rate is zero. The stored uniform numbers are matched sampled reference rates from the original summary, not exact probabilities and not uniform sampling over physical move plans. This database imports them as reported aggregate references; it does not establish their random-draw independence or calculate uncertainty for the difference/lift. Before a formal significance test, retrieve the baseline counts/seeds or independently enumerate the encoded state space to establish the exact reference probability. Never infer a statistical difference simply because a ratio exceeds 1.

### Quality and computational resources

For each run, report the best legal relocation count and absolute gap = best count - confirmed optimum. A run without a legal plan must stay a failure with a missing gap, not be dropped or assigned zero. A relative gap may be added when the optimum is nonzero. Avoid calling optimum/result a universal 'accuracy' score: it mixes solution quality with feasibility and can be misleading.

Show decision qubits, compiled two-qubit gates, QAOA depth, shot budget, and QPU charge. Report classical loop/solver times separately with their scopes. Do not divide classical loop time by QPU billing time to claim speedup. Calibration, compilation, energy-table construction, decoding, queues and validation are not equally included in those times.

### Statistical tests and figures

For this small selected sample, prioritize effect sizes, per-job scatter plots, confidence intervals and transparent tables over p-values. Recommended figures: optimal rate versus uniform by combination; five job-level rates ordered by submission date; best-plan success by method; resources versus observed rate labelled exploratory. Do not fit a strong scaling/noise-causality claim from five bays.

If a future formal analysis uses multiple hypothesis tests, predeclare the test family and use a multiplicity correction such as Holm. Permutation tests require exchangeability; the present sequential encoding groups, different angles and nonrandomized dates do not justify arbitrary label permutation. SA's adaptive correlated proposals also should not be analysed as 2,000 independent Bernoulli shots.

## 3. Suggested manuscript wording

We evaluated fixed-angle p=2 QAOA on five selected small restricted container-relocation instances using IBM's ibm_fez processor. Eight instance/encoding combinations were executed in five jobs of 2,000 shots each, yielding 40 jobs and 80,000 measurements. Circuit settings, preparation versions, job identifiers, measured outcomes and QPU charges were retained. Decoded plans were checked for legality and scored against optima corroborated by a separately implemented MILP and exact search. All planned completed jobs were included. The classical companion used a deterministic greedy heuristic and simulated annealing with the same candidate count; this did not equate computational cost. Post-hoc analysis reports per-job success, legal and optimal sample rates, solution gaps and resource use. Uncertainty estimates are conditional on the selected instances and execution protocol; sequential execution and differing angle policies limit causal comparisons between encodings.

## 4. Statistical sources

- NIST, Wilson confidence intervals: https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm
- SciPy, bootstrap methodology and assumptions: https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html
- SciPy, permutation-test null hypotheses: https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.permutation_test.html

These references guide analysis choices; they do not independently validate this dataset or erase its design limits.
