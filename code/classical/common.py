"""Shared, dependency-light helpers for the classical companion study.

Written fresh for this package. Nothing here imports the QAOA code (Sim9_2.py or
the revised package). Stacks are bottom-to-top; container 1 is retrieved first.
"""
import hashlib
import json
import os
import platform
import sys
from pathlib import Path

PACKAGE = Path(os.environ.get("RCRP_CLASSICAL_OUTPUT", str(Path(__file__).resolve().parents[1])))

# The five IBM bays, typed in from the task brief and cross-checked against
# Sim9_2.py IBM_STUDY_DATA and release_evidence/calibration/instances.json by
# code/check_inputs.py. "claimed_optimum" is used ONLY for the after-the-fact
# comparison column; no solver, heuristic or SA run reads it.
BAYS = {
    "random-S3T4C6-21": dict(stacks=[[1], [4, 3], [6, 2, 5]], capacity=4, claimed_optimum=1),
    "random-S3T4C6-24": dict(stacks=[[5, 2, 6, 1], [4], [3]], capacity=4, claimed_optimum=2),
    "random-S3T4C7-32": dict(stacks=[[7], [6, 2, 4], [5, 3, 1]], capacity=4, claimed_optimum=1),
    "random-S4T3C6-16": dict(stacks=[[], [6], [3, 5], [2, 4, 1]], capacity=3, claimed_optimum=2),
    "data3-3-8": dict(stacks=[[9, 2, 4], [8, 7, 1], [5, 6, 3]], capacity=5, claimed_optimum=2),
}
BAY_ORDER = list(BAYS)

# Hardware pairings (bay, encoding) exactly as run on ibm_fez.
PAIRINGS = [("random-S3T4C6-21", "predicate"), ("random-S3T4C6-21", "galle"),
            ("random-S3T4C6-24", "galle"), ("random-S3T4C6-24", "predicate"),
            ("random-S3T4C7-32", "predicate"), ("random-S3T4C7-32", "galle"),
            ("random-S4T3C6-16", "predicate"), ("data3-3-8", "predicate")]


class IllegalMove(ValueError):
    pass


def replay(stacks, capacity, moves):
    """Independent restricted-CRP replay. Raises IllegalMove on any rule break.

    Rules: only the top container of a stack moves; retrievals happen in order
    1, 2, ..., C; a relocation is allowed only for a container that sits above
    the current target in the target's stack (restricted CRP); the destination
    must be a different stack with free capacity; the plan must empty the bay.
    Returns the relocation count.
    """
    bay = [list(s) for s in stacks]
    C = sum(len(s) for s in bay)
    target, relocations = 1, 0
    for k, m in enumerate(moves):
        s = m["source"] - 1
        if not (0 <= s < len(bay)) or not bay[s] or bay[s][-1] != m["container"]:
            raise IllegalMove(f"move {k}: container {m['container']} is not on top of stack {m['source']}")
        if m["type"] == "retrieve":
            if m["container"] != target:
                raise IllegalMove(f"move {k}: retrieved {m['container']} but target is {target}")
            bay[s].pop()
            target += 1
        elif m["type"] == "relocate":
            d = m["destination"] - 1
            if target not in bay[s]:
                raise IllegalMove(f"move {k}: relocation from a stack that does not hold target {target}")
            if m["container"] == target:
                raise IllegalMove(f"move {k}: the target itself cannot be relocated")
            if not (0 <= d < len(bay)) or d == s:
                raise IllegalMove(f"move {k}: bad destination {m['destination']}")
            if len(bay[d]) >= capacity:
                raise IllegalMove(f"move {k}: destination stack {m['destination']} is full")
            bay[d].append(bay[s].pop())
            relocations += 1
        else:
            raise IllegalMove(f"move {k}: unknown move type {m['type']}")
    if target != C + 1 or any(bay):
        raise IllegalMove("plan does not empty the bay")
    return relocations


def replay_report(stacks, capacity, moves):
    try:
        r = replay(stacks, capacity, moves)
        return dict(legal=True, relocations=r, error=None)
    except IllegalMove as e:
        return dict(legal=False, relocations=None, error=str(e))


def exact_bfs(stacks, capacity):
    """Independent exact search (uniform-cost over relocation count).

    Used only as a second, non-MILP cross-check of the MILP optimum. Each edge is
    one legal restricted relocation, followed by all retrievals that are then free.
    """
    import heapq

    def settle(bay, target):
        bay = [list(s) for s in bay]
        while True:
            for s in bay:
                if s and s[-1] == target:
                    s.pop(); target += 1
                    break
            else:
                return bay, target

    C = sum(len(s) for s in stacks)
    start = settle(stacks, 1)
    key = lambda b, t: (t, tuple(tuple(s) for s in b))
    seen = {key(*start): 0}
    heap = [(0, 0, start[1], start[0])]
    counter = 1
    while heap:
        cost, _, target, bay = heapq.heappop(heap)
        if target == C + 1:
            return cost
        if seen.get(key(bay, target), 1 << 30) < cost:
            continue
        src = next(i for i, s in enumerate(bay) if target in s)
        top = bay[src][-1]
        for d in range(len(bay)):
            if d == src or len(bay[d]) >= capacity:
                continue
            nb = [list(s) for s in bay]
            nb[d].append(nb[src].pop())
            nb, nt = settle(nb, target)
            k = key(nb, nt)
            if seen.get(k, 1 << 30) > cost + 1:
                seen[k] = cost + 1
                heapq.heappush(heap, (cost + 1, counter, nt, nb)); counter += 1
    return None


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text):
    return hashlib.sha256(text.encode()).hexdigest()


def write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=False, default=str) + "\n")
    os.replace(tmp, path)


def environment():
    import numpy
    import scipy
    from scipy.optimize._highspy import _core
    return dict(python=sys.version.split()[0], executable=sys.executable, platform=platform.platform(),
                numpy=numpy.__version__, scipy=scipy.__version__,
                highs=f"{_core.HIGHS_VERSION_MAJOR}.{_core.HIGHS_VERSION_MINOR}.{_core.HIGHS_VERSION_PATCH}",
                threads={k: os.environ.get(k) for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")})
