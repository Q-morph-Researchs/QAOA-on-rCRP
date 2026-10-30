"""Offline mathematical helpers copied from the historical calibration bridge. No historical main."""
import hashlib,json
import numpy as np
from pathlib import Path
def canonical_digest(obj):
    """Same canonical-JSON SHA-256 as revised/artifacts.digest (sort_keys, compact)."""
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                                     allow_nan=False).encode()).hexdigest()


def qaoa_distribution(E, theta, n):
    """Own p=2 QAOA: |+>^n, then per layer exp(-i*gamma*E) and RX(2*beta) on every qubit."""
    p = len(theta) // 2
    psi = np.full(1 << n, (1 / np.sqrt(1 << n)), dtype=complex)
    for layer in range(p):
        psi = psi * np.exp(-1j * theta[layer] * E)
        c, s = np.cos(theta[p + layer]), -1j * np.sin(theta[p + layer])
        for q in range(n):
            v = psi.reshape(-1, 2, 1 << q)
            a0 = v[:, 0, :].copy(); a1 = v[:, 1, :].copy()
            v[:, 0, :] = c * a0 + s * a1
            v[:, 1, :] = s * a0 + c * a1
    P = np.abs(psi) ** 2
    return P / P.sum()


def circuit_distribution(circ, register="decision"):
    """Ideal distribution of the classical register `register` for a measured circuit.

    Works for the logical circuit and for a compiled 156-qubit ISA circuit: only the
    qubits that carry operations are simulated (idle qubits stay |0> and are dropped).
    """
    from qiskit import QuantumCircuit
    from qiskit.quantum_info import Statevector
    active = sorted({circ.find_bit(q).index for ins in circ.data for q in ins.qubits if ins.operation.name != "barrier"})
    pos = {q: i for i, q in enumerate(active)}
    body = QuantumCircuit(len(active)); body.global_phase = circ.global_phase
    meas = {}
    for ins in circ.data:
        qs = [circ.find_bit(q).index for q in ins.qubits]
        if ins.operation.name == "measure":
            loc = circ.find_bit(ins.clbits[0])
            reg, idx = loc.registers[0]
            if reg.name == register:
                meas[idx] = pos[qs[0]]
        elif ins.operation.name != "barrier":
            if any(pos[q] in meas.values() for q in qs):
                raise RuntimeError("gate after measurement")
            body.append(ins.operation, [pos[q] for q in qs])
    nm = len(meas)
    if sorted(meas) != list(range(nm)):
        raise RuntimeError("register not fully measured")
    P = np.abs(Statevector(body).data) ** 2
    full = np.arange(len(P)); out = np.zeros(len(P), dtype=np.int64)
    for cb, q in meas.items():
        out |= ((full >> q) & 1) << cb
    return np.bincount(out, weights=P, minlength=1 << nm), len(active)


def load_qpy(path):
    from qiskit import qpy
    with open(path, "rb") as f:
        cs = qpy.load(f)
    assert len(cs) == 1
    return cs[0]

