"""Offline, frozen-circuit supplementary experiment. Never contacts IBM."""
import os
os.environ.setdefault('OMP_NUM_THREADS', '2')
import argparse, hashlib, json, platform, sys, time
from pathlib import Path
sys.dont_write_bytecode = True
import numpy as np
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel
from qiskit_ibm_runtime.models import BackendProperties
from calibration_bridge import load_qpy, circuit_distribution, qaoa_distribution
from sim9_bridge import Pairing
from common import BAYS

ROOT = Path(__file__).resolve().parents[1]
def write(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, allow_nan=False))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def compact(circuit):
    active = sorted({circuit.find_bit(q).index for ins in circuit.data if ins.operation.name != 'barrier' for q in ins.qubits})
    pos = {q:i for i,q in enumerate(active)}
    assert len(circuit.cregs)==1 and circuit.cregs[0].name=='decision'
    c = QuantumCircuit(len(active), circuit.num_clbits)
    c.global_phase = circuit.global_phase
    for ins in circuit.data:
        if ins.operation.name=='barrier': continue
        c.append(ins.operation, [pos[circuit.find_bit(q).index] for q in ins.qubits], [circuit.find_bit(b).index for b in ins.clbits])
    return c,active

def noise_for(snapshot, active):
    d=json.loads(snapshot.read_text())
    original=NoiseModel.from_backend_properties(BackendProperties.from_dict(d['properties']),thermal_relaxation=False)
    errors=[];pos={q:i for i,q in enumerate(active)}
    for e in original.to_dict()['errors']:
        assert 'gate_qubits' in e, 'Unmapped global error'
        keep=[qs for qs in e['gate_qubits'] if all(q in pos for q in qs)]
        if keep:
            e['gate_qubits']=[[pos[q] for q in qs] for qs in keep];errors.append(e)
    model=NoiseModel.from_dict({'errors':errors})
    return model, {'errors':errors},d['captured_utc']

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);ap.add_argument('--only-slot',type=int);args=ap.parse_args()
    out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=True)
    # Refuse altered inputs, including protocol. Source implementation has its own manifest in final bundle.
    for p,h in json.loads((ROOT/'INPUT_HASHES.json').read_text()).items():
        assert sha(ROOT/p)==h, f'Input changed: {p}'
    jobs=json.loads((ROOT/'inputs/jobs.json').read_text())
    seeds=[int(s.generate_state(1)[0]) for s in np.random.SeedSequence(2026101701).spawn(80)]
    assert len(set(seeds))==80
    import qiskit,qiskit_aer,scipy
    write(out/'environment.json',dict(python=sys.version,platform=platform.platform(),numpy=np.__version__,qiskit=qiskit.__version__,aer=qiskit_aer.__version__,scipy=scipy.__version__,seeds=seeds,protocol_sha256=sha(ROOT/'PROTOCOL.json')))
    cache={};preps={}
    for j,r in enumerate(jobs):
        if args.only_slot and j+1!=args.only_slot: continue
        dest=out/'jobs'/r['attempt_id']
        if (dest/'result.json').exists():
            print('Saved result preserved',j+1,flush=True);continue
        item=r['prep']['item'];v=r['prep']['version'];key=(item,v)
        if item not in cache:
            start=time.perf_counter();P=Pairing(r['case'],r['method']);n=P.n
            legal=np.zeros(1<<n,bool);optimal=legal.copy();energy=np.zeros(1<<n);relocations=np.full(1<<n,-1,int)
            plans={}
            for s in range(1<<n):
                rec=P.outcome(s)
                assert rec['legal_agrees_with_own_rows'] and rec['relocations_agree_with_own_replay']
                energy[s]=rec['energy']/P.scale
                legal[s]=rec['sim9_legal']
                if legal[s]:
                    relocations[s]=rec['own_replay_relocations'];plans[str(s)]=rec['moves']
                    optimal[s]=relocations[s]==BAYS[r['case']]['claimed_optimum']
            ideal=qaoa_distribution(energy,np.array(P.theta),n)
            assert abs(ideal.sum()-1)<1e-12
            d=out/'pairings'/item;d.mkdir(parents=True,exist_ok=True)
            np.savez_compressed(d/'state_space.npz',legal=legal,optimal=optimal,relocations=relocations,energy_scaled=energy,ideal=ideal)
            write(d/'legal_plans.json',plans)
            write(d/'exact.json',dict(case=r['case'],method=r['method'],n=n,theta=list(P.theta),scale=P.scale,states=1<<n,legal_states=int(legal.sum()),optimal_states=int(optimal.sum()),uniform_legal=float(legal.mean()),uniform_optimal=float(optimal.mean()),ideal_legal=float(ideal[legal].sum()),ideal_optimal=float(ideal[optimal].sum()),enumeration_seconds=time.perf_counter()-start))
            cache[item]=(legal,optimal,ideal)
            print('Enumerated and independently replayed',item,1<<n,flush=True)
        legal,optimal,ideal=cache[item]
        if key not in preps:
            p=ROOT/'inputs/prep'/item/f'v{v}'
            assert sha(p/'isa.qpy')==r['prep']['isa_sha256']
            isa=load_qpy(p/'isa.qpy');logical=load_qpy(p/'logical.qpy')
            dist,active_n=circuit_distribution(isa);ldist,_=circuit_distribution(logical)
            err=max(float(np.max(abs(dist-ideal))),float(np.max(abs(ldist-ideal))))
            assert err<1e-9
            c,active=compact(isa)
            cdist,_=circuit_distribution(isa) # original-register check above; compact checked below by exact saved probabilities
            nm,nd,captured=noise_for(p/'backend_snapshot.json',active)
            # Validate remapping: compact ideal with measurements removed matches original full-state ordering.
            from qiskit.quantum_info import Statevector
            prob=Statevector(c.remove_final_measurements(inplace=False)).probabilities()
            mapping={c.find_bit(ins.clbits[0]).index:c.find_bit(ins.qubits[0]).index for ins in c.data if ins.operation.name=='measure'}
            x=np.arange(len(prob));labels=np.zeros(len(prob),int)
            for cb,q in mapping.items(): labels|=((x>>q)&1)<<cb
            cp=np.bincount(labels,weights=prob,minlength=len(ideal))
            assert np.max(abs(cp-ideal))<1e-9
            audit=dict(active_physical_qubits=active,active_qubits=active_n,decision_qubits=len(mapping),compiled_two_qubit_gates=sum(ins.operation.num_qubits==2 for ins in c.data),compiled_depth=c.depth(),max_ideal_error=err,snapshot_captured_utc=captured,isa_sha256=sha(p/'isa.qpy'),snapshot_sha256=sha(p/'backend_snapshot.json'),noise_error_records=len(nd['errors']),noise_mode='gate depolarization plus readout; no explicit thermal relaxation')
            write(out/'preparations'/item/f'v{v}'/'audit.json',audit)
            write(out/'preparations'/item/f'v{v}'/'noise_model.json',nd)
            preps[key]=(c,nm,audit)
        c,nm,audit=preps[key];dest.mkdir(parents=True,exist_ok=True)
        rng=np.random.default_rng(seeds[2*j]);rng_before=rng.bit_generator.state
        ideal_states=rng.choice(len(ideal),size=2000,p=ideal)
        np.save(dest/'ideal_states.npy',ideal_states)
        start=time.perf_counter()
        sim=AerSimulator(method='statevector',noise_model=nm,max_parallel_threads=2,max_parallel_shots=1,max_memory_mb=2048)
        result=sim.run(c,shots=2000,memory=True,seed_simulator=seeds[2*j+1]).result()
        assert result.success
        states=np.array([int(s.replace(' ',''),2) for s in result.get_memory()],dtype=np.int64)
        seconds=time.perf_counter()-start
        assert len(states)==2000 and states.max()<len(ideal)
        np.save(dest/'noisy_states.npy',states)
        hw=np.load(ROOT/'inputs/hardware'/r['attempt_id']/'states.npy')
        scores={}
        for cond,arr in [('hardware',hw),('ideal_sampled',ideal_states),('snapshot_noise',states)]:
            scores[cond]=dict(shots=len(arr),legal_count=int(legal[arr].sum()),optimal_count=int(optimal[arr].sum()))
        assert scores['hardware']['legal_count']==r['results']['score']['accepted_count']
        assert scores['hardware']['optimal_count']==r['results']['score']['replay_optimal_count']
        write(dest/'result.json',dict(slot=j+1,item=item,case=r['case'],method=r['method'],job_id=r['job_id'],prep_version=v,ideal_seed=seeds[2*j],noise_seed=seeds[2*j+1],rng_before=rng_before,rng_after=rng.bit_generator.state,noisy_wall_seconds=seconds,scores=scores,simulator_metadata=result.results[0].metadata))
        print('Completed',j+1,item,'version',v,'seconds',round(seconds,2),'counts',scores,flush=True)
    print('Finished selected workload',flush=True)
if __name__=='__main__':main()
