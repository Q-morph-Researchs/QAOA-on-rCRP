"""Part A: independent implementation of Galle, Barnhart & Jaillet (2018) CRP-I,
solved with scipy.optimize.milp (HiGHS).

Written from the paper's model and the authors' public Julia code
(binaryIPSolver.jl in vgalle/binaryIP_CRP). It does NOT import Sim9_2.py or any
file of the revised QAOA package.

Variables (paper notation):
  a[n,c,d] in {0,1}, n = 1..N, c = n..C+S, d = n..C, with N = C - S + 1.
    For c <= C: a[n,c,d] = 1  <=>  at retrieval stage n, container c lies BELOW d
    in the same stack. For c = C+s: a[n,C+s,d] = 1 <=> d is in stack s.
  b[d] in {0,1}, d = N+1..C: d is blocking in the stage-N configuration
    (Lemma 1: from stage N on, each blocking container costs exactly one relocation).
Objective: sum_{n<N} sum_{d>n} a[n,n,d] + sum_d b[d].

Nothing here reads a known optimum. The solver gets no bound, no incumbent, no
stopping value; the MIP gap is set to zero.
"""
import argparse
import json
import sys
import time
from collections import Counter, OrderedDict
from pathlib import Path

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix, save_npz

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import BAYS, BAY_ORDER, PACKAGE, environment, exact_bfs, replay_report, sha256_file, write_json  # noqa: E402

CATEGORY_TEXT = OrderedDict([
    ("1", "stage-1 variables equal the initial configuration's binary encoding"),
    ("2", "each remaining container is in exactly one stack (n>=2)"),
    ("3", "a container is not below itself (n>=2)"),
    ("4", "c below d and d below c cannot both hold (n>=2)"),
    ("5", "two containers in the same stack are ordered (n>=2)"),
    ("6", "two ordered containers share a stack (n>=2)"),
    ("7", "stack height at most the tier capacity T (n>=2)"),
    ("8", "b[d] = 1 if d is above a higher-priority container at stage N"),
    ("9", "non-relocated container keeps what is below it (upper side)"),
    ("10", "non-relocated container keeps what is below it (lower side)"),
    ("11", "a relocated container leaves its stack"),
    ("12", "two blockers moved in the same stage cannot keep their old order"),
    ("PP", "optional preprocessing: containers fixed until first moved (paper Sec. preprocessing; repo PreProcessingOn)"),
])


def encoding(stacks, C, S):
    """Binary encoding A[(c,d)]: c below d (c<=C) or d in stack s (c=C+s)."""
    A = {}
    for s, stack in enumerate(stacks, 1):
        for k, d in enumerate(stack):
            A[C + s, d] = 1
            for c in stack[:k]:
                A[c, d] = 1
    return A


class CRPI:
    def __init__(self, stacks, T, preprocessing=False):
        self.stacks = [list(s) for s in stacks]
        self.S = S = len(stacks)
        self.C = C = sum(len(s) for s in stacks)
        self.T = T
        if sorted(v for s in stacks for v in s) != list(range(1, C + 1)):
            raise ValueError("containers must be 1..C")
        if C <= S:
            raise ValueError("model needs C > S")
        self.N = N = C - S + 1
        self.names, self.index = [], {}
        for n in range(1, N + 1):
            for c in range(n, C + S + 1):
                for d in range(n, C + 1):
                    self._var(("a", n, c, d))
        for d in range(N + 1, C + 1):
            self._var(("b", d))
        a = lambda n, c, d: self.index["a", n, c, d]
        b = lambda d: self.index["b", d]
        self.cost = np.zeros(len(self.names))
        for n in range(1, N):
            for d in range(n + 1, C + 1):
                self.cost[a(n, n, d)] = 1
        for d in range(N + 1, C + 1):
            self.cost[b(d)] = 1
        self.rows, self.lb, self.ub, self.cat = [], [], [], []
        A0 = encoding(stacks, C, S)
        # (1)
        for c in range(1, C + S + 1):
            for d in range(1, C + 1):
                v = A0.get((c, d), 0)
                self._row("1", {a(1, c, d): 1}, v, v)
        for n in range(2, N + 1):
            for c in range(n, C + 1):
                self._row("2", {a(n, C + s, c): 1 for s in range(1, S + 1)}, 1, 1)   # (2)
                self._row("3", {a(n, c, c): 1}, 0, 0)                                  # (3)
            for c in range(n, C + 1):
                for d in range(n, C + 1):
                    if d == c:
                        continue
                    self._row("4", {a(n, c, d): 1, a(n, d, c): 1}, -np.inf, 1)        # (4)
                    for s in range(1, S + 1):
                        # (5) a_ncd + a_ndc - a_n,C+s,c - a_n,C+s,d >= -1
                        self._row("5", {a(n, c, d): 1, a(n, d, c): 1, a(n, C + s, c): -1, a(n, C + s, d): -1}, -1, np.inf)
                        # (6) a_ncd + a_ndc + a_n,C+s,c + sum_{r!=s} a_n,C+r,d <= 2
                        terms = {a(n, c, d): 1, a(n, d, c): 1, a(n, C + s, c): 1}
                        for r in range(1, S + 1):
                            if r != s:
                                terms[a(n, C + r, d)] = terms.get(a(n, C + r, d), 0) + 1
                        self._row("6", terms, -np.inf, 2)
            for s in range(1, S + 1):
                self._row("7", {a(n, C + s, d): 1 for d in range(n, C + 1)}, -np.inf, T)  # (7)
        for d in range(N + 1, C + 1):
            for c in range(N, d):
                self._row("8", {b(d): 1, a(N, c, d): -1}, 0, np.inf)                    # (8)
        for n in range(1, N):
            for c in range(n + 1, C + 1):
                for d in range(n + 1, C + S + 1):
                    if d == c:
                        continue
                    # (9)  a_{n+1,d,c} - a_{n,d,c} - a_{n,n,c} <= 0
                    self._row("9", {a(n + 1, d, c): 1, a(n, d, c): -1, a(n, n, c): -1}, -np.inf, 0)
                    # (10) a_{n+1,d,c} - a_{n,d,c} + a_{n,n,c} >= 0
                    self._row("10", {a(n + 1, d, c): 1, a(n, d, c): -1, a(n, n, c): 1}, 0, np.inf)
                for s in range(1, S + 1):
                    self._row("11", {a(n, n, c): 1, a(n, C + s, c): 1, a(n + 1, C + s, c): 1}, -np.inf, 2)  # (11)
                for d in range(n + 1, C + 1):
                    if c != d:
                        self._row("12", {a(n, n, c): 1, a(n, n, d): 1, a(n, c, d): 1, a(n + 1, c, d): 1}, -np.inf, 3)  # (12)
        if preprocessing:
            for c in range(1, C + 1):
                first = min(n for n in range(1, C + 1) if n == c or A0.get((n, c), 0))
                for n in range(2, min(first, N) + 1):
                    for d in range(n, C + S + 1):
                        v = A0.get((d, c), 0)
                        self._row("PP", {a(n, d, c): 1}, v, v)

    def _var(self, key):
        self.index[key] = len(self.names)
        self.names.append(key)

    def _row(self, cat, terms, lo, hi):
        self.rows.append({k: v for k, v in terms.items() if v})
        self.lb.append(lo); self.ub.append(hi); self.cat.append(cat)

    def matrix(self):
        r, c, v = [], [], []
        for i, terms in enumerate(self.rows):
            for j, val in terms.items():
                r.append(i); c.append(j); v.append(val)
        return coo_matrix((v, (r, c)), shape=(len(self.rows), len(self.names))).tocsr()

    def name(self, key):
        return f"a[{key[1]},{key[2]},{key[3]}]" if key[0] == "a" else f"b[{key[1]}]"

    def variable_categories(self):
        cnt = Counter()
        for k in self.names:
            if k[0] == "b":
                cnt["b[d]: terminal blocking flag, d=N+1..C"] += 1
            elif k[2] > self.C:
                cnt["a[n,C+s,d]: container d in stack s at stage n"] += 1
            else:
                cnt["a[n,c,d]: container c below container d at stage n"] += 1
        return dict(cnt)

    def check(self, x):
        """Return the categories of violated rows for a 0/1 vector (used by part D too)."""
        bad = Counter()
        for terms, lo, hi, cat in zip(self.rows, self.lb, self.ub, self.cat):
            s = sum(v * x[j] for j, v in terms.items())
            if s < lo - 1e-9 or s > hi + 1e-9:
                bad[cat] += 1
        return dict(bad)

    # ------------------------------------------------------------ reconstruction
    def stage_config(self, x, n):
        C, S = self.C, self.S
        a = lambda c, d: int(round(x[self.index["a", n, c, d]]))
        config = []
        for s in range(1, S + 1):
            members = [d for d in range(n, C + 1) if a(C + s, d)]
            frozen = tuple(members)  # list.sort empties the list while sorting, so count from a copy
            members.sort(key=lambda d: sum(a(c, d) for c in frozen if c != d))
            config.append(members)
        # The reconstructed configuration must re-encode to exactly the stage variables.
        enc = encoding(config, C, S)
        for c in range(n, C + S + 1):
            for d in range(n, C + 1):
                if a(c, d) != enc.get((c, d), 0):
                    raise ValueError(f"stage {n}: variables are not a physical configuration (a[{n},{c},{d}])")
        if sorted(v for s in config for v in s) != list(range(n, C + 1)):
            raise ValueError(f"stage {n}: containers missing or duplicated")
        return config

    def plan(self, x):
        """Rebuild moves from the stage configurations. Raises ValueError if impossible."""
        C, S, N, T = self.C, self.S, self.N, self.T
        stages = [self.stage_config(x, n) for n in range(1, N + 1)]
        if stages[0] != self.stacks:
            raise ValueError("stage 1 does not equal the input bay")
        moves = []
        for n in range(1, N):
            bay = [list(s) for s in stages[n - 1]]
            nxt = stages[n]
            src = next(i for i, s in enumerate(bay) if n in s)
            while bay[src][-1] != n:
                c = bay[src][-1]
                dst = next(i for i, s in enumerate(nxt) if c in s)
                if dst == src:
                    raise ValueError(f"stage {n}: blocker {c} stays in its stack")
                if len(bay[dst]) >= T:
                    raise ValueError(f"stage {n}: destination {dst+1} full")
                bay[dst].append(bay[src].pop())
                moves.append(dict(type="relocate", container=c, source=src + 1, destination=dst + 1))
            bay[src].pop()
            moves.append(dict(type="retrieve", container=n, source=src + 1))
            if bay != nxt:
                raise ValueError(f"stage {n}->{n+1}: replayed configuration differs from the MILP's stage {n+1}")
        # Terminal phase (Lemma 1): S containers left; each blocker is moved once to a
        # stack where it blocks nobody (all containers there have larger numbers or the
        # stack is empty; lowest index first, capacity respected).
        bay = [list(s) for s in stages[-1]]
        target = N
        while any(bay):
            src = next(i for i, s in enumerate(bay) if target in s)
            if bay[src][-1] == target:
                bay[src].pop(); moves.append(dict(type="retrieve", container=target, source=src + 1)); target += 1
                continue
            c = bay[src][-1]
            options = [i for i, s in enumerate(bay) if i != src and len(s) < T and all(v > c for v in s)]
            if not options:
                raise ValueError(f"terminal phase: no non-blocking place for {c}")
            dst = options[0]
            bay[dst].append(bay[src].pop())
            moves.append(dict(type="relocate", container=c, source=src + 1, destination=dst + 1))
        return stages, moves


def solve(case, preprocessing, out_dir, time_limit=600):
    bay = BAYS[case]
    model = CRPI(bay["stacks"], bay["capacity"], preprocessing=preprocessing)
    A = model.matrix()
    tag = "with_preprocessing" if preprocessing else "plain"
    save_npz(out_dir / f"{case}__{tag}__constraint_matrix.npz", A)
    options = dict(disp=True, presolve=True, time_limit=time_limit, mip_rel_gap=0.0)
    print(f"\n===== {case} [{tag}] HiGHS log follows =====", flush=True)
    t0 = time.perf_counter()
    res = milp(c=model.cost, integrality=np.ones(len(model.names)), bounds=Bounds(0, 1),
               constraints=LinearConstraint(A, np.array(model.lb, float), np.array(model.ub, float)), options=options)
    runtime = time.perf_counter() - t0
    sys.stdout.flush()
    rec = OrderedDict(case=case, formulation=f"Galle et al. 2018 CRP-I ({tag})", preprocessing=preprocessing,
                      input=dict(stacks_bottom_to_top=bay["stacks"], capacity_T=bay["capacity"], containers_C=model.C,
                                 stacks_S=model.S, N=model.N),
                      variables_total=len(model.names), variable_categories=model.variable_categories(),
                      constraints_total=len(model.rows),
                      constraint_categories={k: dict(count=Counter(model.cat).get(k, 0), meaning=CATEGORY_TEXT[k])
                                             for k in CATEGORY_TEXT if Counter(model.cat).get(k, 0)},
                      constraint_matrix_file=f"{case}__{tag}__constraint_matrix.npz",
                      solver=dict(name="scipy.optimize.milp -> HiGHS", options=options,
                                  known_optimum_used=False, incumbent_supplied=False, bound_supplied=False),
                      status=int(res.status), message=res.message, success=bool(res.success),
                      objective_value=None if res.fun is None else float(res.fun),
                      objective_bound=None if getattr(res, "mip_dual_bound", None) is None else float(res.mip_dual_bound),
                      mip_gap=None if getattr(res, "mip_gap", None) is None else float(res.mip_gap),
                      mip_node_count=None if getattr(res, "mip_node_count", None) is None else int(res.mip_node_count),
                      runtime_seconds=round(runtime, 4))
    if res.x is None:
        rec["plan_status"] = "no solution vector returned"
        return rec, model, None
    x = np.round(res.x).astype(int)
    if np.max(np.abs(res.x - x)) > 1e-6:
        rec["integrality_warning"] = float(np.max(np.abs(res.x - x)))
    viol = model.check(x)
    rec["rounded_solution_violations"] = viol
    rec["objective_of_rounded_solution"] = int(model.cost @ x)
    rec["solution_vector_nonzero"] = [model.name(model.names[j]) for j in np.flatnonzero(x)]
    rec["solution_vector_file"] = f"{case}__{tag}__solution_vector.json"
    write_json(out_dir / rec["solution_vector_file"],
               dict(case=case, order="variable index order", names=[model.name(k) for k in model.names], x=x.tolist()))
    N = model.N
    rec["objective_breakdown"] = dict(
        stage_relocations=int(sum(x[model.index["a", n, n, d]] for n in range(1, N) for d in range(n + 1, model.C + 1))),
        terminal_blockers_b=int(sum(x[model.index["b", d]] for d in range(N + 1, model.C + 1))))
    try:
        stages, moves = model.plan(x)
        rec["stage_configurations_bottom_to_top"] = {str(n): st for n, st in enumerate(stages, 1)}
        rec["reconstructed_plan"] = moves
        rep = replay_report(bay["stacks"], bay["capacity"], moves)
        rec["replay_validation"] = rep
        rec["plan_status"] = "reconstructed"
        rec["replay_equals_objective"] = bool(rep["legal"] and rep["relocations"] == rec["objective_value"])
    except ValueError as e:
        rec["plan_status"] = f"NOT reconstructed: {e}"
        rec["reconstructed_plan"] = None
        rec["replay_validation"] = None
    return rec, model, x


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(PACKAGE / "A_milp"))
    args = ap.parse_args()
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    env = environment()
    print("environment:", json.dumps(env), flush=True)
    rows = []
    for case in BAY_ORDER:
        recs = {}
        for pre in (False, True):
            rec, model, x = solve(case, pre, out)
            rec["environment"] = env
            write_json(out / f"{case}__{'with_preprocessing' if pre else 'plain'}.json", rec)
            recs[pre] = rec
        primary = recs[False]
        # Comparisons made only AFTER both solves finished.
        bfs = exact_bfs(BAYS[case]["stacks"], BAYS[case]["capacity"])
        claimed = BAYS[case]["claimed_optimum"]
        proven = primary["status"] == 0 and primary["objective_bound"] is not None and \
            abs(primary["objective_value"] - primary["objective_bound"]) < 1e-6
        row = OrderedDict(case=case, milp_status=primary["message"], milp_objective=primary["objective_value"],
                          milp_bound=primary["objective_bound"], optimality_proven=proven,
                          milp_objective_with_preprocessing=recs[True]["objective_value"],
                          plan_reconstructed=primary["plan_status"] == "reconstructed",
                          replay_legal=bool(primary.get("replay_validation") and primary["replay_validation"]["legal"]),
                          replay_relocations=(primary.get("replay_validation") or {}).get("relocations"),
                          independent_bfs_optimum=bfs, claimed_optimum=claimed,
                          runtime_seconds=primary["runtime_seconds"],
                          variables=primary["variables_total"], constraints=primary["constraints_total"])
        row["verdict"] = ("MATCH" if proven and row["replay_legal"] and primary["objective_value"] == claimed
                          and row["replay_relocations"] == claimed and bfs == claimed
                          and recs[True]["objective_value"] == claimed else "MISMATCH_OR_UNRESOLVED")
        rows.append(row)
        print(f"SUMMARY {case}: {json.dumps(row)}", flush=True)
    write_json(out / "A_summary.json", dict(environment=env, rows=rows))
    with open(out / "A_summary.csv", "w") as f:
        keys = list(rows[0])
        f.write(",".join(keys) + "\n")
        for r in rows:
            f.write(",".join(json.dumps(r[k]) if not isinstance(r[k], str) else r[k].replace(",", ";") for k in keys) + "\n")


if __name__ == "__main__":
    main()
