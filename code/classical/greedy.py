"""Part B: deterministic greedy heuristic (fresh implementation, no QAOA code).

RULE (fixed before any run; a min-max rule in the spirit of Caserta et al. 2012):
  1. If the current target container is on top of its stack, retrieve it.
  2. Otherwise take the top container c of the target's stack and relocate it.
     Candidate destinations: every OTHER stack with free capacity.
     a. "Safe" stacks are those where c will not block anything: the stack is empty
        or every container in it has a larger number than c. If any safe stack
        exists, choose the safe stack whose smallest container number is LOWEST
        (an empty stack counts as infinity, so it is used only when no non-empty
        safe stack exists). This keeps empty stacks for later.
     b. If no safe stack exists, choose the stack whose smallest container number
        is HIGHEST (c will be dug out as late as possible).
  3. TIE-BREAK: lowest stack index (stack 1 before stack 2 ...).
The rule never looks ahead and never reads any optimum.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import BAYS, BAY_ORDER, PACKAGE, environment, replay_report, write_json  # noqa: E402

INF = float("inf")


def greedy(stacks, capacity):
    bay = [list(s) for s in stacks]
    C = sum(len(s) for s in bay)
    target, moves = 1, []
    while target <= C:
        src = next(i for i, s in enumerate(bay) if target in s)
        if bay[src][-1] == target:
            bay[src].pop(); moves.append(dict(type="retrieve", container=target, source=src + 1)); target += 1
            continue
        c = bay[src][-1]
        cands = [i for i in range(len(bay)) if i != src and len(bay[i]) < capacity]
        if not cands:
            raise RuntimeError("no free destination: bay is infeasible for this rule")
        low = lambda i: min(bay[i]) if bay[i] else INF
        safe = [i for i in cands if low(i) > c]
        if safe:
            dst = min(safe, key=lambda i: (low(i), i))          # lowest smallest-number, then lowest index
            reason = "safe stack with the lowest smallest-number"
        else:
            dst = min(cands, key=lambda i: (-low(i), i))        # highest smallest-number, then lowest index
            reason = "no safe stack; stack with the highest smallest-number"
        bay[dst].append(bay[src].pop())
        moves.append(dict(type="relocate", container=c, source=src + 1, destination=dst + 1, rule=reason))
    return moves


def main():
    out = PACKAGE / "B_greedy"; out.mkdir(exist_ok=True)
    env = environment(); rows = []
    for case in BAY_ORDER:
        bay = BAYS[case]
        t0 = time.perf_counter(); moves = greedy(bay["stacks"], bay["capacity"]); first = time.perf_counter() - t0
        reps = 1000; t0 = time.perf_counter()
        for _ in range(reps):
            assert greedy(bay["stacks"], bay["capacity"]) == moves      # determinism check
        mean = (time.perf_counter() - t0) / reps
        rep = replay_report(bay["stacks"], bay["capacity"], [{k: v for k, v in m.items() if k != "rule"} for m in moves])
        rec = dict(case=case, input=dict(stacks_bottom_to_top=bay["stacks"], capacity=bay["capacity"]),
                   rule=__doc__.split("RULE")[1].strip(), moves=moves, relocations_by_rule=sum(m["type"] == "relocate" for m in moves),
                   replay=rep, runtime_first_call_seconds=first, runtime_mean_seconds_over_1000_calls=mean,
                   deterministic_over_1000_calls=True, environment=env)
        write_json(out / f"{case}.json", rec)
        rows.append(dict(case=case, greedy_relocations=rep["relocations"], replay_legal=rep["legal"], moves=len(moves),
                         runtime_mean_seconds=mean))
        print("GREEDY", json.dumps(rows[-1]), flush=True)
    # Comparison with the independent MILP optimum, made only after all greedy plans exist.
    milp = {r["case"]: r for r in json.loads((PACKAGE / "A_milp" / "A_summary.json").read_text())["rows"]}
    for r in rows:
        m = milp[r["case"]]
        r["milp_optimum"] = m["milp_objective"] if m["optimality_proven"] else None
        r["greedy_minus_optimum"] = None if r["milp_optimum"] is None else r["greedy_relocations"] - r["milp_optimum"]
        r["greedy_optimal"] = r["greedy_minus_optimum"] == 0
    write_json(out / "B_summary.json", dict(environment=env, rows=rows))
    for r in rows:
        print("COMPARE", json.dumps(r), flush=True)


if __name__ == "__main__":
    main()
