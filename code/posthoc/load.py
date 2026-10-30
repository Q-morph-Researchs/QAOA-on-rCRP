"""Load the sealed Sim9_2.py read-only (hash-checked) and rebuild the eight IBM pairings."""
import hashlib
import importlib.util
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
SIM = HERE / "sim9" / "Sim9_2.py"
EXPECTED = "bbd2c4473ac4540d8770d02191e505dd6c204dda4f3bac7a6085dc14b9a6dec0"   # versions.sim_sha256 of every IBM job

PAIRINGS = [("A", "random-S3T4C6-21", "predicate"), ("A", "random-S3T4C6-21", "galle"),
            ("B", "random-S3T4C6-24", "predicate"), ("B", "random-S3T4C6-24", "galle"),
            ("C", "random-S3T4C7-32", "predicate"), ("C", "random-S3T4C7-32", "galle"),
            ("D", "random-S4T3C6-16", "predicate"), ("E", "data3-3-8", "predicate")]


def sim9():
    digest = hashlib.sha256(SIM.read_bytes()).hexdigest()
    if digest != EXPECTED:
        raise RuntimeError(f"Sim9_2.py hash {digest} is not the hash recorded by the IBM jobs")
    if "sim9_2_readonly" in sys.modules:
        return sys.modules["sim9_2_readonly"]
    spec = importlib.util.spec_from_file_location("sim9_2_readonly", SIM)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod
