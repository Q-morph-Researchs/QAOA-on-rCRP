"""Read-only access to the encodings that ran on IBM (Sim9_2.py), plus independent checks.

Sim9_2.py is loaded from its sealed folder with bytecode writing disabled, so no
file is created there. Its SHA-256 is recorded before and after use. We use it
ONLY to obtain (a) the exact n-bit encoding and energy of each hardware pairing
and (b) its bitstring -> Galle-variable recovery and plan decoder. Every decoded
plan is then re-checked by this package's own replay (common.replay) and the
recovered Galle vector by this package's own CRP-I rows (galle_milp.CRPI).
"""
import importlib.util
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from common import BAYS, replay_report, sha256_file  # noqa: E402
from galle_milp import CRPI  # noqa: E402

SIM9_DIR = HERE
SIM9_FILE = SIM9_DIR / "Sim9_2.py"
EXPECTED_SIM_SHA = "bbd2c4473ac4540d8770d02191e505dd6c204dda4f3bac7a6085dc14b9a6dec0"  # versions.sim_sha256 in every IBM registry record

_mod = None


def sim9():
    global _mod
    if _mod is None:
        before = sha256_file(SIM9_FILE)
        if before != EXPECTED_SIM_SHA:
            raise RuntimeError(f"Sim9_2.py hash {before} differs from the hash recorded by the IBM jobs")
        spec = importlib.util.spec_from_file_location("sim9_2_readonly", SIM9_FILE)
        _mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = _mod   # dataclasses need the module registered
        spec.loader.exec_module(_mod)
    return _mod


class Pairing:
    """One hardware pairing (bay, encoding) rebuilt exactly as Sim9_2.ibm_build does."""

    def __init__(self, case, method):
        m = sim9()
        self.case, self.method = case, method
        self.bay, self.problem, self.theta, self.angle_id = m.ibm_build(case, method)
        p = self.problem
        self.n = p.n
        self.encoding = p.predicate or p.qubo
        self.scale = float(p.scale)
        self.width = p.n if p.predicate is not None else p.qubo.physical_bits
        b = BAYS[case]
        if [list(s) for s in self.bay["stacks"]] != b["stacks"] or self.bay["capacity"] != b["capacity"]:
            raise RuntimeError(f"{case}: Sim9_2 bay data differ from this package's input")
        self.crpi_plain = CRPI(b["stacks"], b["capacity"], preprocessing=False)
        self.crpi_pp = CRPI(b["stacks"], b["capacity"], preprocessing=True)
        gm = p.model
        names = [f"a[{k[0]},{k[1]},{k[2]}]" if k[0] != "b" else f"b[{k[1]}]" for k in sorted(gm.index, key=gm.index.get)]
        mine = {self.crpi_plain.name(k): j for j, k in enumerate(self.crpi_plain.names)}
        if sorted(names) != sorted(mine):
            raise RuntimeError(f"{case}: Sim9 Galle variables differ from this package's CRP-I variables")
        self.to_mine = [mine[nm] for nm in names]       # Sim9 index -> my index
        self._cache = {}

    def energy(self, state):
        bits = [(state >> i) & 1 for i in range(self.n)]
        return float(self.encoding.energy(bits))

    def outcome(self, state):
        """Decode one n-bit state. Returns Sim9's verdict plus this package's independent checks."""
        if state in self._cache:
            return self._cache[state]
        bits = [(state >> i) & 1 for i in range(self.n)]
        out = self.problem.outcome(bits)
        rec = dict(state=int(state), energy=float(out["energy"]), sim9_legal=bool(out.get("valid")),
                   sim9_relocations=out.get("relocations"))
        try:
            x9 = self.encoding.presolve.recover(bits[: self.width] if self.problem.qubo is not None else bits)
        except ValueError:
            x9 = None
        if x9 is None:
            rec.update(own_rows_feasible=False, own_rows_feasible_pp=False)
        else:
            x = [0] * len(self.to_mine)
            for i, v in enumerate(x9):
                x[self.to_mine[i]] = int(v)
            rec["own_rows_feasible"] = not self.crpi_plain.check(x)
            rec["own_rows_feasible_pp"] = not self.crpi_pp.check(x)
            rec["own_objective"] = int(self.crpi_plain.cost @ x)
        if rec["sim9_legal"]:
            moves = [{k: v for k, v in mv.items() if k in ("type", "container", "source", "destination")} for mv in out["moves"]]
            rep = replay_report(self.bay["stacks"], self.bay["capacity"], moves)
            rec["own_replay_legal"] = rep["legal"]
            rec["own_replay_relocations"] = rep["relocations"]
            rec["moves"] = moves
        else:
            rec["own_replay_legal"] = None
        # Agreement flags (any False is reported, never hidden).
        rec["legal_agrees_with_own_rows"] = rec["sim9_legal"] == rec["own_rows_feasible"]
        rec["relocations_agree_with_own_replay"] = (not rec["sim9_legal"]) or (
            rec["own_replay_legal"] and rec["own_replay_relocations"] == rec["sim9_relocations"])
        self._cache[state] = rec
        return rec
