"""Part C: matched simulated-annealing companion study.

Implements C_sa/PROTOCOL_PREREGISTERED.json exactly (the file's SHA-256 is checked
before running). New code; does not reuse or overwrite the old 40,960-evaluation
SA results. The known optimum is not read until every run has been saved.
"""
import csv
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import PACKAGE, PAIRINGS, environment, sha256_file, write_json  # noqa: E402
import sim9_bridge  # noqa: E402

PROTOCOL = PACKAGE / "C_sa" / "PROTOCOL_PREREGISTERED.json"
PROTOCOL_SHA = "8d92846b972e4cc6fdbd7bf4ed02b1ccd5c8653d6432eab90a715a6c1cf3e7ed"
SEEDS = [0, 1, 2, 3, 4]
EVALS = 2000
T0, T1 = 1.0, 0.01


def run_one(P, seed):
    n = P.n
    rng = np.random.Generator(np.random.PCG64(seed))
    init_bits = rng.integers(0, 2, size=n)
    x = int(sum(int(b) << i for i, b in enumerate(init_bits)))
    e = P.energy(x) / P.scale
    trace = [dict(k=0, kind="initial", flip=None, candidate=x, candidate_energy=e, T=None, u=None, dE=None,
                  accepted=True, current=x)]
    t0 = time.perf_counter()
    for k in range(1, EVALS):
        T = T0 * (T1 / T0) ** ((k - 1) / (EVALS - 2))
        flip = int(rng.integers(0, n))
        u = float(rng.random())
        y = x ^ (1 << flip)
        ey = P.energy(y) / P.scale
        dE = ey - e
        acc = dE <= 0 or u < math.exp(-dE / T)
        if acc:
            x, e = y, ey
        trace.append(dict(k=k, kind="proposal", flip=flip, candidate=y, candidate_energy=ey, T=T, u=u, dE=dE,
                          accepted=bool(acc), current=x))
    sa_seconds = time.perf_counter() - t0
    assert len(trace) == EVALS
    # Post-run decoding of every evaluated candidate (no optimum used).
    best = None
    for row in trace:
        o = P.outcome(row["candidate"])
        row["legal"] = o["sim9_legal"]
        row["relocations"] = o["sim9_relocations"] if o["sim9_legal"] else None
        row["own_checks_agree"] = bool(o["legal_agrees_with_own_rows"] and o["relocations_agree_with_own_replay"])
        if o["sim9_legal"] and (best is None or o["sim9_relocations"] < best[1]):
            best = (row["k"], o["sim9_relocations"], o)
    final = P.outcome(x)
    sel = None
    if best is not None:
        o = best[2]
        sel = dict(evaluation_index=best[0], state=o["state"], bitstring_q0_first="".join(str((o["state"] >> i) & 1) for i in range(n)),
                   energy=o["energy"], relocations=o["sim9_relocations"], own_replay_legal=o["own_replay_legal"],
                   own_replay_relocations=o["own_replay_relocations"], moves=o["moves"])
    return dict(seed=seed, rng="numpy PCG64", initial_state=trace[0]["candidate"],
                initial_bits_q0_first="".join(str(int(b)) for b in init_bits), sa_loop_seconds=sa_seconds,
                accepted_proposals=sum(r["accepted"] for r in trace[1:]), evaluations=len(trace),
                final_state=x, final_state_legal=final["sim9_legal"], final_state_relocations=final.get("sim9_relocations"),
                selected=sel, legal_candidates=sum(bool(r["legal"]) for r in trace),
                all_own_checks_agree=all(r["own_checks_agree"] for r in trace)), trace


def main():
    if sha256_file(PROTOCOL) != PROTOCOL_SHA:
        raise SystemExit("protocol file changed after pre-registration; refusing to run")
    out = PACKAGE / "C_sa"; (out / "traces").mkdir(parents=True, exist_ok=True)
    sim_before = sha256_file(sim9_bridge.SIM9_FILE)
    env = environment()
    runs = []
    for case, method in PAIRINGS:
        P = sim9_bridge.Pairing(case, method)
        for seed in SEEDS:
            res, trace = run_one(P, seed)
            res.update(case=case, encoding=method, n_bits=P.n, energy_scale=P.scale)
            name = f"{case}__{method}__seed{seed}"
            with open(out / "traces" / f"{name}.csv", "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(trace[0]))
                w.writeheader(); w.writerows(trace)
            res["trace_file"] = f"traces/{name}.csv"
            write_json(out / "runs" / f"{name}.json", res)
            runs.append(res)
            print("RUN", name, "selected_relocations=", None if res["selected"] is None else res["selected"]["relocations"],
                  "legal_candidates=", res["legal_candidates"], "checks_agree=", res["all_own_checks_agree"], flush=True)
    sim_after = sha256_file(sim9_bridge.SIM9_FILE)
    # ---- scoring, only now reading the independent MILP optimum (part A)
    milp = {r["case"]: r for r in json.loads((PACKAGE / "A_milp" / "A_summary.json").read_text())["rows"]}
    summary = []
    for case, method in PAIRINGS:
        opt = milp[case]["milp_objective"] if milp[case]["optimality_proven"] else None
        rs = [r for r in runs if r["case"] == case and r["encoding"] == method]
        succ = [r["selected"] is not None and r["selected"]["own_replay_legal"] and r["selected"]["own_replay_relocations"] == opt for r in rs]
        legal_c = opt_c = 0
        for r in rs:
            with open(out / r["trace_file"]) as f:
                for row in csv.DictReader(f):
                    if row["legal"] == "True":
                        legal_c += 1
                        opt_c += int(row["relocations"]) == opt
        for r, s in zip(rs, succ):
            r["success_optimal_legal_plan"] = bool(s)
            write_json(out / "runs" / f"{case}__{method}__seed{r['seed']}.json", r)
        summary.append(dict(case=case, encoding=method, n_bits=rs[0]["n_bits"], milp_optimum=opt,
                            runs=len(rs), runs_with_legal_plan=sum(r["selected"] is not None for r in rs),
                            runs_optimal=sum(succ), success_fraction=sum(succ) / len(rs),
                            selected_relocations_by_seed=[None if r["selected"] is None else r["selected"]["relocations"] for r in rs],
                            evaluated_candidates=sum(r["evaluations"] for r in rs),
                            candidate_legal_fraction=legal_c / (EVALS * len(rs)),
                            candidate_legal_optimal_fraction=opt_c / (EVALS * len(rs)),
                            all_independent_checks_agree=all(r["all_own_checks_agree"] for r in rs)))
        print("SUMMARY", json.dumps(summary[-1]), flush=True)
    write_json(out / "C_summary.json", dict(protocol=str(PROTOCOL.name), protocol_sha256=PROTOCOL_SHA, environment=env,
                                            sim9_sha256_before=sim_before, sim9_sha256_after=sim_after, rows=summary))


if __name__ == "__main__":
    main()
