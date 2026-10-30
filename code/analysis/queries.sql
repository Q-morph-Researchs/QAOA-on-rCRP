-- Per-job results in planned order.
SELECT slot,job_id,pairing_id,prep_version,shots,legal_rate,optimal_rate,
       best_relocations,qpu_charge_seconds FROM job_rates ORDER BY slot;

-- Best-plan success per combination.
SELECT pairing_id,COUNT(*) AS jobs,SUM(optimal_count>0) AS successful_jobs,
       SUM(shots) AS shots,SUM(optimal_count) AS optimal_shots
FROM jobs GROUP BY pairing_id ORDER BY pairing_id;

-- Recorded legal move plans; several bit strings may encode the same physical plan.
SELECT pairing_id,bitstring,relocations,moves_json FROM outcomes
WHERE legal=1 ORDER BY pairing_id,relocations,state;

-- Histogram totals must equal shots for each job.
SELECT j.job_id,j.shots,SUM(h.count) AS histogram_total
FROM jobs j JOIN histograms h USING(job_id) GROUP BY j.job_id;

-- Absolute best-plan gap; NULL means no feasible plan and must be reported as failure.
SELECT j.slot,j.pairing_id,j.best_relocations-i.optimum AS absolute_gap
FROM jobs j JOIN pairings p USING(pairing_id) JOIN instances i USING(case_id)
ORDER BY j.slot;
