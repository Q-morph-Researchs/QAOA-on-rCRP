#!/usr/bin/env python3
"""rCRP QAOA Suite, Sim9.2 (12 Oct 2026): Sim9 with a repaired IBM workflow (fixes 19-26).
Built from Sim9.py (sha256 bd9a085a...13bf) by build/make_sim9_2.py; only the IBM workflow section changed.

rCRP QAOA Suite, Sim9 (12 Oct 2026): Sim8 plus fixes 11-18 and the IBM hardware study workflow.

Built from Sim8.py (sha256 4085e0ee...2cb6) by sim9/make_sim9.py; every change is listed in FIXES.
IBM real-hardware test: python Sim9.py ibm plan | check | run | retrieve | summarize (see the pamphlet).

rCRP QAOA Suite — the whole rCRP/QAOA project in one file, with a tkinter GUI.

Restricted Container (Block) Relocation Problem, solved by QAOA on exact
encodings of Galle, Barnhart & Jaillet's CRP-I binary program (EJOR 2018).

This single script merges the solver code of the QAOA handoff package (9 Oct 2026):

  galle_baseline.py      CRP-I model, presolve, exact QUBO, greedy bound, BFS, MILP
  coherent_crp.py        reversible movement oracle (research encoding)
  galle_predicates.py    predicate encoding (direct constraint phases)
  hybrid_encoding.py     hybrid encoding (direct phases + compact slack)
  hardware_solver.py     Problem wrapper, decoders, Qiskit circuits, IBM workflow
  paper_sim.py           NumPy statevector QAOA, tuning, baselines, gate counts
  revised/physical.py    independent physical replay checker
  revised/protocols.py   corrected simulated annealing (protocol /2)
  revised/scoring.py     outcome vocabulary (accepted / replay-optimal / ground)
  noise_gate_level.py,   gate-level Pauli-fault noise simulation
  noise_fast.py
  move_model.py          move-encoding resource counts
  benchmark_support.py   published references, accuracy/optimality metrics
  run_fake_ibm_demo.py   fake IBM device helpers
  rcrp_engine.py         one run = instance + settings -> results
  QAOA_Workbench.py,     the two original windows, merged into one GUI
  Hardware_Panel.py
  benchmark_library/     the 840 group-4 benchmark bays (embedded below)

Release machinery (revised/artifacts, release_io, seal, reproduce, ...), audit
scripts and frozen evidence are NOT merged: they verify hash-sealed files on
disk and stay in the original package.

Run
    python rcrp_qaoa_suite.py                 open the GUI (default)
    python rcrp_qaoa_suite.py selftest        built-in correctness checks
    python rcrp_qaoa_suite.py run --instance data3-3-8 --method predicate
    python rcrp_qaoa_suite.py hardware --stacks "1,3;4,5;2" --height 3 --local-check
    python rcrp_qaoa_suite.py list

Requirements: Python 3.10+, numpy, scipy (required); tkinter for the GUI;
qiskit, qiskit-aer, qiskit-ibm-runtime for circuits, fake-IBM noise and IBM
hardware (optional). Tested with numpy 2.5.3, scipy 1.18.1, qiskit 2.5.2,
qiskit-aer 0.17.2, qiskit-ibm-runtime 0.50.0 (the project's pinned versions).

Conventions: stacks are listed bottom -> top; container numbers are retrieval
priorities 1..C; a state integer's bit i is variable/qubit i.

Lines marked "FIX:" change the original behaviour; each is explained where it
occurs and summarised in FIXES below.
"""
from __future__ import annotations

FIXES = """
 1. C <= S bays crashed the engine (GalleModel raises ValueError). They are now
    solved exactly by Galle's Lemma 1 (move each blocker to an empty stack),
    replay-checked, with no QAOA step.
 2. Infeasible bays crashed in the greedy/BFS baselines before the engine's
    'infeasible' handler could run. Infeasibility is now detected first and
    reported as status 'infeasible'.
 3. "Exact P(optimal plan)" was the probability of the minimum-ENERGY strings.
    Equally optimal plans that keep an unnecessary terminal flag or non-zero
    slack have higher energy, so it understated the chance of drawing an
    optimal plan. Both are now reported, under their correct names
    (the revised release's F01 outcome vocabulary).
 4. The GUI's annealing baseline was the legacy SA that the revised release
    replaced (F02). It now uses the corrected protocol: T0=max(1,W), B
    candidate evaluations, best replayed plan over ALL evaluated candidates.
 5. After tuning, the GUI said transferred angles would be used on the fake IBM
    chip, but the engine used the tuned angles. The message now matches the code.
 6. Stop could not interrupt angle tuning, refinement or decoding (a 20-qubit
    tuning ran for over 10 minutes). All long loops now check for Stop.
 7. Only the 4,000 most frequent distinct legal samples were decoded, so the
    best sampled plan could be missed. Every sampled legal state is now scored
    by an exact cost table.
 8. paper_sim.logical_two_qubit_gates and landscape crashed for the hybrid and
    coherent encodings (AttributeError). Both are now supported.
 9. hardware_solver labelled fixed-angle sampling jobs as "Optimization" and
    printed a traceback for the 20-qubit local-check limit. Both are fixed.
10. The engine drew uniform samples from the same random stream as QAOA, so
    changing QAOA settings changed the random-guessing control. Each method
    now has its own seeded stream.
--- Sim9 (12 Oct 2026), from the strong-presolve audit and the IBM study ---
11. Any presolve value other than 'standard' (e.g. 'Standard', 'none') silently
    selected strong presolve. Unknown values now raise an error.
12. Defaults now use the STANDARD presolve (the validated release model) in the
    engine, the run/export commands and the GUI. Strong presolve is still
    available; it is exact for the best plan but deletes duplicate flag copies,
    so its legal-plan rates cannot be compared with standard runs.
13. Strong presolve stopped probing at a 60 s wall-clock deadline, so a slower
    computer could produce a different (still exact) model. The default is now
    no deadline (run to the fixed point; identical models on this Mac for every
    audited bay), and stats['deadline_hit'] records any cut-off.
14. A comment said strong presolve leaves the feasible set unchanged; flag
    dominance deletes duplicate assignments. The comment now says so.
15. Qubo.complete hit an assert with strong presolve when given an assignment
    with a dominated spare flag; it now raises a clear ValueError.
16. The fake IBM device was an older Eagle chip (FakeBrisbane); it is now the
    Heron r2 snapshot FakeFez, as used in the IBM study.
17. The hardware command defaulted to multi-controlled-phase synthesis; it now
    defaults to the exact Pauli synthesis used by the release ('mcp' still works).
18. New 'ibm' command: the declared IBM study protocol (frozen bays, LOO angles,
    compile check on the live device, approval gate, 5 x 2000 shots, full records).
--- Sim9.2 (12 Oct 2026): IBM workflow repair; science unchanged ---
19. F01: a persistent, file-locked job registry (submitting / submitted / uncertain /
    awaiting / completed / failed / cancelled / reconciled_no_job). The 30 s budget
    reservation is written before dispatch and kept until IBM accounting is final.
    Any unresolved attempt blocks further submissions.
20. F02: IBM usage is read from metrics()['usage'] (status + qpu_charge_time_seconds);
    'pending' is never treated as zero; legacy 'quantum_seconds' only for terminal
    jobs; final / final_zero / pending / unavailable / reserved are kept apart.
21. F03: "ibm replace" replaces exactly ONE failed or cancelled slot with one job,
    once, after final accounting; both attempts and costs are kept.
22. F04: resume = "ibm submit" takes the next genuinely unstarted slot; "ibm collect"
    updates the original record, never submits and never double counts.
23. Interrupted or uncertain submissions are kept as 'uncertain' and resolved by
    "ibm reconcile" (unique per-attempt IBM job tag); no automatic resubmission.
24. Explicit named account + Open Plan CRN; the active instance and plan are
    verified; no default-account or paid-instance fallback.
25. Remote jobs are matched by backend, unique tag, instance, input circuit (when the
    SDK returns it) and shots before results are used.
26. Summaries work for empty and partial studies; old "ibm run"/"ibm retrieve" removed.
27. The legacy "hardware" command (and the GUI hardware tab that calls it) no longer
    contacts real IBM devices: it used the default saved account and bypassed the
    registry. It keeps --backend fake and --local-check; real runs use "ibm".
"""

import argparse
import base64
import hashlib
import json
import math
import os
import queue
import random
import re
import subprocess
import sys
import threading
import time
import traceback
import warnings
import zlib
from collections import Counter, defaultdict, deque
from dataclasses import asdict, dataclass, field
from itertools import combinations, product
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

HERE = Path(__file__).resolve().parent
warnings.filterwarnings('ignore', message='The SamplerV2 class is deprecated')     # still supported in qiskit-ibm-runtime 0.50
SCRIPT = Path(__file__).resolve()
__version__ = '1.0 (merged from the 2026-10-09 handoff)'


class Cancelled(Exception):
    """Raised inside long computations when the user presses Stop."""


def _never():
    return False


# Embedded copy of benchmark_library/catalog.json (Bacci, Mattia & Ventura group-4 instances),
# 840 bays up to 100 containers: [id, capacity, stacks bottom->top, best_known, lower_bound, proven_optimal].
# sha256 of the decoded JSON: f61487c0554148b8d8042d6ab1b1522a96d2fe8cb79043295ca9cc1e814dde42
# The forty 10,000-container bays are omitted (no encoding can even be built for them).
_CATALOG_B85 = (
    'c-n-$$+GOqjvV?g8s~n-0HXbtYiCeqdKzh@=Kqz1yCb;kX0RqI)46*k$!O3x9FBke>%aZ?|M)-u;eY&3`EQ^0`PaYvGd|^?&%f-'
    '`KkfT}=VyKDKmUCHfBpZvKL6)`{onup`yca<41Y8~_2b|F-oF2AegALy*k^qIsD0XxKXUz1`Tp|fU*r4#v+w_1-'
    '#_;6AKAx#{87apt?&Ok;<Y?q^M1YhsXzXx>5n{~aKB!OKOXT%<x_tAQO6&R??0aL1drD&-~YOf3o-'
    'CVh2QdhsaS~nHOKLfre4qD36o3TUKe8NNi+6GPclAfe8!JIDi{8$#d6&rGvYn(-'
    'Sy)}6`qOueU%bB<)0pZg{AP1|N1K)itk!;t5!VIzW?>*S^oETecvyR)c5PY&-'
    '~~6U+1sCs(RMocX|A^egA5nSA*x`dq}y49$UTQM4oo5bgiMqcUAsX;Ts;FHMEAEtAVxj?_ag^YD_(=#6AsPu*qlrJ{o1|=&tzJy2'
    'JOH*5ex5r8S)Ktov+W<+01Zzsri&5Lf=Y7V%v**7W#Swy$yLUm5?Z9IvtY{;SFF8u6wzPSn9RRlVViH*EP`J)U*=t0p_RxEhmIs>'
    'gR7-mvQp@r>I5;-'
    '=KMzZ!cDN4(+R=kWL0u&G@x@r=g%g|$5X)!H{@@uuKb&X@i2ORLei3WfF!_v`l>deL3(@voiFobfA1w_rN+ScO4r4fA+9^X}V5wT'
    'BVC@ATP5dDVC6%y*uV`eLuW>APS77T2(I4G-'
    'Vdwad<xmnEogD?j8V@vohB9v<fStf}wnT*F0sSYF(uFP&bT^+ta=cvG&=^~)otPnq$C7Pbj?u^hguD$KZ-'
    't{B%2&ngH9%JuyR<?w}75l69%8b&<z`)A)Dm=CM)Yv=2qJT5H_YT@&*j3~<a{p*f+Vmpk_zu%`6zR1zfRfQy9V`;qeo&Nj#hhaMI'
    '_dnUE`X`-`%+vQDU$Kq@A5u!(pVRy2u_`4kZ;SI)48MfC@K3DA_2U=jUV&0*S8-3jzhJz2-'
    '(Na?K{_eJ3orV%d;9bTExg>X(^@l@vAu-fSDmzJrO?E`eL^YQH56VhJUO=!cJg?NZQo9K+V9)*95wpE@55hy!1V@*XN$a4XJC8(-'
    'W7ND_c>PNb8jQw{r-'
    'qfk5zOv+W8II<0Q04jIm<bEWOz2Br6`eBeXm?rcj`0E$k3@)C`RlO~4&6>IgUd<OmCUI!Vtc2{A}4S^U6=6VY+Vj&HE?DA9#3284'
    'r`*>EOLZ=l#Iu3^5q7T@tvS6s(~IV<VR3qHB#nKZhjV#oNhW<)i3e)Rm<L%l(HSwsa__rK=J#gV*yyet|bi{JNAaaNT{`TqOCSD$'
    '(V?84y<TD}2~^2+sR#D}weT!X$7DeVHS`D8*c_ydPe7~85kT{E}86uFlXYw#-ysTq?^ocJ9?@ANDj)cF(E-'
    'wB#;n^u$pEG**stY3ajC-HVa1)p9llcCB}?Z;j4@>oP#FvBZcv~qX!cQz=#U9--z0zZpT2d3$~jSA%)rZbLyVHi{C?RXasYp`viw'
    '&7yRIvCoNxK+nD$i%S9D({T9q-'
    '{J$C*J=)NM#!aZD=Pp^4lW$BVEKvyw?)1vUrleKV;|lX6{S`##o!t`3)1Vbo_+%_YY)*!N7t)biU3zF4U71EIBil2%7A$3r!(nF*'
    '>x{5|*l9tz?WCC(4;Q{(6`8XG0PC2q!85%if4Eqz`Y$xAN!x5}Fj(<NMQ%Yt4`-'
    '?3W)lx&5gdASs2{BR;S=E#`dz@S5#yvD=^acODZq7^z9&m5X>5?)m=scDOxlN0toZ;vMi>_g~VGH$qkMoYPv3{}dvY2+`UjT({T}'
    '=b<R)!;lG0@wDySxI%ct2>vYY@+t0XfAVPG%c@H`wD7Qzg%{Rg2T!Y|C=|P|H)B%ZieCg%b{_a&?x$rqy6%sxdN1K4P1#XFzFv4B'
    '?*CGL{hICUd&*`x19hIVvNy)wj#u&jy!<1cPg|I;bTMoK&UAdU`Zru0mvP|=@sJ8!qZ4W8HEVf^8llXB)vriD<gO4681Cc2;Pl)}'
    'B)+kei6#i}C_r}NFdy&s#{0^)DjPJ-)n~R*+RHUke2bfib%IN7_kIk1Ta!^m-'
    'g{WD^>@ni{i)o9f%_Ejxc%kj4p#Nrp5B!%89g<x7Jj29(scSpD;qhNg<kuE3d4CLWKw`3AAT!iVR?s$VG3cclJU6j+j{&h*ZErXn'
    'kIXy-'
    'D?@8`hDc;dA;f*w7TScM%rX#(WMfeEbSQMv<#M4V)6}(<Y^Wy%?RztZ&%+kZr*F+ymj!3baUx_Ve${}H8PRO_2r6H6&;Ko2$=aiu'
    'l?M}5^avWq7J+3^$=mbto_;^QejL<?1mp35sjxSIo)l=*j32G{ac6uTG|H%%eVhMB6Tgp?GY!GX4GlGXiq1jPh9e|FUrWfD!B1Pc'
    'b9@c0TiXZAigbw@JRYHmeFZ)`9|LI`Z?#O?SZncjBjj51jaP8(dW%KyPDYR#beb4wOjheg=J!h>&G*pC>@xgR=POLPF=TfJxs{)y'
    '%NJON>%B*3)8OlK;{bH>lC0UdJhkwy{AuVav(x0rlQPWnLx`xzO=LlH4C97Bk{6>gmFBris?&XTpGVQ|GM3mR^Jgp{`##71h}hwk'
    'toXz-0;<AE`0=JeqON(Jh*c!<KK2#DwE0S3CzZ+9Y<iW0v+xwlJE{HSV}aZbVk~1M`DLxt9-'
    'ZHgz}RBOr%Av#7;~6t{?7F1#TR_b^p7rv>b>@+g447xCZR;%U)Dq$X%ORy262s%5Dor(~Vn-9r(SQLn~JL(^0G}Ar{-'
    'XI75wp!jSlnUz_+f!)m~0AdfW0(M=ZZUb@M%@gv@>K$_z_@3^!xMQDi;eXzB@pK%>xu}ajrBj&kJZk#io&zfJiax+@QL%)nhCH~x'
    '56526DQ+gaRt@4n2SLZpcsYIjsp-mah{G>H3k(bsD2J(6y-i>$QhUMc;u%j-&KJphBF~a-'
    'a8)UzJuI2@WB~@G|dO&Qn6DFFttmgw#n%*vKd`s)Wt6#LOoyNQ!Y<DGs-4(MmMXPwtp8mv{iA6v&-'
    '#(RhAr@PwEEc>ecbLjeB48MYIIj}h#)bEc5rJ7$R(*$(apN_<-'
    'rjBH@y*iD;<_>8>^l#r`0De`GTsKjQ#JFg&axV8ZP_+>y_`7XZE#rKnpsxOJyj$aDA<4XZkA^EQ6-'
    'GKD(XuvXxEOMw!!i?6jeo|I<-$*Rk<a8w!Ys~tNC+X9zJXje;Qy&8ot4V`tWW|=M8~%B}&Yfqv`#Wbk6hhW-YC!6%iyhaNg3x#Dk'
    'PX1-g8Ew~?0o{)aXHh^P-'
    'wo08c=9@6Rfnr?%CR8&CWtFvgfLvoy(*FD{SVb{9uziIiUu4_NA!S=Fle&wFlou}TfR`bV%5IMq;>+R=w8^V%vz2iuTKF~gKY=@{'
    'U<&YUvV)9*BDw29wZC>?7w@sVuEFJ&8r|!C^Wmk)1fr!rcxads_P~LsLR~-'
    '?!7rettd<iey737akdoh>Zb{tqTW8sU6B~w~5`U+@+$9L<Gb!(Y8E`>M+<^X6o!kYf}b0Z@zT1JIjay5}i;Q-'
    '$@dA(dMpR&ETg)Jg_mFH^~k>^VNFW+tDO|1&*$4A8iq}N@i#d%-'
    'OH?{8Dkm=%mJqb=YU2TyKFoqBJtNvT!(f^dcu}mN>O(otkg`5ahS%Sg!)jy%go-`7`nUyYL3Q%!X-'
    'qMNBjqqQGgtz})BbX{6?T;<40`DNPX~Pfo<!$SuKpMwy<aUSEnTn(0NpUc`&i^>RZQJ?b161M5(vQz1ipnz!u=ou$c9jtd2sQmLD'
    'zRMK67aIa-'
    '%Qzmr^Y=Qwk^~BxW)Y8sf$oZ2a?yx#P+ndbN{ZGV{)c=RLAS(jWR*|NF{$kGCf(ku4<91GSjz5ovI10omH0cX~$pPG+t&MeIsgtp'
    'JcpMz{o07Hf0?-Sv~6y^OJYMlsRxYM;ZY{|DJnx9RP^F3lW`*7nx-lGE6Nm+00yXDe8DT3dt3gPkfxP{=}D9_hK;@ao;>ZIX%l0u'
    'E2WpP$G;OnWzu$o-z7}D|r0b_NZqT6~PLZ)%f-PDgUX=8c}9FpM{=~OcC`%-'
    'ejXQiI^fO!82hLj;lK!C};VLZ`+eKr_%1dEYGq=d%0<4gIifm_fMATYg);|-I|}7=eZrwyq=YfeQ#@;o+7qu)+O#A#f_wCJ}-'
    'pr65rbKzNu^}hHp{aSwH($m$TW;ibtZ(@$ZvxGWR9Of?x8MU*9(ie`V%E^jywG_x5x;S2F+J?psoXgyS~FkGOCX59rKBOWB`g$CM'
    '*}xNa6)VNhR&U{pe8*M>!^lAO4FZ*SaWDDi7$q}AOX*~Bv`8Gu$KPsgpx-jG5c?upYxv_6Fl_Do_Eb!jhQj;beNpcE0Z=GPvcW28'
    'AUvNq?NjZh(_W=($v14pEV#6>Rw9$-s-'
    'pEHge+@3WR099ScGA;Ysq|9Bf_pG;^4W)15NM`#a1+TQaxGFVcL6)6MI|pUuX&)v@K=HEUlfd}Ke0Cf?&vc2ti!O0^8olulMphLi'
    'usr<)yVtQE+Mgt-'
    '#%`d(!14agsjN!~L@bdwR`dL`^;z=R?9kZj9XKTYpkrGbBdg=jwoTz|d6vcwQ7bQ%_P@)cFm3%ELq2I#`b^(Or7$F=&5SUFHkdB+'
    'aKOgH6SKnLEG8v+yr_&i^eMK>HU~SFWt;LB(MT-FBEzVk?nzJeGpDa-'
    '1*h*LAgU{&z$dF?X0+<4GoLoCUeB{o6iH{`H!^<e;#G`9sDEGIhPuwc!Tr9hIK5#0EZHmA@K|KabL@#B-'
    'vG>yUpD+Q?CHqXA+2^6mnSgz_~i&X<A_AP=lcfh$1gj6xdVYB%PEXx6_2*ZA73K7ApQCNZ}jn}cdqzlW3>kWI!;=6-'
    'la18e87M3D`7!@XV?vuph4q{(>iol{r=fx9t9d{m*}T3arou$bH<Nf?)c^S$@r~7t5ZHZwv6;rEsMa%Z%YrJ!7u;TP$e2HYZkm1-'
    '|9{;$rlLV@_NK+IO9s>534cp%RET@+yHeIhs95WN2ivDFmOs^?SA_ozr66v3&j(0n+K2|#tUH|;}got1Sej*znqObjf>>~B(<3`h'
    '(nNT8U69teB2%n`kZ3y#>$dTN4Sf+!|8A-'
    'tV_fj2fi$Vc2mQ`FQBNg$}}D&ga?#+r&wLy#CRUY<4`Ubj?*<PyoU{l*ieL8Se7e_(r{XyWP(l>&+(^u5sNAuyNxQ6dR-PI&3sb8'
    'JPjxFpV*E5>!(|8WArdzNlA^O_)gJLG82w6Wf5Oab>USk!C#Lh@T?}4xYkvC%vdn`uKQjt8m7Y~FC(`xLQQf^SX#RGYTxUj&=ZLI'
    '{n++$W6DgUckd0|b4MBG;a8bH;z^6vu^)n>#_H8jWcVN{5i2#C{DE@h5=AwzPvc#@SN@l8(Oqmj1DQB`>?#l}km`wZFXUHo<la`='
    'N-'
    'js7yC!xIYl)kVbN`YqB8=eVPoLhJcM+NHP8#gOgP1a|58yhYIk@ma{WxE9^T%6f$~EC0%aVsQoQSsT)o>BN8DfpKFWy9KOEQ7uVD'
    'Ss+Dzho<v+y~vAE%YxJ`oOg?FJ<HZ%+eKHvtmCi62UnjWw~nhckY>h@Ts<K+7H7&?8~(h3vt;Tm8#Y+eqty<E8Z3KbtuZv%QOOSU'
    '7copS-Q{9`ax)QoL8P!c#MaBuFb*Z+(bvy&OE=#K05Et~ylQ9)_tfhIsA#ZBza66pLL7KS;k}WE#<=lAMbcPl-fjx!;cIbz@CUUe'
    'R%HKbx0sS&@iSUUxuk_$q&KxXzn+o4a^Ty9Af}24^R$C`JdvY9j~$#|7~nHQ_uleMJfsaYrmsOMVMJ5a0K@AT<wPXFYsmZLvKloU'
    'ybuiy2V@LqFT;E_&Mz7rWQ^=O74u<YW!M#ke65z#yZY<0kJ4$!`BAEE(~5A^H;5rR|_0N;keUxYJvYzbwcQU+eacvG;3tdI(QOJ>'
    '!DQI2%--'
    'dqF1S1lB6nM^z_>X?oQDqvNc+J1<{4d=Cawkg@4PGExeI%9>6Gqlgj6;iv1RwJz|^md%M>+1#M3N`fMt`5;dDBW|kb@9DhfWhQur'
    '@YIviEEEj4)virJSTDbASv(&K1VB3`1i^au6uW0WbDY~09LXC^<iN6IIu(I28jEOY3gB2zbeGh`Qx&#}D#!?C=ARYOoLPWj5NVe<'
    'Q&FP;@&8xVzKJ;46ecucMao&?kPRX2<OC+9$F%OS+I`d5<YPq}E40=_-'
    '!qloB_)<g|6xUj>d0Y}@Z&)QXRmOW04>zq)Uw5FZ5%lk?ayYD(ECmrf0Ho+P(hwx{rGMQ4-'
    'Dd9q$+xhdZLYGqjW>puWj#!6iqu}pQ&W#XK}qH2@&c1Gg4oP0S&cnwjJCLIHoslQcF@|CMfI4rz_jib^(0-'
    '(Vc6!JHIFkZ4(qDmYITd$L_8H#odzi+jL#me(%F(im=!|$wju<z)a_gqU0yAkfKRP`b^v8MTF?dzed1ziG@^!CbvwAI~IQ)d~jt4'
    'Q!@Mp`IPao%I)TEdRvH0L~kxhq&=KMQ5%sYKVrO3-'
    'B5pgR^HPgBp+G$%hfEK++`d4fUjIxpBWnn&A!1#zTCkRS2jH*y`|*&aCOuov8+27WF-'
    'bbU45fLwoQYK=1ny!)z71GUB)Kti~Q3LLti%3@^)4=ZeWSCasi7l_91GSK-D;sFF(F%VV!Tn-pS<Qk6rSf!U5E?NzZmTEuu`053='
    '*7jyK!B=&rWdC02yM!1c-'
    'go8ymr((STXQ2{8zt22h^Ni=S{Plau)FF#(NyjEA*XMe*BZ5Q{ZAaY>ISe8>T(YBu$NuL9ryVYA<aD&*0GU?}PcxCfdCs9U?cgc~'
    '@y2esLpTD>}y}(I4otBaOT(#F+OxQe0lAbLfNeK>!AeZIfC@gPi06nVy+XIQlo>p!^=lw#%+^Jw$*{uaiYu0}!aouv|CGRRM7S$%'
    '2LbCZ{wtQ3gJ!^rLu5n~Fdx=burE-'
    '*&Xju+s>p|PhwyjUiV~9_v;^hoUq%fH5Z&b;)X`GJFXEhMO(uSmZDt{!IX@1zt`V!Xae#SkKtRho4l~=D!c{a0^30zrkZ!VH2i$L'
    'iT)+d>dQ)Sa4d!FR0@fv=L^ckkw#9_-'
    '05f_Pk7tFBdLl}E`u`Hs1BGm3_?^brDvbkkG8%Rvljq$>@ZkrHF3_H(4eVRqG!O%FcC<E3v8g{t+J|FJcv*eg(f}TiO{lYm~>YFP'
    '^Y^k!V4DoHv-lNYZTj5BKY<5~=@J``D{_^7@k78LEfU6uON3=+ch+Q8^Sd0qKnesVACAA$2?w-'
    '(@5%drsvD*quC#^Kp?@lzj@n_TB%G5U}GR^LTl_A|0pG?QHZm_VlBd=v7!89q(M0j%_Rb!lL&n#J#@K3fpoJ!6knWpOJF8GO}1F5'
    'A!i#8Lyrch_-3s2e?BT1)y%ZHWq*%Y{uq3>S;GUc;dhwO!dd_O|OxFr>z#y=rZx~s-'
    '3%Um8U*vShyG!Wbm*cxh^s;)eJW(ECH4?z?;d14op7)n34P2G=}n_QAUmA^7lF4ondopiUd!|@7);PeeEAHeqo3c7YfRTjc}X1+>'
    '?jqE+bb*BsWkO}Ay=HsQ{hRiH0>JwL2Du{u!;YX#I@gT0o9`hzE$l1Cs^+{b$)P%ZDc5Z7Qo5QLtW0ALsW<gT$e9-'
    'J3@jZ;HmCxB~q!OI8YfA=t$(l!awPVYk{FI_Tw-;vM*kW;E=S+S??AYwd^9_TK+#B1%c>TOiO-'
    '!>Cuwl=O0YOOEdnB4=$uR1=97oZKvH7kk+=Fz@pHgK_6)ISX4YBY=`l&z_PZ-Jftosg^kMu22QJb5v+j4EJB$(DeZw5R$u%2gThn'
    'yEqih!27Q$wto;8DBY?!?OTBt_K1RIqF$pl6&F!Oc(!$C84)UT(ISu~V^-#Om%{6@FQg^O7Q&NTOR-RNL8?mMy<Q{IfoTM>W*bCc'
    '0X3o0d!9z;U-'
    'NB^=jN*+xd;!VfparrF(Gvcg=FPyU<MIW}>&sqd3~pt(Wkt|QQhZcG{8A%kM&=uWNvC$X$uvqwML#go6Xq5G0mbkXNXSNVPKwjgp'
    '(uwqHKN@r+f3vc;UQM=f)O(IS^??ivv*q%Bh?D5FzrCqE#%zZo4#u)RE(}^8Pr86n7Y@0o?*=213LOCF`Dp%Ioj#*kf<00OlS0sX'
    '&x4X(*t0~n)L!3#mYv<igl|Y$P&-'
    'hO&e<NG^;T4l1d+h+>E%Hbq!JZMv+$Hquqt<HNOVDu$H)mg4DR1=bk(AuFQQ7rTGsW0VSG$bB>sZpipq77JsfQS0)kh>%nIP0iS|'
    'y&qMRV0iB6)fH3g4|x!V<IRguRByz`6vNY&RIK+>Y^brjoatg2}2?!CE|sK|?jU$)2Jrx7XipUuqtP$HvvLLMHpzLRB?8l;?x0va'
    ';i_z1%+Eym=y?k?Qzg`XT*U<j<;?sW?;o%xN7-'
    '?ajh%{|kW5EzO5=FBlP}C{sV5sQHjJRBYOlra=>83TJBKzW%K0q7Cb~PU|TuX9=HGn!P5gQE1giwkl>zma3S)t$Dp3`q_Qsb4iPD'
    'S$fP9Ktsk2L!9OZ2(PQUd&d$P#q`f^0{AYx$~*Xir7pqmW_zZZ#5?B^a_g$~nyI>#L7rzZa>?=;iY%Y(tXJ4sKhoOxT|w<x_if@p'
    '?O2UV5@ccDEQy}c=eSp4<Sc-=MJKeZs|x)6DN7-'
    '0C+o312>I7;AhwhViLV`*()JgCxT`8mGSP$7lm#^NOo!+FIwoHmz_D&|Y3eckjiYtdh&$hv6@;v;M4e)#b!Q#Wvxrx-'
    '?=F_ok8ogD#rXbvysqRP7VDv&Z7?Ay>ly8pu#vt|l>1#@R&VaIV3%6m$J7G>W2soW@t_Q?ouWtZrk&N~p9QP_kg&O5-'
    'Sami_vwsEOv7d@69^y@DThw(?AzH(ft$f<DR&sSa)QEQ5ExdlXF{^I`oI%<xwt8R1FFDGLv$tRXAZ)h$saYP@MAZ;WDa)TDOH|3m'
    '`9etHL+TYUoo{oOmR7osn|nRX1;}gm0hX4y-;q@@3&372|TB4$_WE35^U0M-'
    ';aJff2vCd@9oo*I?jT(#Zgg^POY8!prYg{8obsgq`GI78oGXoMM)n3#LbBt%T9+xQo{w<hCPX%o-'
    'BoG*2c=T8ZOLI><>tuDzq`1<&pJBh1WofJ=Q$>Q>y0%d`;!#^gt}*DEz&$x76&DG6N(-'
    'F!MNACDpUTD$PU*>9QV}zSYdG)@N4(w;?mv+^W-'
    '~*7k@^g9Vr_t9!i&_#xrjxRO>Awg(02{a)Ed>O(0|l0^RKk|>Jna2|y%+D^TYqN+H3IDx8suXsmdloho{#az;YK+EZFMR-tfDhkB'
    '*<`q>3HxLsC<A#}?K>;-'
    'FASsrO=FmzaHA`f^mlJ5)T0n8Rs1{IlwpQK&L;v|cr!MhBcD#S)F&?vr3Y~xIj>5JNW_<BU8VA1$t+&}jgD~JNAbWDnM5|({jVDd'
    'i{}e^8;y$g+R>MtK?$i%@Vr3_;s&jZ;-B3f9-|z&t<MwpHo5>Aq?9N&*c3rh}v<H-'
    'Z5L)6mW@7CaNw2W5k>!AHZWY`y^SAStm34GOVQ&zs5VYwjs0TMw6tAsBN^t!tByn88wJ&hfT&;^P*cj+#qiiIT1ooUusr00z!pz~'
    'TvhH3#*>GuS&a14+th`f(2dQmqm&-2o4f=}<Q59ZICM(geJdPa-'
    'G?jO|eq2qS_7Kc7gIhS}1dodR9{ND&o~T=ViD~GQ84wG$sis_VPRludlc%)N6zURKeTGE-'
    '7wEdxrXU5DWGO=o{r0Gbttbje!g%}N72Ra3h&CqGEmv%qA@u1{Eq98T=u+=QO{t)W{QBm2GC;Bvvk2>Hk}o*8Mc-Vw@HT^!Ub43F'
    'EMTJ_C+m<Mc@QtNp_XvAfDfUkPCiQZJxiS&#v*40tu%~j0FB<QydL$Ld(~vtVQtu3YhlL+E;H1DayVyFBfB{4Z{eozxMG)|kQaOs'
    'FiM@zwHrJO`<~2`j&Z$5w#fi!?E2tIaO4=+e$Tkscu`ecDq9+LfPwUTul&zUX{ohyQCQkbm2=m;#>7>-'
    'Ao+w1HAui%g8Ky?%?CBWfb?2Xf3><JN%AsFJE-vpV@ulTOBo0L1SaR7Esry?W-'
    'WzQW)@GFrd$fKYnE?zKrM~9k00Q}`Dbh9Y}}u0@~%%@S$>Fs>7f=pGX*O=u}l#TUnZ<FtghLvQK}x@cf6iV1#O=`F?ozu-'
    'vIsjXUn5&(!uWIMp)x`>mAlFg`^KHO|t|w*Kr-k?#Z8o-URKeymL8n0Y+~mmep~joOxKmexJW=Zj9e#RJVNCgF|5Un9rF-XM7oti'
    'u0_VN(xh4gNR}kr?tOYYCIFhOI$_ITOtg@H%YG_*HNT{mF$Z}Uxe@Rhi(y%fs1Ek<sm|(u>P&GK9hma9x19$GYDb6nO!rzT9suPy'
    'a4R4>6}0L8z7#K*}656-=Vp(THM|Jv=TT(3f8j1u`3Do_P7-'
    'Op_&>luvr$?dxniIQ5(bz55cU2<drHP&dGzOkUav1r!@qINwwQT)t4@YdDe6u?cr~alQpR_StFac0dH+-'
    '7~PDL2um7*&Q1)CZ9bgKE!U-LW6w}~Nk_+$w@`P=oYKqiX`+{W+R@#VEhoenTMmjm0@g2#-'
    '#BxGUzI*kBM6n@%lTnBajNX!6YWxUe%Q{kr>ikg%);J~n4cYGk>g=&*W7w;IbPILRRa~Nnay81u+O2qkGkUdh}gC!T8*ceYth_Zb'
    'Jf}yG{d>-o{S8c%FBS9xuwBceqD0;9OOea6V-izm1<TshuLG2%6KtedtORe55-9GXC9i<O-'
    '7lqq&;w>Ytx6+w0?TrW<&Jdu3oYO&$maHNW;b<ET5QCob%0}+GaBDNmwZWD;vD_WRa1mCGQ;{WgDM8KdfaeX_<(b(}oST?N~_?h}'
    '<_Jt=*=m7M!ysu}y@sqJC>}k=T-{8b=p!C~(mpEd*J+MNar5dy2=6ed9{j(ok%+DqYsD$fPE70x-'
    'l%UPYF}Un9IEQEVZuR6X^Cb~*+pVUu=(TR(g4%aCRBw;Q+i08hJe9MYAM_nz*uvgn=Bf@Srult;XDj=MaGQ{n?X__YBmd#+sFw`w'
    ';eY_v{&32$E~o`vrscNJ5srBBbSDWGuAICsmqm8^l7y;w`%0)!<q*^-'
    '0oQt%<!xVE$FEZQ~^bLU$#S3J%iwd`#EWN~21TJ2iDNlDOCbQBp!&A{P$Tg<<x7z}sJvcpsJd&@5Bv|WP9+o56EZ{5c6xR&>hmV`'
    'Yd88M0-uctiJUInZ6G!g6bra(9!Q_49hqN#T!%zaUQruZlViunlZ;NP-Qx4toe=9Xg1)N^FM6IXwUx*`z1Z{#`~cKtbC(2f>U)D4'
    'phrRVp@?5?=cITtE5Q^zJ&+wLEwTRkmhj-'
    '0AH!`0M=l+hi}0Bb(N2lFh(`<{h+Udp6&NP%?dX`W=&vD5xo<}4$?4Q~$oV%+lkaSh%3kQ~5QWz`ZWt42wq(mkFkf*ZLuPME+R{1'
    'Zmgemu%j{{mFD`q@+zxMWX`MT959>7b#qY1rT8C42d|mQ#}u9J)TTJb=_T{yLKZKwt{nQGqUd1pJjG<I`8w6dZEme_LZ5*}?V1{V'
    '!P#bcZl(K+Q<@|F_0WOQ|?uB(Vs}Hq4WXTR)iCO{xwq$JilymxSGXS-`&4Y|ynRq7_LFMRd4I35=-'
    '<Q2Q{)GYY2SBTv#4O=5EXNnllc5v!zr2%d&^Q0IyT5-=Zl0=gZK5-'
    'd&Xa>mB#lGkani9fFtDrn@`M#Wk+8)s4AyRz+N0oOy(>B$mqAK|#^;3fxK(*O9g(h-'
    ';6*a`JhU94^Wxe`|;TjZ#Zv@!^|UpcW>OdHtQg+Vxn<l)n4PeD3|4A{)v6G2JK{BKcHN_qgedJpboPRl$#OIkdY>yn`pxa}o5(1R'
    'Q;%J7R-#Uf5Xgq-MjI)sv}<7__LahgNztBj51I&>>)))ZPwiNTuCHy=*nL&FZC#1kD0jLJMa*<n^&R^i7(QFvm@`ccEJZBe_66=F'
    '&%MlSZyu*Jo#PXsFvm#IYD*nat9o>JwmVSTO~=F&E1M^zO|ii!QDr-'
    '>U8$LK}dvTfNrIwq?U;AA1cXc4g^G)ax>NZBhXHM{=yT{GqCSj#TE4w>jxQ>`Y?_!4u4F;55Q?bU2-'
    'X*{R?l<AMlgH|#qRM`?Ps1IR}`Oz@B$jwgQC9S+zpY`w`fI3Hp^5##q84kgSRoC2RlU(s>zfwG}i1}7`tLIWb{v@&6*c1)X22aUa'
    '8jZy@JUweGTO!P`mO5reE!#cKJqa{LA|q3iB7tDPsGPNw*ISTfP@^MRTB$Ts$cFVS%tvzeEPKJDy?&QOXj9wKHj8B-'
    'ut|opSwgImAz|-Rg&FZzyCDg_o_)TV`xw})o&+vf+>zDz@yTNdyP+!3X$^bs7Ye{cb4>3o#x&hk!FP75TcrHc;(~`v-'
    '}h(QuV;;ncbV;_G#b(gQDpmPcM&6hhVQ(dT7&IHtF)zVAI0j)%0Q&svUWll4W2sV^gGdWv4Xe<<Lxf5wDYL?nPq##AkleB9xAAHH'
    'QSeX_LyNHOl>dElCmF+Ocqj&q0J*bXZW|0MTHNYS-dg(oRu#cbr=|kPAZ?|MD>>G)u1}=0~9y-'
    'ef0!GDVKKs{*hnLvQ&oz&>_L_OEOG3)qu&8lV{qr=$af6JG_qCcP+&L$JW}+npTv+J#Q3MA1#MySytQP!|2n`aa5`UqKPw`>|qGA'
    'b%K){B@Q+45vtRp7|H>q|HR(;uV?LeV}Jzf$-pVQ=p$h(wMurrNP^Fiq-l8M!5&IKut=ntpcqL^s%$lK`HB#D9EQ0y5-'
    'C>bFZM761sx8AbXhv2WaT)CHdP6cbHOj>EQ3+O>vt(laag$eDLWBXQ>QT$Y>AnmGw4c)8~iL$k57qmN)C4Fg7e3X?5>)b9K5H9R?'
    '^)ZDPYH0C+9OS4Z_L|p@}k#eg)gta2uAg770#18!n~K+K<eg@t8`yhb9h0qAG=t%#30N;iG^2K8{`6YeIddsEOChbHyW560)1ece'
    '^=q4E0TQaVRXhTSg{=qQlPnRg0gcBP*07daBP77~n{whuXj5`vDV0;Ja^yzbV4rwV7fsEcuZ$k-'
    '<bBo7A17SS<TN5afLS=aG#=n)B5;iP`ZIm2HqG64=Q3$qd4+J%pTncf5>j$o)Q6Jzb0%Jn7$sHts$i<KFu7bN5h923TO9S^PW+VV'
    'R0DNc%jh%|xEsL*A+@`n7}4t<b2zdA4lzk5G&nFbh)$L;|z9dFGB&&&VCe(pbP6#J<kwYCic}EJ@yf)`^QrjId?Zrf2baf@P{^9h'
    ';fVV04VXtg|R;(5&7%3N2$^oF<cfs>#1E9KpcOUz<7P$%5hbnQwOEN*?!mXjuQ%q)rHOcLR}f+G9a^7!e3fSrw}FoG((!HL@+u#z'
    'Vz9uh0F9Rr)`c&jm(ACQN_8#0>E2%SxBscL(MKz2q}(a*1qf6Vzc3n1ysDn@N0GVYApBcY1Kn;w6Z}K*2v^2HEC7OPE#EgDa^d;1'
    '!ZLjlQVy)|fK33}hrO8ael<hRnaSj(wSIlDN-n@MttMTJn>iex<5L=in_%R%eM_#X%knB-NDI;-'
    ';k#vWNoyK@yShBq!D#zqsdhLRi}$g4j4*JsRt5X8+@rMX{OKr#;nR8_~&f>~|a4m=gy&DUvuR$ODWi<Azk?i!yalw&$O;KaBg2oX'
    'JXIj?NJjn|g@|c4nMmIcC}7)YM(sObL&z;-R94om9Rn^*Umy8`i3Al^2>WvIVyOh)77V+r0T?V5{^PxA<75sub~H$OB-PJ7zsyE|'
    'JQabtBv1csQ_<5&(ZqbD(V7DdZ`eJ6~Bg4QtQzsd4&7%bA8F>yJGx27&(UA1QE8Z!u4{_kc;?lQ$zOY9p2?kP}SfJwFad0WqJAEs'
    '<oMPVw}`o{EVk(I9i0Je1%%jj5`QQ)<|Z3vDyqu3a82Vgmo{of_Hv!x*)yq-aPOb1*6I3@*yxXRe)Kp>-'
    '{tQ>j@vIoN8o0vX5s$O72N>OWh*SVczB4G*5&<_Bq<=N;s=w>ZF_lbemcCcMkcst{nC4*T3bd%PO%87ym~(xm4Yo40QCu_vAb%r2'
    'XYRg>O5Rm#VWTWShU<u?)obi^Y-D6j1`Bb$aoz90puYSNSO!D2EYq8o}T%f(wGvE@yS!fc}hOi-ytA}29b8W4(|wnS>K(7&|#P@i'
    'Fc3CC7h$t<-qmOp&4Zy9WVl$>X#OaoOidC0k|{U&&qvHZd-'
    '?uZ!4+9Bprdr?FIlEDmHH8QAKkCu+U+oCbcJ$Wx9dmt%8dmsJtQfIqSRlc?MP^T+9q#|CW-'
    '86q_KL&zFGDjTBks55bsXu$CY(5euxw|ZFV}h1rrq*ZU;f&zLEW8aKfxnQlV$5~QPiwZ#dgfawDp+dO1|ZclQ<Mh0GpJL&Ag9<Ef'
    'QMJN=-'
    'KcLSy2WM%m`&nL}0AyF&&SNJZq1UYxCL3HeZ50wJAjzVfWYB{G@zW6Ws!NtED>J2Bs}?%MJ&grJ0v`3}ZJf85`F}Hk8{|m>byzF<'
    'BK6Iu?ikZD#nSq$CPUI+)B9Dvd1FX5OJDv2S)NrJeMIl%TEoP^R4D={lo_mwUVt4OrO)lL>dtE`#ht9NEv0u*Z{eT#>`kT7!3TK3'
    'orh)0B&~XEEBSlVK@H*`H|A`it_ylcw=7euUDxSUW14W&1$k)T{4bvn<~~CEFh$ydcngvE+MSw#8S10U=C&qhLRtt*ZQDuW~Auev'
    'QBdzdtE#6Gn@`HP%_)GptNdI+XYrfLTud`3YC{<n=VY``ip*Y~7X0kS(dd_iCs?x{9ZAe|5Hpc4mBjED!V?0m(SBY~6**OvtYcae'
    '+q15m+D~U~?x@x+IBqeg%j1ot`aJJ#fJ*)ut)0oFC4PD}c9KnRyDw<s_yqyv!C`CC3rc@1g=>dd(;0>1~qL(KnzUp3|>q-'
    'Kz0$8N0w!|CM9#7~=ng!n?RZ@HG!};ZWpIDZ@mwab|ZKSzs*%*D1tNvSeK-'
    '(f=Fr?|&XBJc0s<F8IZfLY9=Y^32l%ezidYdfY`@sfsi|x(0Tpqja%{icT&WB9jv|MW(oa*^=A^BK{@Q2~C%W3X`#Wlgy>xCDNXB'
    'B3Oc!W8s2(ePy&!fJPblSdf-'
    'Ytcnu>;^Q|)b#XM+skYdYUz7slHN(E4Bvqa|u9=e^Gw!vR*;<cTHxC_r`Z7CD=<1tr)YLsL=+U0C=9g$%Yfr-J_lr~!y5ap+>fJ@'
    'Hp_7gAvr5;Kfn<w;b>U5FJo_WnACX~*ei3MrtF9V#152_!ydJr@FAuN#%i~i78Tcphe3kzx9$-&xr2a`EcI)ZZCYyep(eUA-iKFB'
    '}#t;r8<tC*wF8rLm<qdLDf?GrEhf9|+E$}11UMy?bQ*zNAxV=9I5?GFc^(~x;>@T)_%Zh{pTuOV$0U2)(mwf~J#@YqkYOu^qzH(_'
    '!aq4%)f%Z#%18b|t;o@GXE4}RblMNYf&^B1Hbq{c^8!`*TDvOi!9-~C08MKn71PJ96M2P2PVpKJ3^PmZ1a31Uk=mTUE&-'
    'ZE07|%$NLWN9J&ZhaaCy!>Ezz_}%5&{<q2^wZ>{jY0=IBq3H1pZHU;#r#PFH==}GNF+8OzHX%&>=#>YDUU5k`Vo%`1r+acXycBVw'
    'Uvs<+kToPYri7d=08tD<esGaCB0_-*y#}Dlf;9U>FO}aB9ad-yF**_^m8<&Lp}@y2Dexyh|ghY1#oCo0<-'
    '3_#@nZ`|`R;Vb@1GyzHRyh#c%uWm5MdFR~4_#v0JJsk{x2ue=erd$Or)Fvi^iFqfieHS=D8uoCuJDcn)PR@~G^!z{fCuXgh1qE~g'
    '<N8t!WqwG@Nfs4-r*`-'
    '!>!O9rp+Iuy!>&8q$)G1jQ5AKOAO;N5q{5BHEQKENk3)uHatA?B{1v26P{f+q2lYqs(W6o9XgcJNqG!S7FDN=@+kSR;n#RigVLBN'
    'OZxt9aCp6sul(E_P3D#dpgGo3IZ4!#L@h&^oOurhQ%G#HtKWAQzboK5eags_$(I==*#>r>|^t2)-7@?N`-'
    'r6RUnZ%JC&Sz3gQ#k2BWz{P#=j+;VAsRwRFy~v(d%I}~QD#@Tj43{LXh5D;q$t#KTBC3wZrdPyPDn?9+rWwYLnx&L#61Cof39-'
    '5&P>*%ms-eXCT-nI_tC9w?+`_VVfb4wrLZL>#-UCR{yyz5rIws%)D|0inACyFcI-'
    '5G|vq=IJQq&;DY~nb6`GaS!BJ5^c!DFjMcoI~#^d$Cq6yJ*MRO$q$OFbBwB!VgCBL?g`Y!5;3i?BVZ7bdINvNb<Ng-'
    '~Q@Y&kvM^JIq2kJL41>am2Cp;H@(%vFtuU}8%ylZ(+eQ=^iP`ugyhU(WqZM7N3IN@y90<j|;#4qUNp6=-'
    'y25VFACVBCJ%^OeynbmC19CoeuCXV)y)3|^3xR`D15CpqA*8V>nnFB!7PWI(N`TbX^=AR-gg>#TwDu6exQvyGMDTVC`9wTP2HAA;'
    'W;RL`70q?4QDSAlc*_W}z!FtTrnQg{`2JEtLm*2A2ctt+Tv{9K8VZFO<lEPov3-'
    'FtRna8zBvgwTP7T<dFBDyORiTIVg9Bi6E#>X&Q^asJ<DVkAI!5&f(9bYzK(%nqd(#?S&ClQn5CcVg2}hb@m{{r5|r1M1^zE&Ttzp'
    'Fdt^hkPqGVNX5+)88+ZWCJFxSc*V>w~Xi%$5Ujl?}l>V+1z>QL=15>&qENNbULY9<~(qnm&KyV%^&`k^FFh$%E_})>DTY?@|Iaj{'
    'cyA5WxntA>&$HCtXEMaTLNc6lK9LtRPK3w?gPTya^VyiaW&@+==V~0s<M@j;Ig9;8`%KZ*mA@Zdm-G_l*D)qI;yql7)#=R5tI*>D'
    '@=Fq?uHaoYiyO)6XH08`r#rG3m5w)LKV;EV%xNOD};c&Z1X=J0~MFJxwsFp=-'
    'x!1`5n5CgaNTfu9V2brWDC6I*a_$i@Jj@S$H<7dHLjsrjW8G`p)#N#4%7~^1;rOr0>QJ@VaMEFm)|F!H#Yhsp=zgLonlw%#H^))@'
    'W%&cU>P^(*CkE0t%hOx}*;PpWpUCZx6u0lY9eTOMu)lyHO3Sq~K7;7Sy+vUBPc}V|j)VQah=VOQqG#{(&3t!YMuM0^S2du$R=2qV'
    'jjau?aJ#fpjl#Lo4iLIDy}yCN(!DyP&@N?&OLKdxrtuc6SJ>{8!cwR*LX0hA<FOJlPsyi?}`QsicF$;`C8bx~dXb9UpK@Qnn86$('
    'em#RJ*n*gx9DH#&dHpHXCdteZ^I_8DV=&r}Pd2oGenutIj0qEndi^d1TC;Qvf0QSl(JrMxu{icy4y9z(U-'
    '+#})x9qxnGbolc`>4QR_*P3#(XGM3p;H+oqcS>kx{D&mKezm+bK$^ef$?AbB8a*$I`vDC><5Eo^~!uT0a@z1D!BtALW)+HHWaJ8a'
    '*=WUbpHc!~YMS9Kdx<xVdK^GM<VDkEjJ2>Qr?q&St7X(-'
    '?)%My$!?#KI$c=}9#Xzqg;nq&m9Eqkk<yM?}v^9EbSicKAj?=kG1e3r2sB{(}DU$4ogQatTKtIkklIl;su&5<oNxd*K=sqCSzQtL'
    'BG?xgHTH1xC6tPL*9q*5KxoiX3P;)LA99>(oY=p02RTu38_fdYaH^MkQj=W_J$qPGbi!KHA7!;J=t5h=$SyXel7?X0&yqL-Wr+SJ'
    '`9(T%j<4{-'
    ';qXk0{H6^7~StvASXmH8#wkvfZEm`*lAB>X>R10g#xbO5fb!Sa6)?5T8ha;%T7V*Nc!1o~OOF=Pu@sT}`9TuV<*>bv<##*23jbPD'
    '6LoNozeX-GfHkrD_v2xB3W7${@UF2)k?EeBEt0d1RTwdH1uWxU&H7}eaAd~nMLG~Ttc{;9^vO$XoF*zl$Y?boHM&7nP#-'
    'juCdu!Yu8#v|c=KJ9-hZOAQC48MrTaC8u_7fjn!4F&2>uz5N3rUpCBXlFMb+E-'
    'kQj0T`)ZR1>Fuq{<EBWzHWFK{5N>Dgmmv17s<!Fnzf(23cdWmlYt-'
    '9*0EwdpOMKqnId>*>E6iv>a0`O#!0jVo$Gu+%*a)$9dpBrJVu?z5$BNdQ5Vn?^+nFP_vQn<6{1un?qvM}Kl+>DxyZ=L<r_U5MqzQ'
    '$xV7p~?Y6PiTFf?SD!Y7@XIyg)yOu(9#f6&1WM*zQp1Tsgb<l=KRXWr50J&+{lm3qsR$LEqgJVGh`uMvFiu{>t#ovnpNL0OR&1)i'
    'V;F#j}Ag)4&*erfF+UMQ<;UF*PcRb1jThlfx7u@@EEuV9^O8ouHDslkf{B!wctbtY>U@XEfe+g0B979IQhQ?9u=i+uBT=3=x4dYN'
    '7`p?%D7k%mWoU;hrBJn}khIuSj$J(9F9&TVb!UTDMeGa$|(xuWPg8V)+%vPKkq(?Lss^dK=BGQNaNRP1&df9yn96#=05~!ppfCk8'
    '{&gZ5`}jM7GbSS?k%~fbe2wYRbgck|{V5^f&cPIAMVo@KKmAiWwf@R!Nm~R2^8j3X|gMvMtFhDdMeJs@G1!#q!|H@a@BiOea4j5V'
    '&tAEf4~rcKK{A?f5?FG8Tj|EDT^u@8Ud2BnYt0VjGE5alg&Il)v64QQ?k)hPv004^SLorMM0Yx4_jxFu+r$sj@2E)GFzldoox8G('
    '@7m-ll`4IZ3F;m0Bsc4Zi~+jjp?~kaLlbNev1_=*T7-9qI-&NU3^`e)@I8J9wLurGG#+vN1WgYvw$jd$Ho|KuKpKT7xubw-'
    'g5*ypv7WJ>Jecck2G~A8+G)8+O9t+_Q1P1@PJ@)g8!pSlQMY-rYUb+l(>{a4S+e=KF&|{ZE7+^~c*(ybZst(i6vbJIJ{BqQL~$!S'
    '%tdk%D6RU<<QRy%5Z&n<4A8BTl&A=3c2EZ`1fT^f@q>CEa9`|MASR>iu?>y2Rlw<1jPRfMMAkG>pp{kutwtPI1TE0M_aZA4xS+kv'
    '`??E9ci`(_CkW#S26$4ltC>xx(St!pyh%E>r*UHY3lCQGUeth|t&(@7w-&fwW<{RehhN#I-#%#=&OPu|^~cI_r&?+^c6l-'
    'e%%$yzdOgOIGTKIwW@#BZ;@M$F?_62TRUh!&YUvOd0`k!2QJB>|l-3-e5-'
    'IQeOje@{89D#>4?>`!?D3QFAk&?HzC+x!Z~OBOfX3cKs2FcJfFk<lCU>RMxX8k%C28o-!WW#lR-'
    'KS%f`tGW(us-<g?;7-|}W1}yzx{tB(}_#_Cd>J$T-i-nJ3oIy{3o>h4y1VH{X5#>j;<Xbxt=O914oSZ^)TtxiK`Mb0|ML5ir+D9n'
    '$T%Uck0lPDU0N?@RX<N9uvY_-i)p9%8rxPThfn5npZa4%1aUsW7Te`-'
    'NC8dDyMNu&3I5uiBzH<K}FInU){lIWK`KXgMp~z%%zb{V01XQniXG1|LW#AO&p%fNJ3<ozXSkrW8<DEc)`tmxo$hg6jP@tWk7&GV'
    '_n<=t(2#sqFP*`MENI9^eu^#s84g(l+1#tZ0tx8WL*hpMzYNnQh79$cN?m#_-_7^4_+fZ0*Lxn013cX%-8%4F^#g!M@<k+M}-'
    '>H75`;UyLH%n!}<Tz^z#UIBx?%5aN$t2mO#{0r~#M5sVoklr|{%D7(k^qlnBvxA0)JEYo_XHs(*<oU%Eh!ts>Qn}|le_MuXdG9ER'
    'v9_sfIz2L>E@cmaQ7!h?U}yF;)Bt<?2;`ch0N7CT*_WPVJD~8F<E7kBIjpn0t|}cp2;NRvI@P;a_tIPq~Zh*9LcZfqMi~=)CNN`b'
    '8r$ytISKN_OmpE>ZULa3v*1;%El9Er0(A4IEL7vt=U;vv}BBYigk=uxyi~Pup(q)pA6+|VrK=qjsy;zOkH*Sq1`)LcBF;XRk=c(+'
    '}<`zQ8Lw5k+l$hPQ=woIU33WkYy8NPCr}K;O<18og3KI02rO0_v_r3_}A+wOkP4;x&%oA8~sd$?)Id&l-(-'
    '@u#T+Kk|<b}nvQeZgMX2M>1lOZo*lTW&@QJZl%Qf|=zy?ZLM(gsL;)9%m{ep6-k!iV6=8vETyICYXS{>*H@-'
    '5bMS*Wsvcr|9G=k41ir8dvS~URd`@JDOdvI9*zW$4gPOD66p%L~FY%_&eF#{f)u8Fb(PQ{|7_AV*z0$kryaS1sX;YEKtJG9Ek7+J'
    'XRjI5%E1O%u;_`#O4lN4d>Y@aoajw(uO)RXUpFU;Y@zX0t{b}lY@M=rfdf;E^G=!CIskR_cD&Jo^;Gu1v1CB?;Rnz!_Rfl-ASeaU'
    'K^R(XO|KN2(+0ULBt>p6L+<e^W60K@g02x=R#_LQ3G^2~z*=-=1*zUi-{>=`TDltXAK1-Ddd7BhUw4yu0Sw19XUp5>sUd4H-'
    'XN(0i-^?5owPOA*mmX&vcu><K!-Lf(2u?_&EW!~kTuLMBcxUK;cF*8K=6Z=<Q(k$OrxuPgW4gz4A@f5-'
    'aNWk_`KDx4yhq$NY1Q|HeqPBEZ(UawN2u{6ba7y{~$jX=GHgG@L5Qd5fflMyoObMdR`zQ<%jfO|mK_nvWC9(1LKz1Tvid&Fn#zq4'
    '05G`tutLzf?0x=MzG!@hcd<k5Unl85WEkpMmD@VqQ9~;upnyL|J_w??+oBIwAN&#r}m35-'
    'Zi)SZNR4PCEOMu}+c^0%AFLfbTc1_J49uBtP^!Q91T14t7S9r<lLvaL`DWwC-5QTZqv9b%mfZgH1<=x&S?!adY6HrXkvQUKl5Cv-'
    '!sk$<}kw(=5&uX1%iJgpMn8C=cNt{5A=N#_dQhm!iLo{)KDspy|;cTV8j*D8|QwOMWfubgIvdZ-'
    'm5NE==)ScKq2}bnIDsAjd<K<t%%S_xC;5u>WhC02FI5SJTU#EUg(Z7S+^UrRLCBcVZ1bSvXjCBYPd&35FP^CN`QMZU2Lim{l?s`4'
    '4XX7iP`2iNoF<kI>QFf**z>qdLVdGBICQX8(rTf0EPSE$1%@jT<_qz^3@AYD5T-#~<Meak*!UZRFo{F^dPs()Tu5?^6l8~?gg-'
    '^Tgm)Sy8D5G%LV%4<TEnYsb=YUG2R!S;-'
    'W%dF9<W#hsA}Tv(Rx)VE$JYDxat0SVoTWkoUNj094Ub1oK_&tq(eTbA?Qhc0*;u>)Y`?r+%bH4Izu9BfXQccHD(^S<J-'
    'pp$0!Au8#LD_$<ln`qqYaH0S&2^qc$lm#{su!Drn-_R!J0PZ;?Q7muZCz})G8M{9`rcbv4yxx4H!l>@VX^QE_`bOeJu{{ZHA5osV'
    'Q!A`0|GyHBb?4v#RgD-!3JK$r+6|tGm+ZM2(GB#k&fNTYUk+^E^_e=5rp(<O6t)(1dAQr$_ZK7t%<r70-'
    'Dd5q(OX6Cfg7o5RTgX5mm8v2M$YMOoY4IXlU$2)V9T>d28R<ted-JG1s|6RHuog6ex&sPjfKycV^asbRMCY2#&QbLvWqcVXBCs~<'
    ';0yZNYH_2gC+)EXVDodU|jQUlU#QUC(oQI7B9OmIp$*7N5UQuvU(N@Ks`EY*#vgGiapU{ufhv}g6fmrTrL{lZJi_~MF#wOg}&k<-'
    '_HmAD!w-'
    ';SKDj%1h(5%;gJgkA14Gd~ocU@(s!fecmw^bvf;1b{H2oBn{(Ob$`^IGwMX>p6OckzFeN&bWp=dV@i{=W21z9m0<e^qL0)F5ZzXd'
    'CH!Hj}QMbaj)J=xs8)`*`>h0zC;ubSL&=d;v$%QF*@}@!k(Hz*yCfa6zRYOmdcZudHBdlj41e)7l%=jOTx~bfwM>1LNeA;$pG)fG'
    '38-'
    '<jJ*VnF~5Iu@CYuqv;N`{x0ETMcCft_$jIsJZI^)sYWQ5A^k$GXa|eT=$b~d$%#WNNVw(6Oi9teQyr@bYbaDfwb)wNPn>%(SMcEO'
    'uM>si!a*=@*w9kVU9nj3mEVEv!v(ZRS*c=qE292CBDu<v1C0kBpn7L&mIK`sOG`g1teq4#nhX2L#HpZY%OJqR#yr$^ChLhRMKo5)'
    '_&wxK%@_M_uYs)lg^baqe#Ih2YZAgS;cj`raSp7wyFhwlLvp=as(Fp-9_H>flJd}vp%hj-'
    'J)AL&1OYFj9*5o1}+ObsOeBoupzEdsGMFI`O?weg=6e3Td#3jV)B_OcJc&~xEKAveyY&Y{cM?Z3|E%GUPFdtOiHcw0q`~=lF2boZ'
    'J!hBH&*PVy=d^K{ikE0?eG^bu{bSW}}otPEEmGO~WKsH{Yv;kULGzJnNS}C^yC;&hs+m`+d!y>MCy;!v_<lWzYFab}i@`I2@s^a9'
    '?^v7IzbSl%5BbF*GJO{zT!6q3yJ_`u-'
    '<>uO+10r^NVdOoZbNgVQ!?KF*JXvkflvN<0!b4Pesu^noN6sNO4niXYjDK_f=2IjCi9tzli~}DY+B{1yICHe`3hM`;^I}P8cZ(w3'
    '9T`3EwT;!p`}#`;DS9|?mL{^OFmuJaj)kBw3t-'
    'RojEoK87;)|zCT`~ZGk9ZkLF{xFV2r<|km8H`Vg{Sy&JjNj5)vr;?P#Mwz(+uNh}}v=tS62PGOm}+Te~uyzc-fg?^_-'
    'u0y%=udLcc?VX7|9meGpD<ENMpZ1)wDuM@J&UV)OrOCY+IRK$Zf2l?)8_4c?%7(JF>k?~zAO=%Lgzbi`@?v9~u>B-'
    'S^z*Zw!87#g~IxkL}CT2nMC(h=})$l#x5f1fs5L@?dD8qLRLI^a7GX4OhR`$jRo`}40(Qec|rZzC>sqP<y-'
    's*llZLT=yC_>{jj06lp+HD%=wr6e^A$(*Pqazz3#8h{ZM}d&vmKscyorTj2*^-'
    'yd^@rDR#$>u&$m(;J097|;wtAzhcS~c1Q=!(CM;h6)p#VhfKx>ITf<<vNJKtW<^X8%)C~fCP7`IDk5ao(s=5lohVBfA;)W{uibm3'
    'f~Hc1x~=*#@H>_dSI0-'
    'k@`+?s88Xr0RN3|_e4ZGcB$X6vI#pOPHhuEFn1DnW=dpj6>N9DOCMX9TBSI@xFP)&XTfj8j92BQJ7ER6Ch~2#=%O!yXUL;12YuXK'
    '{dp;VD+Wv3%eoB@5P8dOlznNo2pMp6m${m;@5&HxM0b3?iD%KAL!t^PFT9Rmv-5@REWkLJwy{-fPg`49iHKeXwmaR4*E%>NV-mef'
    'Pt{K<+UE6al1q4vM3wFmtDUscKNRzSBan>*egtY}PdiU+yYVH2bd<qK8_=j^)v%>Rb9!iY6e;1Prh;fSocnJwpy?I=+OXDS#4?HA'
    'zEzzIY^GSy5xiUP!4!#aa58Zt8y{Zp^8_45$K_W7C90OOUO;8I~l&>*x)&w}{MK*cVBkss6daw{vNQ6b@Xemo(WTXd#i}-'
    'dnJQ9vx_%<-}7@*~)UpP;B`<WT=|dMyCquoD{SwwG7z5N|F%8@IRF!WnH<@ohniabQ1qFMO=@epfQ60vAUgu`=$EEeIx|l0%-'
    'Qo!0;4!4WuoZtr+55?--?0>!hgf-djpXR>;<nW>KkVBh-G7hFeolxF>`1=h<8-#4@OBspVn=aKmaEi&2F)Db~J-'
    'p)O`@j}KZhMCf*uB0!;!M=*IY^r=LmtCQ7O@6G+qIJjSzPNp_~yVyzrU)^A>GD!@eu;ks>Lbc10eg}#Mg>JNB^qP*7;zc%D;HXTM'
    '5FMj2*>Q35I!h%H$Lrn~N}F4ay!MA#hdi~bjTbQm<y0q&%T3a*KxKM{#%%Cp9!uu`z*VV@#N|bL$qz2j{knY*j=%05PUyMa?;Cch'
    'UOB^KWbXsQ10U4(u=w2S%9HP^VIkDbqNq-H3ga64nB%yhcPu=Ky}a&tBI^)4QG2}mhY0cg`RvBZh~ma<YD+qvxIk0dPVv6XQrU-'
    '5l12=Y^A#&nQ>yG<YJW@nm#Qd*BtH(4NEUd~sUnoCB5TK5;%2zkdXPPmRi1UfFc;4Un!UDUVr`UjW`|XEU5<Km3rl4cj}Joxl%uG'
    'q*!1BHn-'
    '=>^fGj6n(q|P!Yo%<b+X!C|*x~y;SFS!Hl)AfbCzI&fh;<)cS9KO#&1`9?g}g0kC51mn?LdVIR#U53>@Ci2eN4=|QaP!rp+x%swU'
    'W8xZ2FooqxaRGFNgOjOv7o_^~%K6v4j^M;PFD&XY-'
    '<~^bKHJIc}%g#$f_F^CgrE%4w+`>iK~XP=WAyd2tjE(QD_lM$g>PvOEiu83T&yuG4^>Hn1NRI0p|rs6REZhU!nL%jB>^thdtkbO_'
    'uAY<R?B))uz`h7fV_%KKbl(OA;0v3TVp?j&4GmxhzBo2KOf(ie(}cn77{)YvWXg;3_KRWRO*t5B^b*#0%-Fe=`zNoQc-'
    '{IT7{7`9vlA{6#nXL*BRT9m;M<93F12;3AmAq5JHkX&Fd8FL@3nTj_hY)^co)7L<BMM5n1QZCTBT;-'
    'V|%H|%Jiv2Fh%!XJxgr};Jj9g(bP(CChwSv|Wh}wbR74N$<EX0A=mY~NP)C}}6jk60T<czUJ3-QUh-'
    'U9}svQrYSJLKmCWgva1xHD{+sN!_n^=2QknHa_@=k5seB&Z4Xd^i=-'
    'Ey593>4(UH5VxxhYSO~>jFh4ZMYMX6tGmS(Fs9^waeG_enWa$d_>=!Jxe6oo4)0y8i9nDb<@~@fh5+s=HU5ZhSX@?1O(EKsM-ToU'
    '%yip}m-{9t&p$bMt!TO{S_+)SQBrBtm;yWrh4_`U<j}Lnywo6jWNdt=pEb;jbN#EapjMeAYaGXVIS(o2(?5u1y(dJ$)-'
    '5U6#YJL=bPaES`|T}bLDb`}-44FgiC=-$M9EDf8Sr-Mokz1pH7d9NL^M{Gh`>0ph&tRQ3R6*zrU$OELU&}M`PUGgDUw!0+AN8R#U'
    'hA{q1#a*oZI|b&i<;6*I8`cgMZ7Kk>T#=xEqu#s+3S_;j|-'
    'its>X`q&2I=2h5YujLYkZd6ZbZo=rOULD=0swPDsHw)Z8^+(jhR1tObbrW*$BSxmr8P)YGIzA<Vhmas{_GX8e9*jLJWY*`J;x_2n'
    'sXhe}wNN^naS1YSZuI`u|hTh2hV}OEy6E6fkR7yoW)nXcg#+=|lK|MzR8sb(yvlA7Kv)|9jf_JBA=sBKLnF%y_Hd|iU;etG#@mH*'
    'Cl!220Mx+P2vT(P6Q$f5(@>l4-'
    'NtHvYMtL~Prqf7Dt2kA^$?x&LJtrkl_k^1ZmTOp~xtp~Ra^w8gMvfM{=sO!+naZ=$#CkX(oM5O>4aX3#I1_o3UN|Z}CwsOjZ{Q<Z'
    'j)S(qN$3DLF89M$L0019a4;NZcr|lESlBX>HIT>xBO_NNQY9&)!uFB(Ki=+J%FKav6bWx4IW@|na36zIs)pqNFhQNk+bbD$3cPKV'
    '%`N>FY5fvi0vu%+{M5_1!k=8{e!_U)m1I#Ou$TJZtHFcTha5-'
    '*48GDogOE=KNB~Ktida_2=YV&s;z(;c7_uc#+^tGLv7RM4R@SZtTk*w}MLZK353LQ0?1k|v;?Evy0{Z|q#wJ06Ekf>))0tEk6HSf'
    'KRx`W@rhjbdkM}LRpa7a#^7v|@c1<;n@(PbZDzWsw>o(2{@zIw2b}3DRzX+f?IhAqbiBk&aL#6n99(<4V0Aj%Wfs#u#Ng@%bkegS'
    'fK7ebMG)iMPjW{Mjsi<3f1nM%Rs-a!W_sCl&fa~)H`+8Ebi<E<${o+B=Wy79J^YV^Q$vm9oky2Q;T4bX<-'
    'BtE^sxcJuS)Q7h%#CMGupB&L=rTOm-'
    '=|Dd6}0KeBB>}R=0I%>IxCD&y1>=8^}PdyaDv6Y0N>Rr^f3yaRADE#G<)nhi5yLur}Nu(d=?mTj!SZhK(th;g7{h!)f_X2hFGSM$'
    'O7C_$upOF5Zdb<R*c@=Kox*HUPNDz&z|G;6z>m%j<B}yyn-'
    '`ac3X?u!Z~Uvg3qaJlJnkd^YbL9L}(h+Pga`={^7Nq(GMFk*Gs(Po1Uk+Tya6*DO!^6t26naJ2nbT+*fAp7WX(oYXgF@#PDcr&&+'
    '7<f)*CJkz?cBejf9*vW6z$1<dKx$gZBlPyK@&p9>1U9@rrw4wDeK5+6fzgOel{hlJR1wU5REJEMQxw!)t0lfPJdN{|P5hU3r?9@d'
    'Oi5djp-'
    '^f_{2MQ^SaO<HTZYP5O~{{=WnA_}|@2?9yigaNr;&V#CKuDLQb=ftorzWr5%^z3g3dQd@sy)tHSaGNZv#1ZtORS#@}DoL&IIaMAA'
    'y)Bij`rr1UT&la(#pa7jJaS6+qv8g)?@z}VLl^s@P9V^@@G@SSK27vw>zGiZ!-~|HK&CbJTV6D#P5_WqB-W-'
    '*2KoB|ba=Jswh+J}OROaq$K=uOM@TK^>z(e4R9o_8Dp<$tbG+^aF%&c^=Xppx*cif+3?GFb&j?H%b9FHyI(@(%l28NQtNvGk!e`E'
    'HAtFhiIAgDXs8SL4{`QFDI5li&Y+0Bj=rmt)D29xnRtY|E+@BaDQ0rePM&2KAo2p+QP&0+%>*|Q33GD`5H7?6l!0B6&E4RE|WPMf'
    '+Q-'
    '~Pi`$2WjWD5hB8E&kuCF{9@(2=uh7Hv{v@5bp4w6uve?&y8i_uy$<tAXDaP=zb2*)~f%0!G%PP0!wrkunYJuG=Gzg7Q@vR2Jnu^~'
    '#2CLm+rgTD~99cM&Ik4l}w55nT88l*i9c6z`d3YbXhWz#HfsDFGb~$Qn<95=o7cYGn&(C6l<yXo9>fl!<^T21uN&=Jx|eW-'
    '%4b$(a>|XhWlux^vJ@6gQRpP^K#xwgxk2B`XRrNXa7ygQ|hr@v*x_;{FgUU~*Xj2{*uC$4fl3NVzzfLMPbox4+LYg0|W-'
    '(oa>4$A;I6F_YD@5Oo`nPuIxosKaS?37H%%^JLU#LCHm;_5qR=pZRtNgp(S(kU6g#+)NT`_Zf&}{n~zirtBo_IxcPoepu1EjljIW'
    'N_l61oOM_5Nt|clt9A**2PyJ+2lhY;Od6}2Jv=p9?xJfCC<Al8@dfQ-bgD{Q?LvRp2~rn&5t*9RBIo_UUhdqpGxBL@jw~w`vmj14'
    'j;Y)I1)BpCG>f{&jli~t`BtqE=Gi2(SLZ_rBVxBoETp1|^pPvm57xZ3o)b(&391}*)&J@^bQT9r*I3oV$|1LP<uF0DPcS$y#4>TM'
    'L5Yd{G(0nECl;4g3WY6d@s<;aNDDDK-vUjJ`V{f45ffFZNWvIL`f(12=#AU;U>=uj_N{fN^nP#9OvxLLC|0j-'
    'lyh^E6o|=y_sBXog}*)Pr8PW(leYx#;(u*Q<!HdSQ&cxX2s<LZP!j>Ob22f^ooZIBhR4oV@`ss3Yd{EjZQ_oHBlxJ*t_Rixh(Gh&'
    '78O>0z`bMvH=`u>ll*gkK}&ZAE?A}i^{}ON*PL9UA{x)6)`$Cs(?bLHH1SeVqbZtw1BYhp&>Lh0B<#p}3LC@5kk~>H@rP0XzMyAB'
    '(JsaesoCJ*5VPt?^|PupPTh|hE={5A9ia|3k7)8p9Fz(i5+nhe2wI7oLWLsBJ~i^<x<2#On(jGv?1E>20MiMg2?qkhn1fV~khB5|'
    'Ar8G5R#7U!Fiv1#PYX(Ymihy@Ww#G$S2h7c%0$$e#-'
    '>+$Jw<fMwUgQ`&HNZ8RpV$XWT@igkq1w@@Ze2XSL>CW!uzek21+a&`V&s`g-i`T6GUv2Bw4MW9Ncv-UEW`?k_t{eL!sG9mg>f1hR'
    '_Wr*NgQNf)Owr)NiS1yO<dm`X`4zP?~h|Ca7{mifPec5!|9eqS?usS`Lq==8b5ORiZ}h&_Z>m=P2ijJTCA=U42yOG=eUY#~K|C2v'
    'bn2e83SP=u~nIsE#nPrP&bPS-'
    'v=aLD5hOkKEX8vllK(M#3lKoWeTt3{(tG<mfaYqUA5Vq@;8Tl1ucalkZTY5ou;?5XgS)Zbd1s8kmeH0OkGydopXWiB3+Bp<vw^on'
    'EL|szWtw1&V}K2!*<lx<WUA>SBjBy3DF(@()fsA#>FAC9{1OPtYLpZi`d{WsMp3ixp0=V`~<HQI_r5dRC2l(%7Ff*cbp3!Y2nC$0'
    '>t6k{Vt#rttPaJv-Y_$EL%ipcCgFoKMjvw05X)70bEtXdWH72FBn%i<}j++B&V}1>5RVgXAEbQ7Lg;FGSipcGVe3<*)*Fv5@u{$}'
    'HsAUaw!!9(A#LpOHNECY+Tlpvc#KCpaPNMAnywg93bPB$K0dV59{EM2hbw*}W+?r73Qj*I1J;4LHB9SDa}3<f2X<woe#D?9{>qZb'
    'T)w4GCu$^SY9%f&`^<JSJsPndP~ve=~JYAwWr3BIMC(PE809w^7*USgO9iV5CRG6K3iFQj=#l90W?Jq2_nwNgbI*oP`55&9eX04Q'
    '>#N9@ZyBQ<xSP4x(B@9_vI4IgJ@I3`ob^|NW;&Q+2h9S}{@s8oc0p_h+^@4L}Dl6`c$h+}k8S*CvOB=ozIGFf~^8Z<vsYN^&HcP@'
    'F*qy4@@LLf)`0)mse$E-lO96bd4Js{))`iei9!wj2mqs5vFN5a?TI3AR)t-'
    'kQ{PZ80)mdB%)_2lVM^!3LoITQ=&38?Qus;Xq4{yr#S#!k`AxC^<X|UhOz-'
    '(%)r^S6H&zvc^U_?UhqvfKEnfi7jB2L+mwfEPO%4C9i;K$wnJA?A2`2uSK0sA{|do^k|nFAV>Id33Lo<?y}|@U%-'
    'Y%FiJo}O(B_T3eG`ytu+bhb&}#%Bm#WOlYO(0swn*0M5rfv-|fDgn#-&q+8*#)yYN<l9f-'
    'VVvM3jn)vIXPD8iIoHAA?qDo~3L2HC2;#ipv;q9_=rMnmKA1C@oI_7JKlq`Ge%Kv{hB_n7j^(phXk<!j=ywB&hJ7mdh3NnP9cPAn'
    '04Ja4DyQOOm?IFo4``Mb@;++g(|H;)5g*<H67Sk;yNVtiBL#-X23F-'
    'EsYO51DJQgo2WeX7w(0~zx3DQcUmUCCXmY89=XodN|xkMseeq-'
    ';d65}yKBjcL9C0Th#;Nqf!yy>_vMS@4agq#XNPV2szBD$)G~Jv|z<c6(Ms8*NM2A_R8jLDw7*bY}I*A}g&xJl3<{vy_}NL3KqsUE'
    '=_pTC*XxLV(?~+7)9_yuHPykCsW}gyEWV*hY3I*Wkh4NjD(ENtqs{H|UbCd&Vc~fKlXCgNQulgT3r2M?+v61{f`+1k8*Dz~dLpJ('
    'Md9;Qe>Z`kGi4EA@%c89~(!Bf2oNV7Mt;Xyz@+HZi1sHLnERM}4$Q7akkiG919KKzTXdgOyl?vz={f5CA^up@CE58rs~$KO?wlw2'
    'qa+*J6nPmn6*#fR}3~TcT;ssN+I}kqJ`H_gsvNPSLfh#w?h6-'
    '90#yw6K9FfI??A8+!xIaEO(mG{Y&qwj;gZ5{;}N_fJhq3P=gg2_H3vSy<AnEntqKwu0ZW>0N)i%gEp7{!0~;Z)8+S&cGH^Ukv?(g'
    '%Ton!@wOw-'
    'C&Gb+?*t@PMvLzYfq9r+GM}~JMQ*3wEh0En)N0#+K|p}*e<G9Rbw6K`@q{iHprd?3iZ!tU7vZMt^e^K|MP$U{b9xrbAt+Alm$?8Y'
    '8Zk^GW(_Lk6b3w>ee$jtDFrGo;9%dy2&^zUKV3Aeb2^g0TIG9OitN$5D_s}HvSrce1w;+!Ek@S(NJvYU$bt%Hq7;17&6*{_us|v7'
    '&7?aP2T&}7JFrCM9SaiG*=?P!3yzx4LQC5YaxeD4Vi|)TN9tf09I{bb}xdIG}_=-'
    '*G^FfC^%PY7|yR#Yd<%v^1}ep0oiN!S_&B0EgOz@sCaIC-S^w?Pa`3$QmO-H_6|UhB`qOl=vo^g9NZ#;Xj7vjt8`WY8(m3sEuw*!'
    'IK%yu32E>grhi8N`C*M8)=)lKl#Gw!YYaRHvwOdP#kFD`?YehYgJR=CB;1zBYaKZxbHv#}k^Pf>NNrKbJMrep%)d$ZCz0YpCL9!}'
    'daTMnpYc73zjv(j!;nVa>)cU>P4VR>DMn;+E+T7KTi+t_E$XWcgFY^@+o32?nQ}w7(&C=o=R#fJ03r}UK$Wa#Oex7(7`GBD)Z$Xy'
    'S8OyK#echELnjfKc_@-'
    'nat%Bh&k}co{#yJd14BYqmE#xDS_NAjSRlPT95jR0i*k<S?4Z1V9|uI`lr+8HK6`>{e2OXmgxpfUcoKix#HkOve;DhGr&rDoqhQR'
    'Xp&3wQ2>W@LTh(*B$RR@Feqks_WoZO}Kn*|85RF0+rID}IoPsn)FeU5~a@VL?H6HOACkoZSd&A~+`mn_hn`}SANxv7rhJ_|ksPq1'
    '!)IT|ihSG5b2~}*>q5}-8N?vjVmA8XjRI#c9VGn_Q4F^KusD-'
    'z<S5LFD*1h8QaYWQT<D_7&{IrwpxQpZP&z+4uFd^}KEu3*{*=EyV>JWT>R?c(taCuC)EFw7QZZ#-<H%-'
    '$~%HTEO1+Y#?iHVG_MbgohWVZ?m@go)lUwPlzsMmh|^BBLsOp(VOM1W6eTou^a3c?vyu~Kh7<{+Rl)X1h~Y8*OhJ<7{99BE}<uKr'
    '+%XU$lD)OT(>0NpE;9S8{XlErdjUQbg)wf7V<?%x2>e@0Y_JPN0fG}WWOpGNOV_;Es9q;)n)v@lkr$4r(jECR9H%YtOHQd-'
    '#K#hmT&9>GXu(=LZr3AbPDsx6NePo`B-'
    'nT>b~{qbi<Rx<X87ensY0N`!55h$`)y9ORj{C;GvEPynQOs0GwD*l;&gd8SDx>ii=MMj1G&3<V(Btq7^TGmuA3L_Z>D6o*3?BdJD'
    '_fD7JUzWi~-I~nt{KbJd%+HZ#-M5%3N4J;!ek?1f5u?&cjL*^ti3p53>sH8#o4|5ysZY+7jA#o@+u?nhXK}R<BjLax;McFNtYq-'
    '9s3;4_w8hf4;1RN5fq|qe!Xi_w0sDY{hOpTU7zc)gskWXqL3x!LVP7kok4(svz2j}BI&JHk`yM$QMzf6%)m8iVg8nx7MbSsZDQwZ'
    'X4}+05KtAogSBu<$3R)^(j@j}cbI>D(1n;uu<UQ}m{w>l5%-'
    'RkFwGo}b`?rWbD(Bl)O7RMwY19ouMsP*_yMJT5{&UL|egsb4(Y@Cey}c1B2P4f~?AxhHYfQRITojScY8)!!TNk2D@XI)iWq@wsU2'
    'R;YV~9};_$Dfv6+Kdp?S=1&o82OaX=GU6XYu;IWr{zVLzqd25JPh@zM};+iqqFVGE<G+`ZW%tM`pl@GZ83>o(|X1(4Pm*p7mi5k~'
    'B{>YywTVVO=}ZTz0=KDj8mx&qb+reAjgT{xSt1E$7>Ic1?H$JlwTXDHzrw0|Dp`fvF2AAtD#lRpv)Jh?-'
    'vx7k}I9&Jmw+ky&8W<?d0^Xc3(XI~?q*a|V<c6jLI6h!}tT%r;H&hqN3c=qMT@+YuISkwCaB^nfr)b5FJiI3cWxk{cnpC5w<LfTt'
    'CqQD6)JKM?DpZ#sM^4qbgzD;PIc<~hJTk#7FpGAnt_KvFB=w9t$aFWHiS;1SP3vpfU^M4YXKcu9$`CMO61ePi%axX|}&hmH&i8=8'
    'X-'
    'ov0$^Vcae#b|UPkNLvQ?G}sfj{iv{v|Gs6mO@50UGQtBU3lRvAOLDLB<N#|ljDd|oeydS8!6RmZP_?tobj78Ma1dgJMKKn5ArZU}'
    'f>8Ye_~!c(z$rv{9V{t|7_2ws!+e_$2kCwh;OG~}cQSo}e?ePKjm2x6goz|076O_UhLJYhlGZqw2iZ+nPC$t(@o|>^*^wOvy-AC^'
    'aa2eJ&85-'
    '~wR^|z{a8OgtZoplh4<@7$OlEN+M@)6hT2#=6nqTOXi5#02#2u34Y?s&KPr{TBQ>b8NIp|zv~XHW+`||r7cSB?pVz~zMkjHh&}?P'
    't{=Q_tgM3r?0U<wc&<}=hvTX8dq{I+W0R$M-C^c-'
    'F`c9GYBZfy}RuphuOu_*Zy84Y<#T+=qT{ZlsORfczD2Hqh!V<&>lZl!C{<6ODMN(7|i^|g~*k*}(5yNg#OAW+tW`8!zAZjg#;J{4'
    '9=}N(e29Q4PlQ<MG@{QvvE325yr7=9Eg}b<~V>43Sz83$2m;U#|sPF@*KC<NItV>0WvLUAoU4_LlKvBR!D;(|K+)AK@ne=VsmsC1'
    'irLqM|RCP#)yageZd=Ut<Q43k5i0nD)w5s4GwmUDI-=Jar-m-'
    '*0VAR1%n5bArBuq+Ph@DjNZGcG|^367I@l8V%Bd%?11A##`thX`VYuGRnr-'
    '1sEIF=6F1o|YYeO0JKtnr%JIy}Cwb+~2<KX7_M*)Eb(>^#na-LjsRk|$uQIVnI!=gahiXcq;K@1ulq;TXHVs7cI%Hh@&<heZa5Br'
    'G5X&Xk20Di}md)g*rfcKq5XL5L+H$fck}Y<_BA64sogF+s+-'
    'rN$F_Iw1eLxGH6Xh{ma`7!?rM5ror`8b?6W7W1|zKElz3jDTZ}BIk#f9@w*ghw;n9G8T#t7U(>;g7xLEL;VHJo=~z50x5ZaqGuui'
    'i3u-B&e7QC);ap!;$~@5!{q(Bk%<v6Z(yS~F*yS#Eb-AHD%KizG;IDXKR-'
    '<2M<nKx7ODpN3ukR)odYF9@ujf}|Coc}i1Wh}7QzVTDMI3$BuI2pGiz0bj@d_u5D<E~G<!i9@&J7rm?$Dqg){qZru{yP{;-'
    'ULyN2v1*0J)m72)#@h~gxQR4qM1n;hv<fO`yt`$nG>!$zA59nGjvB@Nm{o=tt!J=>2F?_rGe?PzhC<1CJGD!url_5$fYjle`5j)V'
    'j7Rhml?u2Z<<VyqmXV1x|~hPhHwzl}#(S{7guLoGw2F-'
    'jGl+*o>QGYhgIp;aea6%GERgK<=@ulfFM8olk~h*Xfh&bJ|NOq4XrqD2Vax`t$7F6gBhJ3yiUbyM?<b;1^s2a{G6ta)Tt>hqC~cm'
    'GIF{9!pK!9NteC(()!Yd?eet_TFIAi&CTW04$b6lYu!9z_@8hJpo;n+CL1-'
    'k|$EC8>O0d&nGLR8|aqfX86*B6a%s_SVp8vWaDr0Z-g$9SmNy-'
    '#CGfoph4#9s)ro!Q&>%>|%CKG%R+e5r&MzR|PXhIU2cfqh=~{=s03=i6xqwaTg*&Uv#9nbbV{$RcQz}p4drf_*lDD1Ts`D<8WyLn'
    'd~M(*I6B$#tE+qe1`qNbuuwaWaxrt;(>yCE#<mV_ih@g7uFt<Z-'
    's3@VI<XmAK+t~8i>V=JH#CCaQLugE3@f_VHp?MNVo=U$n%u3ipT_88aAqCn{IIm^5C0*IYvMWwdO%vi{c)dQW`Vb3TO^f@EXQEIX'
    'UBqB%|9YfUXuWaY27*zwi04Evs38iA~0QbqE$rR*{??JS}`bkQNv$#3F&uboiU=qnSW#rA$F#j&C4d)Bs|Upg%MvCtyn~UT8fd4q'
    '$LUIA#k|c@$dx%FQ|j1ZK2dwn0oyD3k>H8nSdk-z*k3^~l0-'
    'MM#g7G1ag}oB<ND(8wxi<DzW(Lbg&#M=ymj2DI&b^IE}yAsCAgwUK@l#m+nH`}YaGkQbO)o3_aj%o35s%m`2uq`M0alto0ZK8TrW'
    'MMWbLqnRRZU_-Lf3X40IHL18`IZ3AuiiDyYw*nw35e76#V*)8ht^k7beJ*eB+kbr?hgV}xoiuyGlR+*(L*L_84}KeC<3WT5H3cL>'
    'BmxXps9H_&M2BN2`n=ZY4v4C-'
    '*$dNgL;I$6ip#U1mz4ks6C0Y)?z+W&Wyi12<1lPT+RiYNrWa~WK*cHpbd_DBM!KWdqWPD`HJ?oT`jzs5$hJ^ok|<7fCh9KT5$UC)'
    'hT4(~j#?z~AxVdg=qUatR@i@i9*1kUP(EzD&MnDr&_7+8@PX1X2TSk($1p4eNmg<UhoiEy#b^!pwnncXmamgM-'
    'm21@M#Z(tfwTotWP}l746$qXlDbMvIKIhHzdnz{x|@7#$*GvI4Q$QO;HpATYc*x?Y+|Sz>&a9aL0p7BY3@{Wl0zzYxzkS<R5n`<C'
    'ArVhO3C6H`AnqY00jZVR`w5$x4XyT-'
    '^lggzgx}zHxhGj+aP&^EWZNOrU?wI2(|E)Djv=#w94joqN;88oHS@Nj5Plfci5tK?z_jWV&no?bWAon7!7y)b$gkghm*s^8I6biX'
    '5%n`O^ooFl1GiKF@V_0!&7lbanPE&W&6cTTec7x0F%-*U>1IWeNIG7aN#b9VzS`4NW~~*zsG@vj7${j?$5hd>euISI5`-'
    'g6+$>U7`;>5sj%+}WmD$8PNw?xv2@kO&_xG_c^4~L9a^jdR1K2;rWEU$@5Na`zN_J5ZJ^p(hK4E+hEtF@`Q0YcC8vPV^lkEX1idR'
    'WO9W?y{fw<+u2>szJ~Z$bVtTchV}5KQ5?dt<MPW_jKwe*Lg+z4KsFzB5aFmw|1#t$Fj;6rQl~*;krXEdaVcgO{j<~31KCoG(0$IH'
    '6hkiQVy#bsDg`ff3Zrjs4RpAO$n<jf@(WJo^hK7p8WF}R}|28RaSWN<Si1mQSMBI%r{elp}+xIDOiSOt!jB3L75pnBu+g0Ms4Fe%'
    'e3SV__GKoe5Hb@*!Qgv#{`G9Q_m8%TaRKuuEGo)Ro#z>(A2_PIvPCuif-'
    '{1_2e_~~SUccfxpSM9Eaivh!7SJeLa?w&^BDqOG4RY!YvhOtkV-)e|nj4B+&Lgr#Z;-'
    '`HeGI|0fu%z_a@F`yrn*#ttZ)^Wjdg$D{lEVFK87weMvr%DBR2Nf8~h)Lo@^fmkV!fYMJO>P0v-'
    '4gnlQRw+wF)W0#t^uz`_QPn&;GI07<tETkN=wr2@;jurPE<IE6#v&gZk`_pyVtW(F2pCoUu#8j(k%Ho(!&0L{TkKrqU(n$;XjL9#'
    '_9L7F{IG4zP~V=S1HR8v!`!8$cnA|UM&fu3ZoFI2pbc|&3F5)BejZn;BzMp%V|S{fAwz>&ngj1$6|QU_{FF{ZBEe&(Eorom_>0Ct'
    'H=H6yCPIAODO?<FQ{48Ed+)7nXqAFTLAaqIPbj*LC)Wc{^`-MenABh6%M;lk95Q_?sDrKpzS%5Vltd`=_L+1(_1HR@ZW5s1-'
    '1rHn=PYIxVyIIEjDcO`luHfIE9w~6}seGFef++m%8QmJOl;Tz~c6jZ)+hH1c&2<5c;&JM&2QBI?FLqPm-'
    'gvpgvr#&)}tdk82C^k|DIpYuLv-GVf15BdP{e5?;_VfD~zYsqTjKl~uf~SRv)xjTRFi$RdwbW}vGCaZ2B}=N2HExoSawwI8U?l+x'
    'urQXQ7tBfr4=LO#G3o)%P}CNnPZm}PN9i?hzxMegi0;B0O<KvpgJZl63sf^tV8e7H|FCgt23!lfYNQn37;!e%_a`7_>hZZQS8P?p'
    'NIJF_Kr2#~i{*@lfZk({$nkuda2JeVK!Zb9u^KwDE2RJ%D=-'
    'L(rC{zVdkP9gLtU~+d5s1}?NHnVu}m{HmstuIKwwdFw^Mw);OQv&8}Js?VSW2P#xEc$U^-'
    'EM7Ec?=aw!+QG{Ioygq$!GYm4|V2xSEh$urh?7HUZYYQ`aAV9Fpim^dv6D>R}8NDRdOVVVHn06Kj?pNwBjgB<Sq5<8hX3H#BgAaS'
    'Mg$sz7;sXhTG);KkxIcMR9XO?~(%}5Gk3XrWa>KOYHjCrJq<;tW3_2sHQrA6&FT88nKyPM*dsqWG!ybMNF9X(3I_z_2tyqk*E6tp'
    'inoeqLu*3<u4r6={JQ6{xRl?2zZFzqOmqm}X@n2NZ&E>5tsrUABYd%u6eUMfl;N;+oF+eE?OwiH;;C8>~>6Qm{uOvHz3C?G%@xKg'
    '(m6hI(@BU__T5-~NvhIx&97Ry7w(iEGooXiPLu#h<!Z}FK4d@-ud^b}7A!-'
    'm5~`Uc7ZrfHFWjxAkSMGwu2M03uqGHF~DE)MYl(DqPrFlw>3Tw#o{pjOAdPw3`THTW~-'
    'Y34zqt4mB{ChZrhm(<E{EZsr>tPxX%jl%(5T!l<&L@TW%qoMb73P%DPuO`SDlV2U2)sk%&f!;SV9ns1JY@4eGm5E>^p)m2fe~e#1'
    'Wse*wXCXo9BfL=?Db~;$^Ezifwj2LA4>2{vF=|WF8?1pv96nOy#gl6=VVM>s*cr4{4bZYopQEb`lYygR^9H{d;}_fpyLby900I(&'
    '!j5a=&$c<VfFVra8~JHyiD=QCO_ATugI-d0D0(CTI~5*<NeWUx-wb%~FK!h_K4rNm6fkK&kHGwu`Fr;G5hQ|e2})P>L+^y)#3;3B'
    'iY*bCDkT8u6_Nw$dnOF}b_%mu(glf?lLkJBMF8=bETiFk+{e9B)SK+O2)5dr{dC4J7|V!WcU1w%+y}a;@efe{Eqh!Iv3Yd9jnwXp'
    'iah!f+g7A&(e=ZOH~1mV+1ORt9L`Ry+aNHMZe&jQ(*4VRhoH#4#n&$U1>^?Q#M$|dF_VoXBRZ%{baRQ+REqAz!Z!{<GJt8|s}D)x'
    'Sm*ihu1R`93N}u&(=aG-sw?&8)qpJmQ_I#eR6YF--E~j=EP8TDTC74~*o9Ixf2y-<io^*7&Wpy8QCvlDHY(vFC$Uo-'
    ')3#E^*jV6_e1lbW@gmVAYZ{PNK`AOs8k;XLC+nqh<ceP!TftD^Fd^y}rg=#6gTsE{07%Mai%j@(soaUt-'
    '^hglr3em>ozdvDLK}>5;TW&X?rHXYQKl9|2H=B5Q&0Y1VP}voJ8tXX4V^*BmPB$f+5a}4i63(HpsU|B`I37|mPil;L8d7G6TjT+#'
    'n-6sU#B^@x{$~KC8W<hinsM{KRc@MW9YEVA1v!LF|tHwf4!{6OlCX~Y}(q+o0^!8w<h%%^Im6r@b-'
    'lGg<|^pul#=RFTPe}6yo%Zqjl#*uz2@}G6*?cw}$Cu_NbnTR#L>Gn!E8qdUs5_2>!T^1Zs^J3z6{Fc)faLY|2(9Z$U#NgOkU9#~0'
    '%lmCL3XJOZ}1Isf@Job9taNy<CRpu6T7wb=HHa6L3mj}YgMX~To*(VZo6H9cY*UNL`tt#_lN`t|eAvF%IaEe5mIcmI7qPy5J9R#t'
    'obW4EXVr0Q*(T(T|reD~#2P+?WK-Kj=p$8)wv!F8-'
    '0^t9YQNAkjLJR~<#cFodQac!+0WoEo7@nS6$d;Wg%*Z1ik9XaXEd;T^uQ9zuc?cx_JVnT!E-#%s&$B@L5V)ry$SRs&I>m8-'
    '*8i8@dvEFTa#|UMvHwh!I$0BC~NfEVTd?8DdpY`oDeqsI;*~U8C@-EDQG<!<Nz;@6yk<UEchwhbEj>=z-'
    '{;Fh?+;kkk7BObO8|Q~-'
    '43>M}v<EK_aCipe%+bz#{a!Gzutw}heo%Mpbv$8n)!ie?*oH^Bp}y6KPY;qOU<udgYC&G+@tFv<OSV$@-'
    'X`DUB0q$Sy4XDv_nc2XZ|XtHQb(X0hlr0BKr@qdRC{~%fN=^6uCw44>rvnTjMkaebF;dVDzBILD?8;fqJD<JpQI;k#Kwd#pFc$Oe'
    '<&1Sq`6q=k&2L^7#AJx^-@asHxOGs|F8cx6oKf52_3}h{SWcvyES8;r_WYjz4Y%tN3(UypHqy}G`!D3_F+gXc=#MgS?iD@ep-awv'
    'uo}0`~26>KdH0Z7At~_s<okgR>%IW&OY%Afmn~3&13UXtx9ykp=T55RLf1la}5a888lZLs?=9HfiO3Oxt}jxeelNUx~7Hn;A#z|f'
    'W`Kj0ts37zn|?p{j~mAg_2D50|dk2?Kv3!MVP3PTuN{61kUFc_EBHD?}nD+^EHK5ID5_}&k%S2;PI}tcz)sYC7<6@;)|aX2+de+d'
    'Zrssn%x&}dEG!?gJc`sR=nKH=1SR@U>GYspRhmF_84)`k&5Oi3#0p(pPQ3P*>&rR9nn!thw)QEUOHUtOhAnNKhOO4vpxFf(m=|lL'
    'q7XwH~Zz4j7F<Us{HI0c?r=+95>_VV4~bKZq2FsT;bi;*Ac|hDlO~A22+rAc}<qSk^Wo((J-'
    '}_3^(JTudmQgK)gv3GHzYX>W8YVbN5H`^p^^t9!C(Uer~{X(D@-'
    'mfis?OQ`^43iy4(v@akWljllCVb}T$6p}|f}_;GLF33OKJP3J2*1kc|WnCS(ol8;5H+gl4`^KeR!DfP*N5ujoAhq_1~PPnOXcqtv'
    '>^Fz}efK<9J?x=oiNssM9u0y>r;&aaX{%U8D2W5ZbJv~$xN{(Bq!gP*fZ<-'
    'uzM9+i@LyzrMc+w)SKYId*z(?}+eCN(AY(<!M!0WH4n9#Ou_3vl9zY_^1!1bKxzC2RUNumQ|-'
    'wltA)y?Kr3bu;3x4hXKQT<mFKX922z3TaQ*0Q3n&V>z+;P56lgV;KJR)3&6^?(kuj|s*IB+YnD|8{YxA$>+&I#G2b_cmv$N;;KE8'
    '0WZ!$e%B*bB{}3xfc!9*BDSU9NgQuj|S}(uWQ%abJO~4`#=56e?Q!R48p0ym11f_Z;bC-MY`!HF1V0l9&|~|6U0*`a9qcero61{`'
    '9WdL1(V0fy!&w}$W**Iz7*v9By|PtphiHiOJnJSi*CGzdf<r2avWod(dTv(Te^LvkE?GL)B48L<IejP#!h89>}Nttv=e`fJI{WOp'
    '_o_b9z)3G*5Ss_i+hCdx1!as1j<QK!Cg#y=wI9V3sZk&k&E0hR}?GT1fX+hZ1ep6gscky(~qlDbm(E7lWkNa`DIA$+3~bL;5<%;`'
    'l8)Wsk6cl#r!es5_zqw95DT%;N0T>z7{M`(!1EpjmNE*=BlPkEJ4W2!-h-5j^N|-'
    '$ulk38{4vIik&%hwm&9b5V&E6q>I^Sc{;nhJQb(6wWr5u8k(vhox=`RMaCF!22em|jNSM*kt$;|c`0;=Pjs)Sm?X2&Tt{{_v`$y<'
    'qc}djHA-ph*6n<^#!UOm2%aXs;&&rZ#iRbJszO4g{!%I}%XKn5-'
    'x*!5cBmh&&X=+G7Dv#LDi!NKeZv~}Dd4Kz^CKvH4Vi?1Zk^Ba(jK8o%Rnx{Y+;tG|FSB3h=nO!c<J?bW*t&B)P}vL>zn+n{`rt;>'
    'CHwB`%kg?t_P>SQq<ewt$mGcZ(%y+>V5@$`Owo@B4oM=r3fdeLXBLTe&`0FD={>3ykC>l=L6<AmI1n5&%L?N&c?E<5G}O;yr-bT@'
    '2K#4Lbb}5QPy&*zswf%@@_@RPBT(urM~5b$GD1ICL{kakBqbbjIbb@aw{V4Jhl(2DhbFSOPzn7Dh+Mbu$Nv9eMMmiBuWi9KEM=q2'
    '}R$IR8R<((_dV@6xSYMyX742AT4wM8}3CfU++QK;jrD=UoFbk04XScsfHbS>W5!9_Z`gakJ?cy^gvjBD!4Hr3zp@Cce;>x{^l;`E'
    'Z)pxV>CQ-'
    '|NOu{u}L;T4G0{`?YYu%F0R0Vb{$UP*AQS>t{>o@_vM)1x9mQP5iYkls4Ar!2yMpI1x{_yI+fe=X+uz|Zacy;9NDme4b`8IWfiH~'
    '*+V#6EML**R(gO0-6bH_KjKH_`+8%gilaWU;VT;-'
    '_w8eW;!DH6srVp^{~J8Y!(}jX>!+hXk_*)0^k&&vvwLoL|H{5^?IlFuD@4N|eWefc*s1rc6080Ib0z9_yZ;vfSSt|<jGTtVEp?*^'
    'oldv;VGwgKlU%{3)%i*?a#%p)4IS`}rc$S+xD<yWP9oU{)H!<nINNtT^+UmONyXPUDS<ZwVxa7GA}E5%Soxz<VYISF+2k5-'
    'WiJ(SJGi@6eiKeSptZedeQ|b*b|p9$SX030Ff~#_OTo6U;Rl+0I!`mIMN&NEn>xHde9~q0Vv_024q+kC86MS_QYiZ%FBR6nK<=i2'
    'e&Sg&JWP33Kg+Y%A*|yS0v0rSx2`{?a`A3no?NR`c~NC8Pn<n6e#~I-P)&23u9f-dxo-uLGUx0?ZzUM}9LW}S6_;l_Sqm))oSNXN'
    'w27*a>pxU4v3&t=)#00Ie=lL*=Gj8b3G>$hEm47uJZP!BDNGRG)sM=OO<Yv)ULd+HxUhdhv9C$laD{WdquHg{{dt#Xt!>X5)k+P^'
    'm2tz&Z?J5jsSc^!yX5LL@7;^n`(38l*Ue=`-qa_emk<lH9LWMzzocM8DxAPr<nl&|^)<d-'
    '%Q3e<yFhS5L(^?c;P%NVer|oEa`CuLOEA(OacXz>2{ZAYq~w_dZhfea5BDk3ew^;9(7Hs_0wiUXK&DA2Sva<WlXRyx&~n>4R|TqK'
    'F60vO-X^2&w`W;siIv%&^WWpOiJSsQG`p5E_6>{C-;e2zF7)(n#H<B~Wxi|HI#zq0P(^a7iu~}Vws43GK(-'
    'E|n&wTyR+LgmmEp|hDukEWv*InK?olbHceJ|+Fl6re>vT_z#wH`Nt+(!`cohl;L=>f*nWAZR&Qq{+S#AJjU!otjVt!b1M41(;9WW'
    '6e(|;q=X$gf(O5FGsHQ7-'
    'n6vK>1+u5XcmWyJaKs{IuD)9Sbd2%Td%>54S!clhQ5ajXnfwfEOxxkuYu!(&@dQhexm9D)U|6Rf;*%EahK=$Kw-'
    '+}2eFi(9&KpD`f*b2%otcf!xUUdT1URg&LPB)!RBQ+{uKC9GG%djaHJ6VOpOskm>*ltBuvVaY(TN#9+syeeg0h|r9fJlD=e;~cD8'
    'n5_d2t3}D>RVyy%-'
    '~Nu@a#0XLvl_xcekhJv<$deDb?2#f#2v@_2Y0~*E$CEkxWYeq9CV+)*kQP#hPx!hAP8b_(VBBm4OsnCSgI?)&#;5jv`pQ>HYDpP?'
    'qh53K&Z6k-#(|gK`npZQHsWwEEWSVF|6!-'
    'WYT)`sH{o=jQ0WV_P>i7GmVYNXaUOKwf~ul@N#f6x$O?>i380ecDZN)3Q4y@DIfBb<XSmyNz3x9;WJ&F0b7Uy+tYHv_rwA9MjdN#'
    'a^jbn`uXk=CUsFtS9BGUtJ$8%QDQyz?$mCY%eL;Byiz9BvV4N+niU~;COlf6n&z%``*X?l2(Ifg{rW9+DP6LPcgMYIkWVXwCnB;t'
    '3}Yg#W<+!UU3jpm=@LPw&LYS*nRE$oG8SmO{WNkWRWi@oc1r)4GSTYRDxwwqRy7Zs$vqzTS1)`cr<NW8+Hi67KcVgl$CT4nIL<qn'
    ')lh#tH8GfQMAYS5`0Ow*j0L{`%tDP(4(qM+hJoGRJH<rQ)Kn!DgO$)yiwewGGlslw5UuKhH6;RAd(HRt6KB=ak{5W^V}7cmk8Am_'
    ')5=82Cbd+l>1ih#`W6E8|YkZ(deCf@o7Rysat5tb4u(3eR-CC)pXy7pr7LCByQVg>(!3--drW1Ei>ckJ{Y4Tg+*Fl4)kTG8-'
    '5GWl_pA%qX~ovOI|uPnn5&?r-'
    '+cS!fb!M9|4`2x@hVm$?H!H!w>rA^)W=L9=D(6K1M?6btkH%LJgGCJ;Kj#B7L_mCQM4ZkiFE&r5LcTS>4-?-'
    '}(v3c4U_GELy~hzfgN&UUuI0f?0yPqFR>F$?@@k(?x0|d}RXGU<Z!w_=QSB5SA?Nf#Ikdch}{5aPPOn$-'
    'vc?o%uc<NAs|{LJYrp>+9Q(pr<d}tW;4@3s`kTZl8a&k{aEXpedxedNVd-'
    'N(IJkR7g~=*O~(tPmv18?;=#T+$IB62U**}@clg;#+xWoUqK+C=p<~FZe4H>7ct$h^u@$lJ`_Ad(PS$U%==ya1W%rei8VE=bU`k^'
    'Nggl;&GRzX)6rp{e#DPL?X`2H#-'
    'f55Ix3iK@faqFlsgU8sS2>+v3vpu4CN`b5%gP4%%&Yvr=oH{4`eoa`Ii@bZKSk<785s!_k7vTvIHO4G#ADUA#Nlzyp(E7^z|3MIl'
    '76DcP}iXib*6AtD5563qgYhP-'
    '*}!eEP?5zUxRA(rmPAa;*L%r^UAnCf)AoIS=a2zH<B<H3(bwoxa@+JS#N<eCxPZVt>+OiIZLhR$+>`er5;l4-'
    'cFquC!unSVf|Tk;jWO!rE~xroyFOsNdkJ;xX-?>Ms{UXLPC2lPap6E}$?n%7su?T~?<^R<N-W`g|<TK)6@B>GgT>*ss$)g_<0-'
    '6!^R60^+wpEG!2ipWy;?Dz$XwbQZqKS)=aLwP=(q{i<iou)Ajgg)V);`+ND^^dQ+fi7V9K_h87SSUd$#LZWTeB6)bba;~(M*R-'
    'oDJAKrGN<9l`q<F=><jc~%ra8Y=DNW(Av#1amNvISliHbJ;Py)mJozv>;MV7<U#>-'
    'tC4$4jnZhQ)bHaJzS@m)<IdBDcw7Ry?gXUtl+I#72RbX3`jWVq1X`1*!>inm5^N#H8ArdVe@j&@qxF`Q^@w*mQbDOZHyh13f0Pm~'
    'L0pr(40bDgc*spX$yRw0Sk<So9^3^WIqx~W2U9^@J1qaT{4&(}9S5W<|*pxb3VaJ47=Q*xFqIn6gtr4w%yvq)PXJBKmEw8ssJZct'
    '$`K|ll3J^+ZA$ftCEw3yhZJB~rHR2xB8Q?*FB)2ye0@hA;Vg*Nc)AHG$Zw@|AUKq0gR8&P^Yp;!i<_PW^eDnbSF%fsf(w)%9(&#U'
    '`dj0!%@lg^i2<+0C8JL%1194c&m`yHtx1OZrK(OC<N@B*}a<Z=@Ler-ue#NrFbjZlup{stcjxxl9_bBD0nE%3a{m|MgTN4r&;b;='
    'ckI;IgF2~~|6N!hkC?otUYXlK1!Ukqeg>?Kr&_jpC9_SBXdA>r-gj{W~d-'
    'TSL`yr%6*qg<_NQz59OSus%>eP2|}s5mrMr=Z=cW!WIKl@`N4@4k<QVaaxJn8*~Ph+10sDp?q)S2T4LWw|0#88O|IwWsR`T@Z`mG'
    'SE<9@}kgqupm};A(iD=7VM>W4(vQ@(84|j(~El338!cXl%2S!P&>E@?9Sg>$G1#F**je3=kz04?ucnfB#(WB@{QVc*1OXs745<{9'
    '+j}3c46%(&US)^x_}d|`c>Z4v~rbMY{r&!@9FV{IFv!-U)r)bG=aFYk}T@7^Ag=%J?&5d-'
    '{^dJ%`QZO)~bJ~gSO@$#71j59YwtaZLsaPDE}};mrTf<tNV*Lf9+lo%@*gXb~HkpezW%(zPmwdc<KK^yDaCd6k6Mxv0I_x8}CB|i'
    '2{<hC0=EBQ(ZSBj_b<?<3hP!NnVLjtiOXp@?&B0@@lulci>}j6}Tzuu=-006uDnsZZ9qS6kaBDo7(Z3gMZioaV@MrzRr-oG6Y3%|'
    'IdC=46oztM1e?SU?~jDX(><G6Y}=vJoOP{8MP1ZfC^fC+pmU{U-'
    'tC7ZR(c<TxGue8rt5M^VmQ>K97m$0yL$r3)ZaDRMJ{d`DE0xM3@*9myO{0_LJtZ`^e=TzO|3w5&7ZCtEQjW#|=Qe%KCcbs+cJH?v'
    'CHQ`RjVS6tI)bW5WiN)UX&df-hA9Xugh~OAKIu5tQv%#3F&1rO0gGOH9WK?;PO+EWv9WV|Zy~w|Mh_2Ku-TQ%Sg0Mr<X<*k@DJRy'
    '>JxD|BG@plT1|u46_X`Un~HJ2`K7K81J^Pe8T58j=KM3~n^kN^*`<_W+4`cjkU5L|)%ryk6!pf5z@<v0~^V@PkK?+G>l8Kta;<s('
    'I*U#tfRHaBo`F@GS3t$=jP%<1C>Yr_c*u{r=ADOt1+n(`VS)dkxwb+zLF8SP2xWV{UaJkN0MHdN@CpMYEEYwH+-'
    'tBIcvSl~80;Dd1Y?d12`VN+D(NK<EJ0dvkyAH?R3Ggx{r9hG0ylhRgG-BPdL)s#8Z5)<qd_D&DDuBG97HN^D}X1YYX{WY6W^L*b!'
    '&U34*siJ<(lGq$bglu3!%%Yd`Y0Wfe9N>&@b{$r~@9d6pWV;@@T_7)j#?sn&u(ab^l#H?X`-'
    'uWqZ$L`^sIhfzad%C}(?%PjOzKH9*`eJysqoD0t-'
    '6_2pnkd^11^iqyCuZ`k!YI)3huz$)+0@UU>I}iKsiRZk4sArH@SJB;bsiwCufv9fq~Y()7-HrE1^3y$BA9zwyK`GbxupdN-WT|2n'
    'm)VpU{MIWaNG3quH)--YDT`g?%uS_ymfg$uI_7stZzPwIn{tF<Qje~c@&f^{i|P#*^Lwc<Sqp-H0v&8XLc%5vu+-'
    'bWBjvJUxyb#QYKugM1`g3nuF$~q2CHCl~w?xddk~I9=95b&<I0y@@+pFl;jsI4Ym6=THeP8Z-lSZEY}%Wn|byEac-'
    'y08@c(%cmHixeh>G5{|7kW*xm'
)
_CATALOG_SHA256 = 'f61487c0554148b8d8042d6ab1b1522a96d2fe8cb79043295ca9cc1e814dde42'


# ============================================================================
# GALLE CRP-I MODEL, PRESOLVE, EXACT QUBO, GREEDY, BFS, MILP   (from galle_baseline.py)
# ============================================================================
# Exact penalty reformulation of Galle et al. CRP-I (2018), ordinary restricted CRP.
#
# Build/evaluate needs only Python's standard library. Validation uses SciPy/HiGHS.
# All stack lists are bottom-to-top; container numbers are retrieval priorities.
# QUBO convention: offset + sum(linear[i]*x[i]) + sum(q[i,j]*x[i]*x[j], i<j).
# No simulation is started by this module.

@dataclass
class Row:
    label: str
    terms: dict[int, int]
    sense: str
    rhs: int

    def holds(self, x):
        v = sum(a*x[i] for i, a in self.terms.items())
        return v == self.rhs if self.sense == "eq" else v <= self.rhs


class GalleModel:
    def __init__(self, stacks, capacity, preprocessing=True):
        self.stacks = tuple(tuple(s) for s in stacks)
        self.S = len(stacks)
        self.C = sum(map(len, stacks))
        self.T = capacity
        C, S, T = self.C, self.S, self.T
        if sorted(v for s in stacks for v in s) != list(range(1, C+1)):
            raise ValueError("Use distinct priorities 1..C, each exactly once.")
        if S < 2 or T < 1 or max(map(len, stacks)) > T or C <= S:
            raise ValueError("This implementation requires S>=2, valid capacity and C>S.")
        self.N = N = C-S+1
        self.names, self.index, self.rows = [], {}, []
        for n in range(1, N+1):
            for c in range(n, C+S+1):
                for d in range(n, C+1):
                    self.var((n,c,d), f"a[{n},{c},{d}]")
        for d in range(N+1, C+1):
            self.var(("b",d), f"b[{d}]")
        a = lambda n,c,d: self.index[n,c,d]
        b = lambda d: self.index["b",d]
        self.objective = {a(n,n,d):1 for n in range(1,N) for d in range(n+1,C+1)}
        self.objective.update({b(d):1 for d in range(N+1,C+1)})
        A = self.encoding(self.stacks)
        for c in range(1,C+S+1):
            for d in range(1,C+1):
                self.add("1",[(a(1,c,d),1)],"eq",A[c,d])
        for n in range(2,N+1):
            for c in range(n,C+1):
                self.add("2",[(a(n,C+s,c),1) for s in range(1,S+1)],"eq",1)
                self.add("3",[(a(n,c,c),1)],"eq",0)
                for d in range(n,C+1):
                    if d == c:
                        continue
                    self.add("4",[(a(n,c,d),1),(a(n,d,c),1)],"le",1)
                    for s in range(1,S+1):
                        self.add("5",[(a(n,c,d),-1),(a(n,d,c),-1),
                                      (a(n,C+s,c),1),(a(n,C+s,d),1)],"le",1)
                        self.add("6",[(a(n,c,d),1),(a(n,d,c),1),(a(n,C+s,c),1)]+
                                 [(a(n,C+r,d),1) for r in range(1,S+1) if r!=s],"le",2)
            for s in range(1,S+1):
                self.add("7",[(a(n,C+s,d),1) for d in range(n,C+1)],"le",T)
        for d in range(N+1,C+1):
            for c in range(N,d):
                self.add("8",[(a(N,c,d),1),(b(d),-1)],"le",0)
        for n in range(1,N):
            for c in range(n+1,C+1):
                for d in range(n+1,C+S+1):
                    if d == c:
                        continue
                    self.add("9",[(a(n+1,d,c),1),(a(n,d,c),-1),(a(n,n,c),-1)],"le",0)
                    self.add("10",[(a(n,d,c),1),(a(n+1,d,c),-1),(a(n,n,c),-1)],"le",0)
                for s in range(1,S+1):
                    self.add("11",[(a(n,n,c),1),(a(n,C+s,c),1),(a(n+1,C+s,c),1)],"le",2)
                for d in range(n+1,C+1):
                    if c != d:
                        self.add("12",[(a(n,n,c),1),(a(n,n,d),1),
                                       (a(n,c,d),1),(a(n+1,c,d),1)],"le",3)
        if preprocessing:
            for c in range(1,C+1):
                first = min(n for n in range(1,C+1) if n==c or A[n,c])
                for n in range(2,min(first,N)+1):
                    for d in range(n,C+S+1):
                        self.add("PP",[(a(n,d,c),1)],"eq",A[d,c])

    def var(self,key,name):
        self.index[key] = len(self.names)
        self.names.append(name)

    def add(self,family,terms,sense,rhs):
        co = defaultdict(int)
        for i,v in terms:
            co[i] += v
        self.rows.append(Row(f"{family}:{len(self.rows)}",{i:v for i,v in co.items() if v},sense,rhs))

    def encoding(self,stacks):
        A = {(c,d):0 for c in range(1,self.C+self.S+1) for d in range(1,self.C+1)}
        for s, stack in enumerate(stacks,1):
            for k,d in enumerate(stack):
                A[self.C+s,d] = 1
                for c in stack[:k]:
                    A[c,d] = 1
        return A

    def cost(self,x):
        return sum(v*x[i] for i,v in self.objective.items())

    def violations(self,x):
        return [r.label for r in self.rows if not r.holds(x)]

    def assignment_from_moves(self,moves):
        stacks = [list(s) for s in self.stacks]
        stages = {1:self.encoding(stacks)}
        for move in moves:
            src = move["from"]-1
            box = stacks[src].pop()
            assert box == move["container"]
            if move["type"] == "relocate":
                stacks[move["to"]-1].append(box)
            elif box+1 <= self.N:
                stages[box+1] = self.encoding(stacks)
        x = [0]*len(self.names)
        for key,i in self.index.items():
            if key[0] == "b":
                d = key[1]
                x[i] = int(any(stages[self.N][c,d] for c in range(self.N,d)))
            else:
                n,c,d = key
                x[i] = stages[n][c,d]
        return x


def physical_bfs(stacks, capacity):
    """Independent exact search: only a top blocker of the current target may move.

    Retrievals have cost 0 and are performed immediately when available; every
    BFS edge is exactly one legal relocation plus all newly available retrievals.
    """
    def close(state):
        state = [list(s) for s in state]
        moves = []
        while any(state):
            target = min(v for s in state for v in s)
            src = next(i for i,s in enumerate(state) if target in s)
            if state[src][-1] != target:
                break
            state[src].pop()
            moves.append(dict(type="retrieve",container=target,**{"from":src+1}))
        return tuple(tuple(s) for s in state), moves
    start, initial = close(stacks)
    queue = deque([start])
    parents = {start:None}
    depths = {start:0}
    expanded = 0
    while queue:
        state = queue.popleft()
        expanded += 1
        if not any(state):
            tail, cursor = [], state
            while parents[cursor] is not None:
                prior, edge = parents[cursor]
                tail.append(edge)
                cursor = prior
            path = initial + [m for edge in reversed(tail) for m in edge]
            return dict(optimum=depths[state],expanded=expanded,discovered=len(parents),moves=path)
        target = min(v for s in state for v in s)
        src = next(i for i,s in enumerate(state) if target in s)
        assert state[src][-1] != target
        for dst in range(len(state)):
            if dst == src or len(state[dst]) >= capacity:
                continue
            nxt = [list(s) for s in state]
            box = nxt[src].pop()
            nxt[dst].append(box)
            nxt, free = close(nxt)
            if nxt not in parents:
                edge = [dict(type="relocate",container=box,**{"from":src+1,"to":dst+1})]+free
                parents[nxt] = (state,edge)
                depths[nxt] = depths[state]+1
                queue.append(nxt)
    raise ValueError("No legal complete retrieval sequence exists.")


def feasible_upper_bound(stacks,capacity):
    """Deterministic legal greedy plan; never consults an optimal solution.

    Put a blocker on the smallest larger stack minimum if possible; otherwise
    choose the largest minimum. An empty stack has minimum C+1.
    """
    state = [list(s) for s in stacks]
    C = sum(map(len,state))
    moves = []
    while any(state):
        target = min(v for s in state for v in s)
        src = next(i for i,s in enumerate(state) if target in s)
        box = state[src][-1]
        if box==target:
            state[src].pop()
            moves.append(dict(type="retrieve",container=box,**{"from":src+1}))
            continue
        destinations = [i for i,s in enumerate(state) if i!=src and len(s)<capacity]
        if not destinations:
            raise ValueError("Greedy plan is blocked; obtain a feasible plan by another method.")
        minimum = {i:min(state[i],default=C+1) for i in destinations}
        good = [i for i in destinations if minimum[i]>box]
        dst = min(good,key=lambda i:(minimum[i],i)) if good else min(destinations,key=lambda i:(-minimum[i],i))
        state[src].pop(); state[dst].append(box)
        moves.append(dict(type="relocate",container=box,**{"from":src+1,"to":dst+1}))
    return dict(upper_bound=sum(m["type"]=="relocate" for m in moves),moves=moves)


class InfeasibleInstance(ValueError):
    """Raised when the bay has no legal restricted retrieval sequence."""


INFEASIBLE_MESSAGE = ("This bay has no legal restricted retrieval sequence: the Galle constraints "
                      "cannot all hold (usually too little free capacity to park the blockers). "
                      "No QAOA model was built.")


class Presolve:
    """Only feasibility implications: constants, equal/complemented bits, tautologies.

    No objective cutoff, known optimum or chosen relocation is used.
    Every removed variable has a recoverable expression in remaining bits.
    """
    def __init__(self,model):
        self.model = model
        self.parent = list(range(len(model.names)))
        self.parity = [0]*len(model.names)
        self.fixed = {}
        self.log = []
        while True:
            start = len(self.log)
            rows = self.simplify()
            # Two opposing inequalities imply an equality.
            lookup = {(tuple(sorted(r.terms.items())),r.rhs):r for r in rows if r.sense=="le"}
            extra = []
            for r in rows:
                if r.sense == "le":
                    opp = lookup.get((tuple((i,-v) for i,v in sorted(r.terms.items())),-r.rhs))
                    if opp:
                        extra.append(Row(r.label+"&"+opp.label,r.terms,"eq",r.rhs))
            for row in rows+extra:
                terms, rhs = self.substitute(row.terms,row.rhs)
                lo = sum(min(0,v) for v in terms.values())
                hi = sum(max(0,v) for v in terms.values())
                if not (lo<=rhs<=hi if row.sense=="eq" else lo<=rhs):
                    raise InfeasibleInstance(INFEASIBLE_MESSAGE+" (row "+row.label+")")
                changed = False
                for i,v in terms.items():
                    possible = []
                    for bit in (0,1):
                        a = lo-min(0,v)+v*bit
                        b = hi-max(0,v)+v*bit
                        if a<=rhs<=b if row.sense=="eq" else a<=rhs:
                            possible.append(bit)
                    if len(possible)==1:
                        self.fix(i,possible[0],row.label)
                        changed = True
                        break
                if changed:
                    continue
                if len(terms)==2 and row.sense=="eq":
                    (i,u),(j,v) = sorted(terms.items())
                    allowed = {(x,y) for x,y in product((0,1),repeat=2) if u*x+v*y==rhs}
                    if allowed == {(0,0),(1,1)}:
                        self.merge(i,j,0,row.label)
                    elif allowed == {(0,1),(1,0)}:
                        self.merge(i,j,1,row.label)
            if len(self.log)==start:
                break
        self.rows = self.simplify()
        roots = sorted({self.find(i)[0] for i in range(len(model.names))}-self.fixed.keys())
        self.roots = roots
        self.root_index = {r:i for i,r in enumerate(roots)}
        self.mapping = []
        for i in range(len(model.names)):
            root,flip = self.find(i)
            if root in self.fixed:
                self.mapping.append(dict(constant=self.fixed[root]^flip))
            else:
                self.mapping.append(dict(bit=self.root_index[root],complement=bool(flip)))
        self.reduced_rows = [Row(r.label,{self.root_index[i]:v for i,v in r.terms.items()},r.sense,r.rhs) for r in self.rows]
        terms, rhs = self.substitute(model.objective,0)
        self.objective_offset = -rhs
        self.objective = {self.root_index[i]:v for i,v in terms.items()}

    def find(self,i):
        if self.parent[i]!=i:
            root,flip = self.find(self.parent[i])
            self.parity[i] ^= flip
            self.parent[i] = root
        return self.parent[i],self.parity[i]

    def fix(self,i,value,why):
        root,flip = self.find(i)
        value ^= flip
        if root in self.fixed:
            if self.fixed[root]!=value:
                raise InfeasibleInstance(INFEASIBLE_MESSAGE+" (conflicting implication: "+why+")")
        else:
            self.fixed[root]=value
            self.log.append(dict(action="fix",variable=root,value=value,reason=why))

    def merge(self,i,j,flip,why):
        ri,fi = self.find(i)
        rj,fj = self.find(j)
        relation = flip^fi^fj
        if ri==rj:
            if relation!=0:
                raise InfeasibleInstance(INFEASIBLE_MESSAGE+" (contradictory merge: "+why+")")
            return
        if ri in self.fixed:
            self.fix(rj,self.fixed[ri]^relation,why)
            return
        if rj in self.fixed:
            self.fix(ri,self.fixed[rj]^relation,why)
            return
        child,root = max(ri,rj),min(ri,rj)
        self.parent[child]=root
        self.parity[child]=relation
        self.log.append(dict(action="merge",variable=child,root=root,complement=bool(relation),reason=why))

    def substitute(self,terms,rhs):
        out = defaultdict(int)
        for i,v in terms.items():
            root,flip = self.find(i)
            if root in self.fixed:
                rhs -= v*(self.fixed[root]^flip)
            elif flip:
                rhs -= v
                out[root] -= v
            else:
                out[root] += v
        return {i:v for i,v in out.items() if v},rhs

    def simplify(self):
        out = {}
        for row in self.model.rows:
            terms,rhs = self.substitute(row.terms,row.rhs)
            lo,hi = sum(min(0,v) for v in terms.values()),sum(max(0,v) for v in terms.values())
            if (row.sense=="le" and hi<=rhs) or (not terms and rhs==0):
                continue
            if not (lo<=rhs and (row.sense=="le" or rhs<=hi)):
                raise InfeasibleInstance(INFEASIBLE_MESSAGE+" (row "+row.label+")")
            items = tuple(sorted(terms.items()))
            if row.sense=="eq" and items and items[0][1]<0:
                terms,rhs = {i:-v for i,v in terms.items()},-rhs
            key = (row.sense,tuple(sorted(terms.items())),rhs)
            if key in out:
                out[key].label += ","+row.label
            else:
                out[key] = Row(row.label,terms,row.sense,rhs)
        return list(out.values())

    def reduce_assignment(self,x):
        return [x[r] for r in self.roots]

    def recover(self,y):
        return [m["constant"] if "constant" in m else y[m["bit"]]^int(m["complement"]) for m in self.mapping]


def bounded_weights(maximum):
    """Nonnegative binary weights representing exactly every integer 0..maximum."""
    if maximum<0:
        raise ValueError("Negative slack bound")
    weights, remaining, power = [], maximum, 1
    while remaining:
        w = min(power,remaining)
        weights.append(w)
        remaining -= w
        power *= 2
    return weights


class Qubo:
    def __init__(self,model,upper_bound,compact=True,presolve='standard'):
        if not isinstance(upper_bound,int) or upper_bound<0:
            raise ValueError("Supply a validated feasible integer relocation upper bound.")
        self.model = model
        if presolve not in ('standard', 'strong'):  # FIX (Sim9) 11
            raise ValueError(f"presolve must be 'standard' or 'strong', not {presolve!r}")
        self.presolve = p = Presolve(model) if presolve=='standard' else StrongPresolve(model)
        self.names = [model.names[r] for r in p.roots]
        self.physical_bits = len(self.names)
        self.objective_lower_bound = p.objective_offset+sum(min(0,v) for v in p.objective.values())
        if upper_bound<self.objective_lower_bound:
            raise ValueError("Upper bound is smaller than the reduced objective's domain lower bound.")
        self.weight = upper_bound-self.objective_lower_bound+1
        self.offset = p.objective_offset
        self.linear = defaultdict(int,p.objective)
        self.quadratic = defaultdict(int)
        self.components = []
        for row in p.reduced_rows:
            if compact and len(row.terms)<=2:
                keys = sorted(row.terms)
                f = lambda bits: int(not row.holds(dict(zip(keys,bits))))
                if len(keys)==1:
                    zero,one = f([0]),f([1])
                    coeff = {keys[0]:one-zero}
                    pair = {}
                else:
                    zero = f([0,0])
                    coeff = {keys[0]:f([1,0])-zero, keys[1]:f([0,1])-zero}
                    pair = {(keys[0],keys[1]):f([1,1])-f([1,0])-f([0,1])+zero}
                self.add_poly(zero,coeff,pair,self.weight)
                self.components.append(dict(kind="indicator",row=row,aux=[]))
                continue
            # Compact le encoding: r=(lhs+2*t-rhs), P=r*(r+1)/2.
            # On integers P>=0, with zeros exactly at r=0,-1. Thus t encodes
            # floor(slack/2), saving one binary digit over a slack square.
            # lhs's binary-domain minimum bounds slack, including the odd end.
            terms = dict(row.terms)
            maximum = row.rhs - sum(min(0,v) for v in row.terms.values())
            interval = compact and row.sense=="le"
            weights = bounded_weights(maximum//2 if interval else maximum) if row.sense=="le" else []
            aux = []
            for w in weights:
                if interval:
                    w *= 2
                bit = len(self.names)
                self.names.append(f"slack[{len(self.components)},{len(aux)};weight={w}]")
                terms[bit] = w
                aux.append((bit,w))
            if interval:
                self.interval(-row.rhs,terms,self.weight)
            else:
                self.square(-row.rhs,terms,self.weight)
            self.components.append(dict(kind="interval" if interval else "square",row=row,aux=aux))
        self.linear = {i:v for i,v in self.linear.items() if v}
        self.quadratic = {pair:v for pair,v in self.quadratic.items() if v}

    def add_poly(self,offset,linear,quadratic,scale):
        self.offset += scale*offset
        for i,v in linear.items():
            self.linear[i] += scale*v
        for pair,v in quadratic.items():
            self.quadratic[pair] += scale*v

    def square(self,c,terms,scale):
        linear = {i:v*v+2*c*v for i,v in terms.items()}
        items = sorted(terms.items())
        quadratic = {(i,j):2*v*w for k,(i,v) in enumerate(items) for j,w in items[k+1:]}
        self.add_poly(c*c,linear,quadratic,scale)

    def interval(self,c,terms,scale):
        linear = {i:(v*v+2*c*v+v)//2 for i,v in terms.items()}
        items = sorted(terms.items())
        quadratic = {(i,j):v*w for k,(i,v) in enumerate(items) for j,w in items[k+1:]}
        self.add_poly(c*(c+1)//2,linear,quadratic,scale)

    def energy(self,x):
        if len(x)!=len(self.names) or any(v not in (0,1) for v in x):
            raise ValueError("Expected one 0/1 per QUBO variable.")
        return self.offset + sum(v*x[i] for i,v in self.linear.items()) + sum(v*x[i]*x[j] for (i,j),v in self.quadratic.items())

    def component_energy(self,x):
        p = self.presolve
        result = p.objective_offset+sum(v*x[i] for i,v in p.objective.items())
        for comp in self.components:
            row = comp["row"]
            if comp["kind"]=="indicator":
                penalty = int(not row.holds(x))
            else:
                residual = sum(v*x[i] for i,v in row.terms.items())-row.rhs+sum(w*x[i] for i,w in comp["aux"])
                penalty = residual*(residual+1)//2 if comp["kind"]=="interval" else residual*residual
            result += self.weight*penalty
        return result

    def complete(self,original_x):
        if self.model.violations(original_x):
            raise ValueError("Original assignment is infeasible.")
        y = self.presolve.reduce_assignment(original_x)+[0]*(len(self.names)-self.physical_bits)
        if self.presolve.recover(y)!=original_x:  # FIX (Sim9) 15: was a bare assert
            raise ValueError("This assignment is not representable after the presolve (strong presolve removes "
                             "duplicate copies of a plan that set an unneeded terminal flag). Clear that flag and retry.")
        for comp in self.components:
            if comp["aux"]:
                row = comp["row"]
                slack = row.rhs-sum(v*y[i] for i,v in row.terms.items())
                if comp["kind"]=="interval":
                    slack -= slack%2
                for i,w in reversed(comp["aux"]):
                    if w<=slack:
                        y[i]=1
                        slack-=w
                assert slack==0
        assert self.energy(y)==self.model.cost(original_x)
        return y

    def ising(self):
        """Sparse diagonal H=offset I+sum(h_i Z_i)+sum(J_ij Z_i Z_j)."""
        h = defaultdict(float)
        constant = float(self.offset)
        for i,v in self.linear.items():
            constant += v/2
            h[i] -= v/2
        J = {}
        for (i,j),v in self.quadratic.items():
            constant += v/4
            h[i] -= v/4
            h[j] -= v/4
            J[i,j] = v/4
        return constant,dict(h),J

    def export(self,folder):
        folder = Path(folder)
        folder.mkdir(parents=True,exist_ok=True)
        data = dict(convention="offset + sum(linear_i*x_i) + sum(quadratic_ij*x_i*x_j), i<j; x binary",
                    instance=dict(stacks_bottom_to_top=self.model.stacks,capacity=self.model.T,C=self.model.C,S=self.model.S,N=self.model.N),
                    penalty_weight=self.weight,objective_domain_lower_bound=self.objective_lower_bound,
                    feasible_upper_bound=self.weight+self.objective_lower_bound-1,
                    number_of_bits=len(self.names),decision_bits=self.physical_bits,
                    auxiliary_bits=len(self.names)-self.physical_bits,offset=self.offset,
                    variables=self.names,linear=[[i,v] for i,v in sorted(self.linear.items())],
                    quadratic=[[i,j,v] for (i,j),v in sorted(self.quadratic.items())])
        (folder/"qubo.json").write_text(json.dumps(data,indent=2)+"\n")
        mapping = dict(original_variables=self.model.names,recovery=self.presolve.mapping,
                       presolve_log=self.presolve.log,objective_offset=self.presolve.objective_offset,
                       objective_linear=self.presolve.objective,
                       components=[dict(kind=c["kind"],row=vars(c["row"]),aux=c["aux"]) for c in self.components])
        (folder/"provenance.json").write_text(json.dumps(mapping,indent=2)+"\n")
        (folder/"original_model.json").write_text(json.dumps(dict(variables=self.model.names,objective=self.model.objective,
                     rows=[vars(r) for r in self.model.rows]),indent=2)+"\n")
        terms = [str(self.offset)]
        terms += [f"{v:+d} x{i}" for i,v in sorted(self.linear.items())]
        terms += [f"{v:+d} x{i} x{j}" for (i,j),v in sorted(self.quadratic.items())]
        (folder/"full_single_QUBO.txt").write_text("F(x) =\n"+"\n".join(terms)+"\n\nAll x_i are binary. Each i<j term appears once.\n")
        offset,h,J = self.ising()
        (folder/"ising.json").write_text(json.dumps(dict(offset=offset,h=sorted(h.items()),J=[[i,j,v] for (i,j),v in sorted(J.items())]),indent=2)+"\n")
        return data


def solve_milp(model,limit=60):
    import numpy as np
    from scipy.optimize import milp,Bounds,LinearConstraint
    from scipy.sparse import coo_matrix
    ri,ci,vals,lo,hi = [],[],[],[],[]
    for k,row in enumerate(model.rows):
        for i,v in row.terms.items():
            ri.append(k); ci.append(i); vals.append(v)
        lo.append(row.rhs if row.sense=="eq" else -np.inf)
        hi.append(row.rhs)
    A = coo_matrix((vals,(ri,ci)),shape=(len(model.rows),len(model.names))).tocsc()
    objective = np.array([model.objective.get(i,0) for i in range(len(model.names))],dtype=float)
    res = milp(objective,integrality=np.ones(len(objective)),bounds=Bounds(0,1),
               constraints=LinearConstraint(A,lo,hi),options=dict(time_limit=limit,mip_rel_gap=0.0))
    if not res.success:
        raise RuntimeError(res.message)
    x = np.rint(res.x).astype(int).tolist()
    assert not model.violations(x)
    assert abs(model.cost(x)-res.fun)<1e-7
    return dict(objective=model.cost(x),dual_bound=float(res.mip_dual_bound),
                gap=float(res.mip_gap),nodes=int(res.mip_node_count),assignment=x,status=res.message)


# ============================================================================
# STRONG PRESOLVE: fewer qubits for the SAME problem   (new, option 2)
# ============================================================================
# The original Presolve fixes variables that one constraint forces and merges
# pairs that one 2-variable equality ties together. StrongPresolve keeps all of
# that and adds three reductions. The first two are IMPLIED by the constraints
# (they hold in every feasible assignment), so on their own they leave the
# feasible set unchanged and every eliminated variable is recovered exactly.
# The third is a DOMINANCE rule that keeps every legal crane plan and every
# optimal solution but DELETES duplicate assignments that carry unneeded
# terminal flags (FIX (Sim9) 14; audit 11 Oct 2026: 41,766 -> 22,086 assignments
# over 411 bays, 8,936/8,936 legal plans and 1,038/1,038 optimal plans kept).
#
#  (P) Probing. Set one remaining bit to 0, propagate every constraint; then to
#      1. A value that leads to a contradiction is impossible in every feasible
#      assignment, so the bit is fixed to the other value. A bit that takes the
#      same value both ways is fixed; a bit that copies (or complements) the
#      probed bit in both branches is merged with it.
#  (A) Affine elimination of one-hot groups. Galle's row (2) says a container
#      is in exactly one stack: m_1 + ... + m_S = 1. One membership bit is then
#      m_S = 1 - (m_1 + ... + m_{S-1}); it is substituted into every constraint
#      and the objective, and the domain rows 0 <= 1 - sum <= 1 are added so it
#      stays a bit. Only done when no constraint grows beyond the predicate's
#      local-synthesis cutoff (so no scratch qubits appear).
#  (D) Terminal-flag dominance. A flag b_d that no remaining constraint can
#      force to 1 only adds +1 to the objective; it is fixed to 0. This removes
#      redundant copies of the same plan (with an unnecessary flag) and keeps
#      every legal plan and every optimum.
#
# Validation (selftest): on random small bays every legal plan is encoded,
# recovered and satisfies the reduced constraints, the minimum is unchanged and
# every ground state decodes to an optimal plan.
class StrongPresolve(Presolve):
    """Presolve + probing + one-hot affine elimination + flag dominance."""

    def __init__(self, model, direct_cutoff=5, probing=True, aggregate=True, dominance=True,
                 time_limit=None, cancelled=_never):   # FIX (Sim9) 13: no wall-clock deadline by default
        self.model = model
        self.parent = list(range(len(model.names)))
        self.parity = [0] * len(model.names)
        self.fixed = {}
        self.log = []
        self.affine = {}          # eliminated var -> (const, {original var: coeff}) before expansion
        self.extra_rows = []      # domain rows of eliminated variables
        self.cutoff = direct_cutoff
        self.stats = Counter()
        deadline = math.inf if time_limit is None else time.time() + time_limit
        self.stats['deadline_hit'] = 0
        self._base_loop()
        changed = True
        while changed:
            if cancelled():
                raise Cancelled()
            changed = False
            if probing and time.time() < deadline and self._probe(deadline):
                changed = True; self._base_loop(); continue
            if aggregate and self._aggregate():
                changed = True; self._base_loop(); continue
            if dominance and self._dominance():
                changed = True; self._base_loop(); continue
        self._finish()

    # ----------------------------------------------------- shared machinery
    def substitute(self, terms, rhs):
        """Like Presolve.substitute, but also expands affinely eliminated variables."""
        out = defaultdict(int)
        stack = list(terms.items())
        while stack:
            i, v = stack.pop()
            root, flip = self.find(i)
            if root in self.fixed:
                rhs -= v * (self.fixed[root] ^ flip)
            elif root in self.affine:
                const, expr = self.affine[root]
                if flip:              # x_i = 1 - x_root
                    rhs -= v; v = -v
                rhs -= v * const
                stack.extend((j, v * c) for j, c in expr.items())
            elif flip:
                rhs -= v; out[root] -= v
            else:
                out[root] += v
        return {i: v for i, v in out.items() if v}, rhs

    def simplify(self):
        out = {}
        for row in list(self.model.rows) + self.extra_rows:
            terms, rhs = self.substitute(row.terms, row.rhs)
            lo, hi = sum(min(0, v) for v in terms.values()), sum(max(0, v) for v in terms.values())
            if (row.sense == 'le' and hi <= rhs) or (not terms and rhs == 0):
                continue
            if not (lo <= rhs and (row.sense == 'le' or rhs <= hi)):
                raise InfeasibleInstance(INFEASIBLE_MESSAGE + ' (row ' + row.label + ')')
            items = tuple(sorted(terms.items()))
            if row.sense == 'eq' and items and items[0][1] < 0:
                terms, rhs = {i: -v for i, v in terms.items()}, -rhs
            key = (row.sense, tuple(sorted(terms.items())), rhs)
            if key in out:
                out[key].label += ',' + row.label
            else:
                out[key] = Row(row.label, terms, row.sense, rhs)
        return list(out.values())

    def _base_loop(self):
        """The original Presolve fixed point (constants, merges, tautologies), verbatim logic."""
        while True:
            start = len(self.log)
            rows = self.simplify()
            lookup = {(tuple(sorted(r.terms.items())), r.rhs): r for r in rows if r.sense == 'le'}
            extra = []
            for r in rows:
                if r.sense == 'le':
                    opp = lookup.get((tuple((i, -v) for i, v in sorted(r.terms.items())), -r.rhs))
                    if opp:
                        extra.append(Row(r.label + '&' + opp.label, r.terms, 'eq', r.rhs))
            for row in rows + extra:
                terms, rhs = self.substitute(row.terms, row.rhs)
                lo = sum(min(0, v) for v in terms.values())
                hi = sum(max(0, v) for v in terms.values())
                if not (lo <= rhs <= hi if row.sense == 'eq' else lo <= rhs):
                    raise InfeasibleInstance(INFEASIBLE_MESSAGE + ' (row ' + row.label + ')')
                changed = False
                for i, v in terms.items():
                    possible = []
                    for bit in (0, 1):
                        a = lo - min(0, v) + v * bit
                        b = hi - max(0, v) + v * bit
                        if a <= rhs <= b if row.sense == 'eq' else a <= rhs:
                            possible.append(bit)
                    if len(possible) == 1:
                        self.fix(i, possible[0], row.label)
                        changed = True
                        break
                if changed:
                    continue
                if len(terms) == 2 and row.sense == 'eq':
                    (i, u), (j, v) = sorted(terms.items())
                    allowed = {(x, y) for x, y in product((0, 1), repeat=2) if u * x + v * y == rhs}
                    if allowed == {(0, 0), (1, 1)}:
                        self.merge(i, j, 0, row.label)
                    elif allowed == {(0, 1), (1, 0)}:
                        self.merge(i, j, 1, row.label)
            if len(self.log) == start:
                break

    def _free_roots(self):
        return sorted({self.find(i)[0] for i in range(len(self.model.names))} - self.fixed.keys() - self.affine.keys())

    def _finish(self):
        self.rows = self.simplify()
        roots = self._free_roots()
        self.roots = roots
        self.root_index = {r: i for i, r in enumerate(roots)}
        self.mapping = []
        for i in range(len(self.model.names)):
            root, flip = self.find(i)
            if root in self.fixed:
                self.mapping.append(dict(constant=self.fixed[root] ^ flip))
            elif root in self.affine:
                terms, rhs = self.substitute({i: 1}, 0)
                self.mapping.append(dict(affine=[-rhs, [[self.root_index[r], c] for r, c in sorted(terms.items())]]))
            else:
                self.mapping.append(dict(bit=self.root_index[root], complement=bool(flip)))
        self.reduced_rows = [Row(r.label, {self.root_index[i]: v for i, v in r.terms.items()}, r.sense, r.rhs) for r in self.rows]
        terms, rhs = self.substitute(self.model.objective, 0)
        self.objective_offset = -rhs
        self.objective = {self.root_index[i]: v for i, v in terms.items()}
        self.stats['qubits'] = len(roots)

    def recover(self, y):
        out = []
        for m in self.mapping:
            if 'constant' in m:
                out.append(m['constant'])
            elif 'affine' in m:
                const, terms = m['affine']; v = const + sum(c * y[b] for b, c in terms)
                if v not in (0, 1):
                    raise ValueError('Reduced assignment violates an eliminated variable\'s 0/1 domain.')
                out.append(v)
            else:
                out.append(y[m['bit']] ^ int(m['complement']))
        return out

    # ----------------------------------------------------- (P) probing
    def _root_rows(self):
        rows = []
        for r in self.simplify():
            for sign in ((1,) if r.sense == 'le' else (1, -1)):
                terms = {i: sign * v for i, v in r.terms.items()}
                rhs = sign * r.rhs
                if terms and sum(max(0, v) for v in terms.values()) > rhs:
                    rows.append((terms, rhs))
        watch = defaultdict(list)
        for k, (terms, _) in enumerate(rows):
            for i in terms:
                watch[i].append(k)
        return rows, watch

    @staticmethod
    def _propagate(rows, watch, start):
        a = dict(start); dirty = set()
        for i in a:
            dirty.update(watch.get(i, ()))
        while dirty:
            k = dirty.pop(); terms, rhs = rows[k]
            lo = 0; free = []
            for i, c in terms.items():
                if i in a:
                    lo += c * a[i]
                else:
                    lo += min(0, c); free.append((i, c))
            if lo > rhs:
                return None
            for i, c in free:
                if c > 0 and lo + c > rhs:
                    val = 0
                elif c < 0 and lo - c > rhs:
                    val = 1
                else:
                    continue
                if i in a:
                    if a[i] != val:
                        return None
                    continue
                a[i] = val; dirty.update(watch.get(i, ()))
        return a

    def _probe(self, deadline):
        """One full pass; every recorded fact is implied by the constraints, so facts
        found from rows built before other fixes in the same pass remain valid."""
        rows, watch = self._root_rows()
        found = False
        for r in self._free_roots():
            if time.time() > deadline:
                self.stats['deadline_hit'] += 1   # FIX (Sim9) 13: recorded, not silent
                break
            root, _ = self.find(r)
            if root != r or r in self.fixed or r in self.affine:
                continue
            f0 = self._propagate(rows, watch, {r: 0}); f1 = self._propagate(rows, watch, {r: 1})
            if f0 is None and f1 is None:
                raise InfeasibleInstance(INFEASIBLE_MESSAGE + ' (probing)')
            if f0 is None or f1 is None:
                self.fix(r, 1 if f0 is None else 0, 'probing'); self.stats['probe_fixed'] += 1; found = True
                continue
            for y in set(f0) & set(f1):
                if y == r:
                    continue
                if f0[y] == f1[y]:
                    before = len(self.log); self.fix(y, f0[y], 'probing')
                    if len(self.log) > before:
                        self.stats['probe_fixed'] += 1; found = True
                else:
                    before = len(self.log); self.merge(r, y, 0 if f1[y] == 1 else 1, 'probing')
                    if len(self.log) > before:
                        self.stats['probe_merged'] += 1; found = True
        return found

    # ----------------------------------------------------- (A) affine one-hot elimination
    def _aggregate(self):
        rows = self.simplify()
        for r in rows:
            if r.sense != 'eq' or r.rhs != 1 or len(r.terms) < 3 or any(v != 1 for v in r.terms.values()):
                continue
            if not all(self.model.names[i].startswith('a[') for i in r.terms):
                continue
            for x in sorted(r.terms, reverse=True):
                expr = {j: -1 for j in r.terms if j != x}          # x = 1 - sum(others)
                if self._fill_ok(rows, x, expr):
                    self.affine[x] = (1, expr)
                    self.extra_rows += [Row(f'domain:{x}', {x: 1}, 'le', 1), Row(f'domain:{x}', {x: -1}, 'le', 0)]
                    self.log.append(dict(action='aggregate', variable=x, expression=dict(const=1, terms=expr), reason=r.label))
                    self.stats['aggregated'] += 1
                    return True
        return False

    def _fill_ok(self, rows, x, expr):
        """Would substituting x keep every touched constraint within the direct cutoff?"""
        for r in rows:
            if x not in r.terms:
                continue
            c = r.terms[x]; new = dict(r.terms); del new[x]
            for j, v in expr.items():
                new[j] = new.get(j, 0) + c * v
                if not new[j]:
                    del new[j]
            if len(new) > self.cutoff and len(new) > len(r.terms) - 1:
                return False
        return True

    # ----------------------------------------------------- (D) flag dominance
    def _dominance(self):
        """Fix b_d = 0 when b_d is its own root and every remaining constraint
        containing it is a <= row with a POSITIVE coefficient on b_d: lowering b_d
        then never breaks feasibility and lowers the objective by 1."""
        rows = self.simplify(); changed = False
        for d in range(self.model.N + 1, self.model.C + 1):
            v = self.model.index['b', d]; root, flip = self.find(v)
            if root != v or flip or v in self.fixed or v in self.affine or self.model.objective.get(v) != 1:
                continue
            if any(v in r.terms and (r.sense != 'le' or r.terms[v] < 0) for r in rows):
                continue
            if any(self.find(j)[0] == v and j != v for j in range(len(self.model.names))):
                continue                                   # another variable is merged into b_d
            self.fix(v, 0, 'dominance: unforceable terminal flag'); self.stats['dominance'] += 1; changed = True
        return changed


PRESOLVES = {'standard': Presolve, 'strong': StrongPresolve}


# ============================================================================
# COHERENT MOVEMENT ORACLE (research encoding)   (from coherent_crp.py)
# ============================================================================
# Gate-synthesized restricted-CRP cost oracle: no route or energy lookup table.
#
# Input bits select destinations at retrieval stages. A Boolean circuit implements
# the crane transitions and validity tests. Compute / phase / uncompute implements
# a diagonal cost unitary on superpositions of ALL encoded plans, not a catalogue
# chosen by classical optimization. This is an experimental research candidate.

class Logic:
    """Hash-consed AND/XOR DAG with complemented edges and exact constant folding.

    Literals 0/1 are constants; +/-i refer to node i or its complement.
    Every live non-input node gets a clean work qubit in this first compiler.
    """
    def __init__(self, node_limit=2_000_000):
        self.nodes=[('constant',0),('constant',1)]
        self.inputs=[]; self.cache={}; self.node_limit=node_limit

    @staticmethod
    def NOT(a): return 1-a if a in (0,1) else -a

    def node(self, kind, a, b):
        a,b=sorted((a,b)); key=(kind,a,b)
        if key not in self.cache:
            if len(self.nodes)>=self.node_limit:
                raise MemoryError('Compiler node budget exceeded; increase --node-limit on the compilation host. No QPU was contacted.')
            self.cache[key]=len(self.nodes); self.nodes.append(key)
        return self.cache[key]

    def input(self, name):
        if len(self.nodes)>=self.node_limit: raise MemoryError('Compiler node budget exceeded.')
        i=len(self.nodes); self.nodes.append(('input',name)); self.inputs.append(i); return i

    def AND(self,a,b):
        if a==0 or b==0:return 0
        if a==1:return b
        if b==1:return a
        if a==b:return a
        if a==self.NOT(b):return 0
        return self.node('and',a,b)

    def XOR(self,a,b):
        if a==0:return b
        if b==0:return a
        if a==1:return self.NOT(b)
        if b==1:return self.NOT(a)
        if a==b:return 0
        if a==self.NOT(b):return 1
        return self.node('xor',a,b)

    def OR(self,a,b):return self.NOT(self.AND(self.NOT(a),self.NOT(b)))
    def all(self,items):
        value=1
        for item in items:value=self.AND(value,item)
        return value
    def any(self,items):
        value=0
        for item in items:value=self.OR(value,item)
        return value
    def xor_all(self,items):
        value=0
        for item in items:value=self.XOR(value,item)
        return value
    def eq(self,bits,value):
        return self.all(bit if (value>>j)&1 else self.NOT(bit) for j,bit in enumerate(bits))
    def less_const(self,bits,value):
        less=0;equal=1
        for j in reversed(range(len(bits))):
            if (value>>j)&1:less=self.OR(less,self.AND(equal,self.NOT(bits[j])))
            equal=self.AND(equal,bits[j] if (value>>j)&1 else self.NOT(bits[j]))
        return less
    def mux(self,select,yes,no):return self.XOR(no,self.AND(select,self.XOR(yes,no)))

    def evaluate(self, bits):
        if len(bits)!=len(self.inputs) or any(b not in (0,1) for b in bits):raise ValueError('Expected one binary value per decision qubit.')
        values=[0,1]; cursor=0
        def get(lit):return values[lit] if lit>=0 else 1-values[-lit]
        for node in self.nodes[2:]:
            if node[0]=='input':values.append(int(bits[cursor]));cursor+=1
            else:
                a,b=get(node[1]),get(node[2]);values.append(a&b if node[0]=='and' else a^b)
        return values


def validate_instance(stacks,height):
    if len(stacks)<2 or not isinstance(height,int) or height<1:raise ValueError('Need >=2 stacks and positive integer capacity.')
    labels=sorted(v for s in stacks for v in s)
    if not labels or labels!=list(range(1,len(labels)+1)):raise ValueError('Priorities must be distinct integers 1..N.')
    if max(map(len,stacks))>height:raise ValueError('Initial stack exceeds capacity.')


@dataclass
class Oracle:
    stacks: tuple
    height: int
    terminal_reduction: bool
    logic: Logic
    slots: list
    phases: dict
    valid: int
    move_flags: list
    terminal_flags: list
    stages: int
    bound: int

    @staticmethod
    def value(values,lit):return values[lit] if lit>=0 else 1-values[-lit]
    def evaluate(self,bits):
        values=self.logic.evaluate(bits)
        get=lambda lit:self.value(values,lit)
        return dict(energy=sum(weight*get(lit) for lit,weight in self.phases.items()),
                    valid=bool(get(self.valid)),prefix_relocations=sum(get(v) for v in self.move_flags),
                    terminal_relocations=sum(get(v) for v in self.terminal_flags))
    def live_nodes(self):
        live=set(self.logic.inputs); todo=[abs(v) for v in self.phases if abs(v)>1]
        while todo:
            i=todo.pop()
            if i in live:continue
            live.add(i);node=self.logic.nodes[i]
            if node[0] in ('and','xor'):todo.extend(abs(x) for x in node[1:] if abs(x)>1)
        return sorted(live)
    def wiring(self):
        live=self.live_nodes();inputs=self.logic.inputs
        work=[i for i in live if self.logic.nodes[i][0]!='input']
        return {node:q for q,node in enumerate(inputs+work)},work
    def forward_gates(self):
        """Yield only X, CX, CCX; all scratch targets initially zero."""
        mapping,work=self.wiring()
        for i in work:
            kind,a,b=self.logic.nodes[i];q=mapping[i]
            if kind=='and':
                negative=[mapping[-v] for v in (a,b) if v<0]
                for c in negative:yield ('x',(c,))
                yield ('ccx',(mapping[abs(a)],mapping[abs(b)],q))
                for c in reversed(negative):yield ('x',(c,))
            else:
                yield ('cx',(mapping[abs(a)],q));yield ('cx',(mapping[abs(b)],q))
                if (a<0) != (b<0):yield ('x',(q,))
    def resources(self,p=1):
        mapping,work=self.wiring();counts=Counter(kind for kind,_ in self.forward_gates())
        return dict(method='coherent stage-destination oracle',containers=sum(map(len,self.stacks)),
                    stacks=len(self.stacks),height=self.height,terminal_reduction=self.terminal_reduction,
                    encoded_retrieval_stages=self.stages,decision_qubits=len(self.logic.inputs),
                    clean_work_qubits=len(work),total_logical_qubits=len(mapping),boolean_nodes=len(self.logic.nodes)-2,
                    forward_gate_counts=dict(counts),phase_terms=sum(abs(lit)>1 for lit in self.phases),
                    qaoa_depth=p,compute_uncompute_ccx=2*p*counts['ccx'],
                    compute_uncompute_cx=2*p*counts['cx'],
                    ccx_cx_expansion_estimate=2*p*(6*counts['ccx']+counts['cx']),
                    routing_included=False,error_correction_included=False,physical_qubits=None,
                    note='All scratch counted. Six-CX/CCX is an unoptimized synthesis estimate, not a routed IBM gate count. Physical fault-tolerant overhead and rotation synthesis require a specified device/error target.')
    def phase_circuit(self,gamma):
        from qiskit import QuantumCircuit
        mapping,work=self.wiring();qc=QuantumCircuit(len(mapping),name='coherent_relocation_cost')
        gates=list(self.forward_gates())
        for name,args in gates:getattr(qc,name)(*args)
        for lit,weight in self.phases.items():
            angle=-gamma*weight
            if lit==0:continue
            if lit==1:qc.global_phase+=angle
            elif lit>0:qc.p(angle,mapping[lit])
            else:
                qc.global_phase+=angle;qc.p(-angle,mapping[-lit])
        for name,args in reversed(gates):getattr(qc,name)(*args)
        return qc
    def ansatz(self,p=1,measure=True):
        from qiskit import QuantumCircuit,ClassicalRegister
        from qiskit.circuit import ParameterVector
        if not isinstance(p,int) or p<1:raise ValueError('QAOA depth must be a positive integer.')
        mapping,_=self.wiring();q=len(self.logic.inputs)
        if not q:raise ValueError('This instance reduces to a constant; no QAOA search is needed.')
        qc=QuantumCircuit(len(mapping));gamma=ParameterVector('gamma',p);beta=ParameterVector('beta',p)
        qc.h(range(q))
        for layer in range(p):
            qc.compose(self.phase_circuit(gamma[layer]),inplace=True)
            qc.rx(2*beta[layer],range(q))
        if measure:
            register=ClassicalRegister(q,'decision');qc.add_register(register);qc.measure(range(q),register)
        return qc


def build_oracle(stacks,height,terminal_reduction=True,node_limit=2_000_000):
    """Compile movement logic, never enumerate assignments or candidate routes."""
    stacks=tuple(tuple(s) for s in stacks);validate_instance(stacks,height)
    S=len(stacks);N=sum(map(len,stacks));B=N.bit_length();D=(S-1).bit_length()
    L=Logic(node_limit);NOT=L.NOT
    bay=[[[((stack[h] if h<len(stack) else 0)>>b)&1 for b in range(B)] for h in range(height)] for stack in stacks]
    stages=max(0,N-S) if terminal_reduction else N
    active_slots=sum(min(height-1,N-t) for t in range(1,stages+1))
    bound=active_slots+(min(N,S)-1 if terminal_reduction else 0)
    valid=1;slots=[];moves=[]
    def view(target):
        occupied=[[NOT(L.eq(cell,0)) for cell in stack] for stack in bay]
        top=[[L.AND(occupied[s][h],1 if h==height-1 else NOT(occupied[s][h+1])) for h in range(height)] for s in range(S)]
        is_target=[[L.eq(cell,target) for cell in stack] for stack in bay]
        source=[L.any(row) for row in is_target]
        exposed=L.any(L.AND(is_target[s][h],top[s][h]) for s in range(S) for h in range(height))
        return occupied,top,is_target,source,exposed
    for target in range(1,stages+1):
        for step in range(min(height-1,N-target)):
            occupied,top,is_target,source,exposed=view(target)
            blocked=NOT(exposed)
            if blocked==0:
                slots.append(dict(target=target,step=step,inputs=[]));continue
            code=[L.input(f'destination[{target},{step},{b}]') for b in range(D)]
            slots.append(dict(target=target,step=step,inputs=list(code)))
            chosen=[L.eq(code,s) for s in range(S)]
            legal=L.any(L.all((chosen[s],NOT(source[s]),NOT(occupied[s][-1]))) for s in range(S))
            canonical=L.OR(L.AND(blocked,legal),L.AND(NOT(blocked),L.eq(code,0)))
            valid=L.AND(valid,canonical)
            perform=L.AND(valid,blocked);moves.append(perform)
            from_cell=[[L.all((source[s],top[s][h],perform)) for h in range(height)] for s in range(S)]
            moving=[L.xor_all(L.AND(from_cell[s][h],bay[s][h][b]) for s in range(S) for h in range(height)) for b in range(B)]
            updated=[]
            for s in range(S):
                stack=[]
                for h in range(height):
                    insert=L.all((perform,chosen[s],NOT(occupied[s][h]),1 if h==0 else occupied[s][h-1]))
                    stack.append([L.XOR(L.AND(NOT(from_cell[s][h]),bay[s][h][b]),L.AND(insert,moving[b])) for b in range(B)])
                updated.append(stack)
            bay=updated
        occupied,top,is_target,source,exposed=view(target)
        valid=L.AND(valid,exposed)
        bay=[[[L.AND(NOT(L.AND(valid,is_target[s][h])),bit) for bit in bay[s][h]] for h in range(height)] for s in range(S)]
    terminal=[]
    if terminal_reduction:
        # Galle terminal lemma: with <=S containers, minimum remaining work is
        # the number of containers above a smaller-priority container.
        for c in range(stages+1,N+1):
            terms=[]
            for s in range(S):
                earlier=0
                for h in range(height):
                    terms.append(L.AND(L.eq(bay[s][h],c),earlier))
                    smaller=L.AND(NOT(L.eq(bay[s][h],0)),L.less_const(bay[s][h],c))
                    earlier=L.OR(earlier,smaller)
            terminal.append(L.AND(valid,L.any(terms)))
    phases=Counter(moves+terminal);phases[NOT(valid)]+=bound+1
    phases={lit:weight for lit,weight in phases.items() if lit!=0 and weight}
    return Oracle(stacks,height,terminal_reduction,L,slots,phases,valid,moves,terminal,stages,bound)


def decode_plan(oracle,bits):
    """Independent ordinary crane replay of a measured decision string.

    This is used only AFTER measurement or during tests, not for building the
    phase circuit. Invalid codes are rejected, never repaired into a good route.
    """
    if len(bits)!=len(oracle.logic.inputs) or any(v not in (0,1) for v in bits):raise ValueError('Invalid decision bitstring.')
    choice=dict(zip(oracle.logic.inputs,bits));bay=[list(s) for s in oracle.stacks]
    moves=[];cursor=0;relocations=0
    for target in range(1,oracle.stages+1):
        source=next(s for s,stack in enumerate(bay) if target in stack)
        for step in range(min(oracle.height-1,sum(map(len,oracle.stacks))-target)):
            slot=oracle.slots[cursor];cursor+=1
            assert (slot['target'],slot['step'])==(target,step)
            code=sum(choice[node]<<j for j,node in enumerate(slot['inputs']))
            if bay[source][-1]==target:
                if code: return dict(valid=False,complete=False,reason='noncanonical inactive action')
                continue
            if code>=len(bay) or code==source or len(bay[code])>=oracle.height:
                return dict(valid=False,complete=False,reason='illegal destination')
            c=bay[source].pop();bay[code].append(c);relocations+=1
            moves.append(dict(type='relocate',container=c,source=source+1,destination=code+1))
        if bay[source][-1]!=target:return dict(valid=False,complete=False,reason='target not exposed')
        bay[source].pop();moves.append(dict(type='retrieve',container=target,source=source+1))
    prefix=relocations
    # Exact terminal completion: an empty stack exists whenever a remaining
    # target is blocked and remaining container count is <= number of stacks.
    while any(bay):
        target=min(c for s in bay for c in s);source=next(s for s,stack in enumerate(bay) if target in stack)
        if bay[source][-1]==target:
            bay[source].pop();moves.append(dict(type='retrieve',container=target,source=source+1))
        else:
            dest=next(s for s,stack in enumerate(bay) if not stack)
            c=bay[source].pop();bay[dest].append(c);relocations+=1
            moves.append(dict(type='relocate',container=c,source=source+1,destination=dest+1))
    return dict(valid=True,complete=True,relocations=relocations,prefix_relocations=prefix,
                terminal_relocations=relocations-prefix,moves=moves)


# ============================================================================
# PREDICATE ENCODING   (from galle_predicates.py)
# ============================================================================
# Exact Galle feasibility indicators with reusable coherent scratch registers.
#
# The search register contains presolved Galle variables only. Constraint truth is
# computed by reversible arithmetic, phased and uncomputed one row at a time.
# There are no slack decision variables and no full-instance energy lookup table.
# This is a general diagonal Hamiltonian, not a claim that indicators are QUBO.

def compile_row(row):
    L=Logic();keys=sorted(row.terms);inputs={i:L.input(f'x[{i}]') for i in keys}
    minimum=sum(min(0,c) for c in row.terms.values())
    total=sum(abs(c) for c in row.terms.values());rhs=row.rhs-minimum
    width=max(1,total.bit_length());accumulator=[0]*width
    for i in keys:
        coefficient=row.terms[i];bit=inputs[i] if coefficient>0 else L.NOT(inputs[i]);weight=abs(coefficient)
        carry=0;new=[]
        for j,a in enumerate(accumulator):
            b=bit if (weight>>j)&1 else 0;ab=L.XOR(a,b)
            new.append(L.XOR(ab,carry));carry=L.OR(L.AND(a,b),L.AND(carry,ab))
        accumulator=new
    if rhs<0:satisfied=0
    elif row.sense=='eq':satisfied=0 if rhs>total else L.eq(accumulator,rhs)
    elif row.sense=='le':satisfied=1 if rhs>=total else L.less_const(accumulator,rhs+1)
    else:raise ValueError('Unsupported constraint sense')
    indicator=L.NOT(satisfied)
    oracle=Oracle((),0,False,L,[],{indicator:1},satisfied,[],[],0,0)
    return keys,oracle


def pauli_z_terms(merged):
    """Rewrite sum_S c_S prod_{i in S} x_i exactly as const + sum_T a_T Z_T.

    Uses x = (1-Z)/2. Terms from different constraints that share a parity are
    added before any gate is chosen, so overlapping constraints share rotations.
    Returns (constant, [(sorted qubit tuple, coefficient), ...]).
    """
    from fractions import Fraction
    from itertools import combinations
    const=Fraction(0);terms={}
    for mono,c in merged.items():
        k=len(mono);c=Fraction(c)
        const+=c/2**k
        for r in range(1,k+1):
            for T in combinations(sorted(mono),r):
                terms[T]=terms.get(T,Fraction(0))+c*(-1)**r/2**k
    ordered=sorted(((T,a) for T,a in terms.items() if a),key=lambda item:(len(item[0]),item[0]))
    return float(const),[(T,float(a)) for T,a in ordered]


class PredicateModel:
    def __init__(self,stacks,height,scratch_banks=1,direct_cutoff=5,presolve='standard'):
        if not 1<=scratch_banks<=16:raise ValueError('Scratch banks must be 1..16.')
        self.model=GalleModel(stacks,height);self.presolve_mode=presolve
        if presolve not in ('standard','strong'):raise ValueError(f"presolve must be 'standard' or 'strong', not {presolve!r}")  # FIX (Sim9) 11
        self.presolve=Presolve(self.model) if presolve=='standard' else StrongPresolve(self.model,direct_cutoff);p=self.presolve
        if not 0<=direct_cutoff<=5:raise ValueError('Local synthesis cutoff must be 0..5.')
        self.n=len(p.roots);self.banks=scratch_banks;self.direct_cutoff=direct_cutoff
        low=p.objective_offset+sum(min(0,v) for v in p.objective.values())
        high=p.objective_offset+sum(max(0,v) for v in p.objective.values())
        # Valid for the entire Boolean objective domain, no feasible solution,
        # optimal answer, classical route or MILP is used to set this weight.
        self.weight=high-low+1;self.rows=[];seen=set();cache={};self.polynomials={}
        for row in p.reduced_rows:
            identity=(tuple(sorted(row.terms.items())),row.sense,row.rhs)
            if identity in seen:continue
            seen.add(identity)
            # Share symbolic templates for repeated coefficient patterns;
            # only small arithmetic circuits, never evaluated bitstrings.
            keys=sorted(row.terms)
            signature=(tuple(row.terms[i] for i in keys),row.sense,row.rhs)
            if signature not in cache:cache[signature]=compile_row(row)[1]
            self.rows.append((row,keys,cache[signature]))
            if len(keys)<=direct_cutoff and signature not in self.polynomials:
                # At most 32 truth values for ONE constraint, not a table of
                # routes or full-instance energies. Exact multilinear synthesis.
                values=[int(not row.holds({i:(mask>>j)&1 for j,i in enumerate(keys)})) for mask in range(1<<len(keys))]
                for j in range(len(keys)):
                    for mask in range(len(values)):
                        if mask & (1<<j):values[mask]-=values[mask^(1<<j)]
                self.polynomials[signature]={mask:v for mask,v in enumerate(values) if v}
        self.scratch=max((len(oracle.wiring()[1]) for _,keys,oracle in self.rows if len(keys)>direct_cutoff),default=0)
        self.total=self.n+self.banks*self.scratch
        self.low=low;self.high=high;self.templates=len(cache)
        # All diagonal terms commute. Merge repeated monomials across rows
        # before decomposing gates, including exact coefficient cancellations.
        self.merged=Counter({():p.objective_offset})
        self.merged.update({(i,):v for i,v in p.objective.items()})
        self.raw_phase_terms=0
        for row,keys,_ in self.rows:
            if len(keys)>direct_cutoff:continue
            signature=(tuple(row.terms[i] for i in keys),row.sense,row.rhs)
            for mask,coefficient in self.polynomials[signature].items():
                monomial=tuple(i for j,i in enumerate(keys) if mask&(1<<j))
                self.merged[monomial]+=self.weight*coefficient;self.raw_phase_terms+=bool(monomial)
        self.merged={key:v for key,v in self.merged.items() if v}
        self.pauli_constant,self.pauli_terms=pauli_z_terms(self.merged)
    def energy(self,bits):
        if len(bits)!=self.n or any(x not in (0,1) for x in bits):raise ValueError('Invalid Galle decision string')
        p=self.presolve
        return p.objective_offset+sum(v*bits[i] for i,v in p.objective.items())+self.weight*sum(not row.holds(bits) for row,_,_ in self.rows)
    def resources(self,p=1):
        counts=Counter();phase_counts=Counter(str(len(key)) for key in self.merged if key)
        for row,keys,oracle in self.rows:
            if len(keys)>self.direct_cutoff:counts.update(name for name,_ in oracle.forward_gates())
        return dict(method='Galle predicate QAOA',decision_qubits=self.n,clean_work_qubits=self.banks*self.scratch,
                    scratch_per_bank=self.scratch,scratch_banks=self.banks,total_logical_qubits=self.total,
                    constraint_rows=len(self.rows),arithmetic_templates=self.templates,penalty_weight=self.weight,
                    local_synthesis_cutoff=self.direct_cutoff,direct_phase_gates_by_arity_per_layer=dict(phase_counts),
                    raw_local_constraint_phase_terms=self.raw_phase_terms,merged_phase_terms=sum(bool(key) for key in self.merged),
                    pauli_z_terms=len(self.pauli_terms),pauli_ladder_cx_per_layer=sum(2*(len(t)-1) for t,_ in self.pauli_terms),
                    objective_domain=[self.low,self.high],qaoa_depth=p,
                    compute_uncompute_ccx=2*p*counts['ccx'],compute_uncompute_cx=2*p*counts['cx'],
                    ccx_cx_expansion_estimate=2*p*(6*counts['ccx']+counts['cx']),routing_included=False,
                    physical_qubits=None,note='Exact ground-state reformulation of Galle feasibility; no slack decision variables. Indicators are generally nonquadratic. Constraints with <=5 variables use local Boolean phase synthesis; larger ones reuse scratch. CX expansion estimate excludes direct phase synthesis and routing. Error-correction overhead is not included.')
    def circuit(self,p=1,scale=1,synthesis='mcp'):
        """synthesis='mcp': multi-controlled phases (original).
        synthesis='pauli': exact Z-parity rotations with CX ladders; the same
        unitary including global phase, usually with far fewer CX gates."""
        from qiskit import QuantumCircuit,ClassicalRegister
        from qiskit.circuit import ParameterVector
        if p<1 or not self.n:raise ValueError('Positive depth and nonconstant encoding required.')
        qc=QuantumCircuit(self.total);gamma=ParameterVector('gamma',p);beta=ParameterVector('beta',p)
        qc.h(range(self.n))
        # Rows commute. A batch has disjoint decision variables and independent
        # work banks; Qiskit's DAG can schedule their gates in parallel.
        pending=[row for row in self.rows if len(row[1])>self.direct_cutoff];schedule=[]
        while pending:
            batch=[];used=set();rest=[]
            for row in pending:
                if len(batch)<self.banks and not used.intersection(row[1]):batch.append(row);used.update(row[1])
                else:rest.append(row)
            schedule.append(batch);pending=rest
        if synthesis not in ('mcp','pauli'):raise ValueError("synthesis must be 'mcp' or 'pauli'")
        for layer in range(p):
            if synthesis=='pauli':
                qc.global_phase+=-gamma[layer]*self.pauli_constant/scale
                for qubits,a in self.pauli_terms:
                    q=list(qubits)
                    for i in range(len(q)-1):qc.cx(q[i],q[i+1])
                    qc.rz(2*gamma[layer]*a/scale,q[-1])
                    for i in reversed(range(len(q)-1)):qc.cx(q[i],q[i+1])
            else:
              for qubits,coefficient in self.merged.items():
                angle=-gamma[layer]*coefficient/scale
                if not qubits:qc.global_phase+=angle
                elif len(qubits)==1:qc.p(angle,qubits[0])
                else:qc.mcp(angle,list(qubits[:-1]),qubits[-1])
            for batch in schedule:
                for bank,(row,keys,oracle) in enumerate(batch):
                    mapping,work=oracle.wiring()
                    wiring=keys+[self.n+bank*self.scratch+j for j in range(len(work))]
                    qc.compose(oracle.phase_circuit(gamma[layer]*self.weight/scale),qubits=wiring,inplace=True)
            qc.rx(2*beta[layer],range(self.n))
        cr=ClassicalRegister(self.n,'decision');qc.add_register(cr);qc.measure(range(self.n),cr)
        return qc


# ============================================================================
# HYBRID ENCODING   (from hybrid_encoding.py)
# ============================================================================
# Hybrid encoding of Galle CRP-I for QAOA (exact).
#
# Constraints with <= direct_cutoff variables keep the predicate method's direct
# phase polynomial. Larger constraints (mainly capacity rows) use the exact slack
# penalty r(r+1)/2 from Sim5 proof A instead of reversible adders, so they cost
# quadratic terms plus a few slack qubits instead of Toffoli-heavy arithmetic.
#
# Every violated row costs at least the penalty weight W = high - low + 1 of the
# objective domain, so every global minimum is a feasible optimal plan. Checked by
# brute force (test_fixes.py and the 15-bay check in the results doc).
#
# Slack qubits are ordinary decision variables: they get H, the mixer and a
# measurement. Only the first n_decision bits are decoded into a plan.

def hybrid_polynomial(pm):
    """Return (poly, n_slack): pm.merged plus slack penalties for large rows."""
    n = pm.n; poly = Counter(pm.merged); aux = 0; W = pm.weight
    for row, keys, _ in pm.rows:
        if len(keys) <= pm.direct_cutoff:
            continue
        terms = dict(row.terms); c = -row.rhs
        if row.sense == 'le':
            maximum = row.rhs - sum(min(0, v) for v in row.terms.values())
            for w in bounded_weights(maximum // 2):
                terms[n + aux] = 2 * w; aux += 1
            items = sorted(terms.items())                    # P = r(r+1)/2, r = sum + c
            poly[()] += W * c * (c + 1) // 2
            for i, v in items:
                poly[(i,)] += W * (v * v + 2 * c * v + v) // 2
            for a, (i, v) in enumerate(items):
                for j, w in items[a + 1:]:
                    poly[(i, j)] += W * v * w
        else:                                                # P = r^2
            items = sorted(terms.items())
            poly[()] += W * c * c
            for i, v in items:
                poly[(i,)] += W * (v * v + 2 * c * v)
            for a, (i, v) in enumerate(items):
                for j, w in items[a + 1:]:
                    poly[(i, j)] += W * 2 * v * w
    return {k: v for k, v in poly.items() if v}, aux


class HybridModel:
    def __init__(self, stacks, height, direct_cutoff=5, presolve='standard'):
        self.pm = pm = PredicateModel(stacks, height, 1, direct_cutoff, presolve)
        self.model, self.presolve, self.weight = pm.model, pm.presolve, pm.weight
        self.low, self.high = pm.low, pm.high
        self.poly, self.n_slack = hybrid_polynomial(pm)
        self.n_decision = pm.n
        self.n = pm.n + self.n_slack
        self.pauli_constant, self.pauli_terms = pauli_z_terms(self.poly)

    def energy(self, bits):
        if len(bits) != self.n or any(b not in (0, 1) for b in bits):
            raise ValueError('Invalid hybrid bitstring')
        return sum(c * all(bits[i] for i in mono) for mono, c in self.poly.items())

    def resources(self, p=1):
        cx = sum(2 * (len(t) - 1) for t, _ in self.pauli_terms)
        return dict(method='Galle hybrid QAOA (direct phases + slack penalties)', decision_qubits=self.n_decision,
                    slack_qubits=self.n_slack, total_logical_qubits=self.n, penalty_weight=self.weight,
                    pauli_z_terms=len(self.pauli_terms), logical_cx=p * cx, qaoa_depth=p, routing_included=False,
                    physical_qubits=None, local_synthesis_cutoff=self.pm.direct_cutoff,
                    note='Exact: every violated constraint costs >= penalty weight. Slack qubits are measured variables, not scratch. CX = Pauli-Z ladder count before routing.')

    def circuit(self, p=1, scale=1):
        from qiskit import QuantumCircuit, ClassicalRegister
        from qiskit.circuit import ParameterVector
        if p < 1 or not self.n:
            raise ValueError('Positive depth and nonconstant encoding required.')
        qc = QuantumCircuit(self.n); gamma = ParameterVector('gamma', p); beta = ParameterVector('beta', p)
        qc.h(range(self.n))
        for layer in range(p):
            qc.global_phase += -gamma[layer] * self.pauli_constant / scale
            for qubits, a in self.pauli_terms:
                q = list(qubits)
                for i in range(len(q) - 1):
                    qc.cx(q[i], q[i + 1])
                qc.rz(2 * gamma[layer] * a / scale, q[-1])
                for i in reversed(range(len(q) - 1)):
                    qc.cx(q[i], q[i + 1])
            qc.rx(2 * beta[layer], range(self.n))
        cr = ClassicalRegister(self.n, 'decision'); qc.add_register(cr); qc.measure(range(self.n), cr)
        return qc


def hybrid(pm):
    """Resource summary used by scaling_scan.py and count45.py."""
    poly, aux = hybrid_polynomial(pm)
    _, Z = pauli_z_terms(poly)
    return dict(qubits=pm.n + aux, cx=sum(2 * (len(t) - 1) for t, _ in Z), poly=poly, aux=aux)


# ============================================================================
# PROBLEM WRAPPER, DECODERS, CIRCUITS, IBM WORKFLOW   (from hardware_solver.py)
# ============================================================================
# IBM/Qiskit full-instance QAOA. Compile first; hardware submission is explicit.
#
# No production path enumerates bitstrings, builds an energy table or imports
# published solutions. Measurement outcomes alone are decoded and scored.

#!/usr/bin/env python3


def verify_moves(initial,height,moves):
    bay=[list(s) for s in initial];target=1;relocations=0
    for move in moves:
        s=move['source']-1;c=move['container']
        if not bay[s] or bay[s][-1]!=c:raise ValueError('Non-top move in decoded plan')
        if move['type']=='retrieve':
            if c!=target:raise ValueError('Incorrect retrieval order')
            bay[s].pop();target+=1
        elif move['type']=='relocate':
            d=move['destination']-1
            if target not in bay[s] or c==target or d==s or len(bay[d])>=height:raise ValueError('Illegal restricted relocation')
            bay[d].append(bay[s].pop());relocations+=1
        else:raise ValueError('Unknown move')
    if any(bay):raise ValueError('Incomplete route')
    return relocations


def decode_galle(model,x):
    """Physical reconstruction plus exact <=S terminal completion, no search."""
    if model.violations(x):return dict(valid=False,complete=False)
    C,S,N=model.C,model.S,model.N;states=[];moves=[]
    try:
        for t in range(1,N+1):
            state=[]
            for s in range(1,S+1):
                members=[c for c in range(t,C+1) if x[model.index[t,C+s,c]]]
                state.append(sorted(members,key=lambda c:sum(x[model.index[t,d,c]] for d in members)))
            encoding=model.encoding(state)
            if any(x[model.index[t,c,d]]!=encoding[c,d] for c in range(t,C+S+1) for d in range(t,C+1)):
                return dict(valid=False,complete=False,reason='nonphysical below relation')
            states.append(state)
        if tuple(map(tuple,states[0]))!=model.stacks:raise ValueError('Initial configuration mismatch')
        for t in range(1,N):
            bay=[list(s) for s in states[t-1]];nxt=states[t]
            source=next(s for s,stack in enumerate(bay) if t in stack)
            while bay[source][-1]!=t:
                c=bay[source][-1];dest=next(s for s,stack in enumerate(nxt) if c in stack)
                if dest==source or len(bay[dest])>=model.T:raise ValueError('Invalid transition')
                bay[dest].append(bay[source].pop());moves.append(dict(type='relocate',container=c,source=source+1,destination=dest+1))
            bay[source].pop();moves.append(dict(type='retrieve',container=t,source=source+1))
            if bay!=nxt:raise ValueError('Invalid transition order')
        bay=[list(s) for s in states[-1]]
        while any(bay):
            t=min(c for s in bay for c in s);source=next(s for s,stack in enumerate(bay) if t in stack)
            c=bay[source][-1]
            if c==t:bay[source].pop();moves.append(dict(type='retrieve',container=t,source=source+1))
            else:
                dest=next(s for s,stack in enumerate(bay) if not stack)
                bay[dest].append(bay[source].pop());moves.append(dict(type='relocate',container=c,source=source+1,destination=dest+1))
        relocations=verify_moves(model.stacks,model.T,moves)
        return dict(valid=True,complete=True,relocations=relocations,moves=moves,model_objective=model.cost(x))
    except (ValueError,StopIteration,IndexError):return dict(valid=False,complete=False,reason='physical replay rejected assignment')


class Problem:
    def __init__(self,stacks,height,method='predicate',terminal=True,node_limit=2_000_000,scratch_banks=1,direct_cutoff=5,max_model_rows=200_000,synthesis='mcp',presolve='standard'):
        if presolve not in PRESOLVES:raise ValueError('presolve must be standard or strong')
        self.presolve_mode=presolve
        self.synthesis=synthesis
        validate_instance(stacks,height)
        self.stacks=tuple(tuple(s) for s in stacks);self.height=height;self.method=method
        self.oracle=None;self.qubo=None;self.predicate=None;self.hybrid=None
        if method in ('predicate','galle','hybrid'):
            n=sum(map(len,stacks));s=len(stacks)
            if n>s:
                total_m=(n-s)*(n+s-1)//2
                total_m2=(n-1)*n*(2*n-1)//6-(s-1)*s*(2*s-1)//6
                rows=n*(n+s)+2*total_m+(1+2*s)*(total_m2-total_m)+s*(n-s)+s*(s-1)//2+3*total_m2+(3*s-3)*total_m
                if max_model_rows and rows>max_model_rows:
                    raise MemoryError(f'Galle construction has {rows:,} rows before preprocessing. This compilation-host guard is {max_model_rows:,}; raise --max-model-rows on a larger host, or compile the coherent route model. No hardware job submitted.')
        if method=='coherent':
            self.oracle=build_oracle(stacks,height,terminal,node_limit);self.n=len(self.oracle.logic.inputs)
            self.scale=max(1,self.oracle.bound+1)
        elif method=='predicate':
            self.predicate=PredicateModel(stacks,height,scratch_banks,direct_cutoff,presolve);self.n=self.predicate.n
            self.model=self.predicate.model;self.scale=max(1,self.predicate.weight)
        elif method=='hybrid':
            self.hybrid=HybridModel(stacks,height,direct_cutoff,presolve);self.n=self.hybrid.n
            self.model=self.hybrid.model;self.scale=max(1,self.hybrid.weight)
        elif method=='galle':
            self.model=GalleModel(stacks,height)
            # This ordinary feasible witness bounds penalty strength only. It is
            # not a warm start, a supplied optimum, or a fallback answer.
            witness=feasible_upper_bound(stacks,height)
            self.qubo=Qubo(self.model,witness['upper_bound'],presolve=presolve);self.n=len(self.qubo.names)
            self.scale=max([1,*map(abs,self.qubo.linear.values()),*map(abs,self.qubo.quadratic.values())])
        else:raise ValueError('Method must be predicate, hybrid, coherent or galle')
    def resources(self,p=1):
        if self.oracle:return dict(self.oracle.resources(p),energy_scale=self.scale)
        if self.predicate:return dict(self.predicate.resources(p),energy_scale=self.scale)
        if self.hybrid:return dict(self.hybrid.resources(p),energy_scale=self.scale)
        return dict(method='Galle CRP-I QUBO baseline',decision_qubits=self.qubo.physical_bits,
                    auxiliary_qubits=self.n-self.qubo.physical_bits,measured_qubits=self.n,total_logical_qubits=self.n,
                    linear_terms=len(self.qubo.linear),quadratic_terms=len(self.qubo.quadratic),
                    qaoa_depth=p,logical_cp_gates=p*len(self.qubo.quadratic),routing_included=False,
                    penalty_weight=self.qubo.weight,energy_scale=self.scale,physical_qubits=None,
                    note='QUBO slack qubits are variables, not clean scratch. Hardware routing and error correction are not included.')
    def circuit(self,p):
        def monitor(circuit):
            from qiskit import ClassicalRegister
            if circuit.num_qubits>self.n:
                register=ClassicalRegister(circuit.num_qubits-self.n,'workspace');circuit.add_register(register)
                circuit.measure(range(self.n,circuit.num_qubits),register)
            return circuit
        if self.predicate:return monitor(self.predicate.circuit(p,self.scale,self.synthesis))
        if self.hybrid:return self.hybrid.circuit(p,self.scale)
        if self.oracle:
            circuit=self.oracle.ansatz(p)
            gamma={par:par/self.scale for par in circuit.parameters if par.name.startswith('gamma')}
            return monitor(circuit.assign_parameters(gamma))
        from qiskit import QuantumCircuit,ClassicalRegister
        from qiskit.circuit import ParameterVector
        if p<1 or self.n<1:raise ValueError('Need positive depth and at least one variable.')
        qc=QuantumCircuit(self.n);gammas=ParameterVector('gamma',p);betas=ParameterVector('beta',p)
        qc.h(range(self.n))
        for layer in range(p):
            gamma=gammas[layer]/self.scale;qc.global_phase-=gamma*self.qubo.offset
            for i,v in self.qubo.linear.items():qc.p(-gamma*v,i)
            for (i,j),v in self.qubo.quadratic.items():qc.cp(-gamma*v,i,j)
            qc.rx(2*betas[layer],range(self.n))
        cr=ClassicalRegister(self.n,'decision');qc.add_register(cr);qc.measure(range(self.n),cr)
        return qc
    def outcome(self,bits):
        if self.oracle:
            evaluation=self.oracle.evaluate(bits);decoded=decode_plan(self.oracle,bits)
            if evaluation['valid']!=decoded['valid']:raise AssertionError('Quantum logic / physical replay mismatch')
            if decoded['valid']:
                if evaluation['energy']!=verify_moves(self.stacks,self.height,decoded['moves']):raise AssertionError('Incorrect oracle cost')
            return dict(decoded,energy=evaluation['energy'],zero_penalty=evaluation['valid'])
        encoding=self.predicate or self.hybrid or self.qubo
        energy=encoding.energy(bits)
        try:x=encoding.presolve.recover(bits)
        except ValueError:return dict(valid=False,complete=False,reason='eliminated variable outside 0/1',energy=energy,zero_penalty=False)  # strong presolve
        decoded=decode_galle(self.model,x)
        return dict(decoded,energy=energy,zero_penalty=bool(decoded['valid'] and energy==self.model.cost(x)))


def stats(counts,problem,include_plans=True):
    shots=sum(counts.values())
    if shots<=0:raise ValueError('No measurement shots received')
    total=0.;total2=0.;feasible=0;zero=0;best=None
    for key,count in counts.items():
        bitstring=key.replace(' ','')
        if len(bitstring)!=problem.n or any(c not in '01' for c in bitstring):raise ValueError('Measurement register does not match decision encoding')
        bits=[int(c) for c in reversed(bitstring)];record=problem.outcome(bits);energy=record['energy']
        total+=count*energy;total2+=count*energy**2;zero+=count*bool(record['zero_penalty'])
        if record['valid']:
            feasible+=count
            if best is None or record['relocations']<best['relocations']:
                best=dict(record,bitstring=bitstring,observed_count=count)
    mean=total/shots;variance=max(0.,total2/shots-mean**2)
    if best and not include_plans:best={k:v for k,v in best.items() if k!='moves'}
    return dict(shots=shots,mean_energy=mean,energy_standard_error=math.sqrt(variance/max(1,shots-1)),
                feasible_fraction=feasible/shots,zero_penalty_fraction=zero/shots,best_observed=best)


def target_compile(circuit,backend,seed=0):
    from qiskit.transpiler import generate_preset_pass_manager
    if circuit.num_qubits>backend.num_qubits:
        raise ValueError(f'Circuit requires {circuit.num_qubits} total qubits including scratch; backend has {backend.num_qubits}. No job submitted.')
    start=time.perf_counter();pm=generate_preset_pass_manager(optimization_level=2,backend=backend,seed_transpiler=seed)
    compiled=pm.run(circuit)
    report=dict(backend=str(backend.name),backend_qubits=backend.num_qubits,compiled_width=compiled.num_qubits,
        active_qubits=len({q for instruction in compiled.data for q in instruction.qubits}),
        depth=compiled.depth(),two_qubit_depth=compiled.depth(filter_function=lambda instruction:len(instruction.qubits)==2),
        two_qubit_gates=sum(len(instruction.qubits)==2 for instruction in compiled.data),
        gate_counts=dict(compiled.count_ops()),compile_seconds=time.perf_counter()-start,physical_fault_tolerant_estimate=None)
    return compiled,report


class BudgetEnded(Exception):pass


# Median ideal-optimal angles over all 15 benchmark bays (8-20 qubits), in units of
# energy / penalty weight, gammas then betas. QAOA angles "concentrate": they are
# nearly the same across instances, so these transfer to new bays. NOTE the
# negative betas: the original random start (beta in 0.05..0.6) began in the
# wrong half of the landscape. Source: results/bench_*.jsonl, transfer test.
CONCENTRATED_ANGLES={
    'predicate':{1:[0.240,-0.554],2:[0.185,0.346,-0.554,-0.259],3:[0.124,0.229,0.420,-0.570,-0.355,-0.160]},
    # hybrid and QUBO: selected by cross-evaluation over 8 calibration bays each
    # (calibrate_angles.py, select_angles.py); their tuned angles fall into
    # several equivalent basins, so a plain median would not transfer.
    'hybrid':{1:[0.141,-0.501],2:[0.129,0.860,-0.512,-0.181],3:[0.089,0.222,5.500,-0.494,-0.190,0.154]},
    'galle':{1:[0.696,-0.482],2:[0.647,-2.595,-0.409,0.211],3:[0.511,-0.391,-3.013,-1.020,0.490,0.212]},
}


def concentrated_angles(p,method='predicate'):
    """Transferred starting angles for this encoding; for p>3, interpolate the p=3 schedule.
    Methods without a calibrated set (coherent) fall back to the predicate angles."""
    table=CONCENTRATED_ANGLES.get(method,CONCENTRATED_ANGLES['predicate'])
    if p in table:return np.array(table[p],dtype=float)
    g,b=np.array(table[3][:3]),np.array(table[3][3:])
    x=np.linspace(0,1,p);xp=np.linspace(0,1,3)
    return np.r_[np.interp(x,xp,g),np.interp(x,xp,b)]


ramp_angles=concentrated_angles  # backwards-compatible name


def uniform_control(problem,shots,seed):
    """Classical control: score uniformly random bitstrings with the SAME decoder.

    Run with the same total number of shots as the quantum run. QAOA is only
    useful if it beats this control. Nothing quantum is simulated here.
    """
    rng=np.random.default_rng(seed+1_000_003)
    draws=rng.integers(0,2,size=(shots,problem.n),dtype=np.int8)
    counts={}
    for row in draws:
        key=''.join(str(int(b)) for b in reversed(row))
        counts[key]=counts.get(key,0)+1
    return stats(counts,problem,include_plans=False)


def optimize_samples(problem,circuit,sampler,p,shots,max_evaluations,seed,out,event=print,qpu=False,max_qpu_seconds=None,
                     initial_angles=None,control=True,rhobeg=0.05,optimize=True):
    """Shot-based objective, no statevector probabilities or full energy table.

    One final independent validation batch is reserved. QPU jobs are serialized;
    each is capped at the remaining reservation divided by remaining job count.
    max_qpu_seconds is an execution-time ceiling, not a monetary-price quote.
    """
    if shots<1 or max_evaluations<2*p+3:raise ValueError('Need positive shots and >=2*p+3 evaluation jobs (includes final validation).')
    if qpu and (max_qpu_seconds is None or max_qpu_seconds<max_evaluations):
        raise ValueError('Specify a positive total QPU-seconds cap >= maximum evaluation jobs.')
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(seed);history=[];best_theta=None;best_mean=math.inf;best_observed=None
    params={par.name:par for par in circuit.parameters};reserved=0
    def sample(theta,final=False):
        nonlocal best_theta,best_mean,best_observed,reserved
        if len(history)>=max_evaluations-(0 if final else 1):raise BudgetEnded()
        bindings={params[f'gamma[{i}]']:float(theta[i]) for i in range(p) if f'gamma[{i}]' in params}
        bindings.update({params[f'beta[{i}]']:float(theta[p+i]) for i in range(p) if f'beta[{i}]' in params})
        bound=circuit.assign_parameters(bindings)
        if qpu:
            # Reserve a hard per-job cap before dispatch, even if a failed job
            # later omits usage metadata. Never retry a submission automatically.
            cap=max(1,(int(max_qpu_seconds)-reserved)//(max_evaluations-len(history)))
            sampler.options.max_execution_time=cap;reserved+=cap
        event(f"{'Final validation' if final else ('Optimization' if optimize else 'Fixed-angle sampling')}: job {len(history)+1}/{max_evaluations}, {shots} shots")  # FIX: label
        started=time.perf_counter();job=sampler.run([bound],shots=shots)
        jobid=job.job_id()
        # Save receipt immediately; after an uncertain result, retrieve this job
        # rather than submitting a duplicate experiment.
        receipt=dict(job_id=jobid,theta=list(map(float,theta)),shots=shots,hardware=qpu,final_validation=final)
        (out/f'job_{len(history)+1}_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
        result=job.result();counts=result[0].data.decision.get_counts();summary=stats(counts,problem)
        if hasattr(result[0].data,'workspace'):
            workspace=result[0].data.workspace.get_counts()
            summary['workspace_zero_fraction']=sum(v for k,v in workspace.items() if set(k)<= {'0',' '})/sum(workspace.values())
            summary['workspace_postselection_used']=False
        entry=dict(receipt,counts=counts,summary=summary,wall_seconds=time.perf_counter()-started,
                   metadata=result[0].metadata,execution_time_cap_reserved=reserved)
        (out/f'job_{len(history)+1}.json').write_text(json.dumps(entry,indent=2,default=str)+'\n')
        history.append(entry)
        if summary['mean_energy']<best_mean and not final:
            best_mean=summary['mean_energy'];best_theta=np.array(theta,copy=True)
        candidate=summary['best_observed']
        if candidate and (best_observed is None or candidate['relocations']<best_observed['relocations']):best_observed=candidate
        return summary['mean_energy']/problem.scale
    if initial_angles is not None:
        initial=np.asarray(initial_angles,dtype=float)
        if initial.shape!=(2*p,):raise ValueError(f'initial angles need {2*p} numbers: {p} gammas then {p} betas')
    else:initial=concentrated_angles(p,getattr(problem,'method','predicate'))
    try:
        if optimize:minimize(sample,initial,method='COBYLA',options={'maxiter':max_evaluations-1,'rhobeg':rhobeg})
        else:
            # Recommended in the paper: transferred angles, no optimiser; the whole
            # budget is spent sampling. best_theta stays the transferred angles.
            while True:sample(initial)
    except BudgetEnded:pass
    if best_theta is not None:sample(best_theta,final=True)
    result=dict(status='completed' if best_observed else 'no_feasible_sample',hardware_execution=qpu,
                method=problem.method,shots_per_job=shots,total_shots=sum(h['summary']['shots'] for h in history),
                jobs=len(history),best_observed=best_observed,relocations=None if not best_observed else best_observed['relocations'],
                moves=[] if not best_observed else best_observed['moves'],
                final_validation=None if not history else history[-1]['summary'],
                theta=None if best_theta is None else best_theta.tolist(),qpu_seconds_reserved=reserved,
                limitation='No optimality, novelty or quantum-advantage guarantee. Best route may come from a training batch; final validation is reported separately.')
    result['budget']=dict(jobs=len(history),max_jobs=max_evaluations,shots_per_job=shots,depth=p,
                          initial_angles=list(map(float,initial)),optimizer=f'COBYLA, rhobeg {rhobeg}' if optimize else 'none (fixed transferred angles)',start='transferred concentrated angles' if initial_angles is None else 'user-supplied')
    if control and history:
        total=sum(h['summary']['shots'] for h in history)
        u=uniform_control(problem,total,seed);fin=history[-1]['summary']
        qbest=None if not best_observed else best_observed['relocations']
        ubest=None if not u['best_observed'] else u['best_observed']['relocations']
        result['uniform_control']=dict(shots=total,feasible_fraction=u['feasible_fraction'],
            best_relocations=ubest,mean_energy=u['mean_energy'])
        result['comparison_to_uniform']=dict(
            final_batch_feasible_fraction=fin['feasible_fraction'],
            feasible_amplification=None if not u['feasible_fraction'] else fin['feasible_fraction']/u['feasible_fraction'],
            qaoa_best_relocations=qbest,uniform_best_relocations=ubest,
            qaoa_better_than_uniform=None if qbest is None or ubest is None else qbest<ubest,
            note='Same decoder, same total shots. If QAOA does not beat this control, do not claim the quantum circuit helped.')
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result


def read_instance(path,stacks,height):
    if path:
        rows=[[int(v) for v in line.split()] for line in Path(path).read_text().splitlines() if line.strip()]
        if len(rows[0])!=3:raise ValueError('File header must be stacks capacity containers (Group4 format).')
        S,H,N=rows[0]
        if height is not None and height!=H:raise ValueError('Height differs from file header')
        if len(rows)!=S+1 or any(row[0]!=len(row)-1 for row in rows[1:]):raise ValueError('Invalid count-prefixed stack rows')
        bay=tuple(tuple(row[1:]) for row in rows[1:]);height=H
        if sum(map(len,bay))!=N:raise ValueError('Container count mismatch')
    else:
        if height is None:raise ValueError('--height is required with --stacks')
        bay=tuple(tuple(int(v) for v in row.replace(',',' ').split()) for row in stacks.split(';'))
    validate_instance(bay,height);return bay,height


def hardware_main(argv=None):
    parser=argparse.ArgumentParser(prog='rcrp_qaoa_suite.py hardware',description=HARDWARE_DOC)
    src=parser.add_mutually_exclusive_group(required=True);src.add_argument('--file');src.add_argument('--stacks')
    parser.add_argument('--height',type=int);parser.add_argument('--method',choices=['predicate','hybrid','coherent','galle'],default='predicate')
    parser.add_argument('--scratch-banks',type=int,default=1)
    parser.add_argument('--presolve',choices=['standard','strong'],default='standard',help='strong = exact extra variable reduction (fewer qubits)')
    parser.add_argument('--single-job',action='store_true',help='With --fixed-angles: send all shots*evaluations shots as ONE job (saves QPU overhead)')
    parser.add_argument('--synthesis',choices=['mcp','pauli'],default='pauli',help="Predicate phase synthesis (FIX (Sim9) 17: default 'pauli', exact, far fewer CX).")
    parser.add_argument('--direct-cutoff',type=int,default=5,help='Local constraint synthesis up to 5 variables; 0 selects arithmetic-only predicates')
    parser.add_argument('--no-terminal-reduction',action='store_true');parser.add_argument('--depth',type=int,default=1)
    parser.add_argument('--node-limit',type=int,default=2_000_000,help='Compilation-host memory guard, not a QPU qubit cap')
    parser.add_argument('--max-model-rows',type=int,default=200_000,help='Galle compilation-host guard; 0 disables it. Not a QPU qubit cap.')
    parser.add_argument('--output',default='hardware_results');parser.add_argument('--export-circuit',action='store_true')
    parser.add_argument('--backend',help="IBM backend name (e.g. ibm_kingston), 'auto' = least busy device that fits, or 'fake' = rehearse locally on a fake IBM device. Transpiles; submits only with --submit")
    parser.add_argument('--submit',action='store_true',help='Explicitly run paid/account-metered hardware jobs; requires backend and total QPU-seconds cap')
    parser.add_argument('--local-check',action='store_true',help='Small ideal statevector check; never reported as hardware')
    parser.add_argument('--shots',type=int,default=1024)
    parser.add_argument('--evaluations',type=int,default=40,help='Total jobs including final validation. 12 was too few for 15+ qubits in ideal tests.')
    parser.add_argument('--init-angles',help='JSON list of 2*depth starting angles (gammas then betas), e.g. transferred from a smaller instance')
    parser.add_argument('--fixed-angles',action='store_true',help='Recommended: no optimiser; sample every job at the transferred (or --init-angles) angles')
    parser.add_argument('--no-uniform-control',action='store_true',help='Skip the classical uniform-sampling control (not recommended for papers)')
    parser.add_argument('--max-qpu-seconds',type=int);parser.add_argument('--seed',type=int,default=0)
    args=parser.parse_args(argv)
    if args.backend and args.backend!='fake':parser.error('Sim9.2 (fix 27): real IBM devices are used only through the "ibm" workflow '
                                                      '(named account + Open Plan CRN, job registry). Use "ibm init/prepare/submit". '
                                                      'This legacy command still supports --backend fake and --local-check.')
    if args.submit and (not args.backend or args.max_qpu_seconds is None):parser.error('--submit requires --backend and --max-qpu-seconds')
    if args.local_check and (args.backend or args.submit):parser.error('Local simulation and hardware execution are separate modes')
    if args.depth<1 or args.shots<1 or args.evaluations<2*args.depth+3:parser.error('Invalid depth, shots or evaluation budget')
    init=None if not args.init_angles else json.loads(args.init_angles)
    bay,height=read_instance(args.file,args.stacks,args.height)
    start=time.perf_counter();problem=Problem(bay,height,args.method,not args.no_terminal_reduction,args.node_limit,args.scratch_banks,args.direct_cutoff,args.max_model_rows,args.synthesis,presolve=args.presolve)
    out=Path(args.output).expanduser().resolve()/f'run_{time.time_ns()}';out.mkdir(parents=True)
    report=problem.resources(args.depth);report['build_seconds']=time.perf_counter()-start
    report['instance']=dict(stacks_bottom_to_top=bay,height=height)
    report['hardware_execution_at_compilation']=False
    (out/'resources.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)
    (out/'configuration.json').write_text(json.dumps(vars(args),indent=2)+'\n')
    if args.export_circuit or args.backend or args.local_check:
        if problem.n==0:
            result=problem.outcome([]);(out/'constant_result.json').write_text(json.dumps(result,indent=2)+'\n')
            print('No decision qubits remain: this instance is solved analytically; no QAOA or hardware run.',flush=True)
            print(f'Results: {out}',flush=True);return 0
        if args.local_check and report['total_logical_qubits']>20:
            # FIX: a user limit, not a crash; exit cleanly with the reason.
            print(f"Local statevector check is capped at 20 total qubits; this model needs {report['total_logical_qubits']}. Resources were saved; hardware/resource compilation has no such cap.",flush=True)
            print(f'Results: {out}',flush=True);return 2
        backend=None
        if args.backend:
            from qiskit_ibm_runtime import QiskitRuntimeService,SamplerV2
            if args.backend=='fake':
                backend=fake_backend();print(f'REHEARSAL on fake device {backend.name}: local simulation with its noise, no account, no QPU time.',flush=True)
            else:
                service=QiskitRuntimeService()
                backend=(service.least_busy(operational=True,simulator=False,min_num_qubits=report['total_logical_qubits']) if args.backend=='auto' else service.backend(args.backend))
                print(f'Backend: {backend.name} ({backend.num_qubits} qubits)',flush=True)
                if getattr(backend.configuration(),'simulator',False):raise ValueError('Selected backend is a simulator; hardware mode refuses mislabeling')
            if report['total_logical_qubits']>backend.num_qubits:
                raise ValueError(f"Circuit requires {report['total_logical_qubits']} total qubits; {args.backend} has {backend.num_qubits}. No circuit materialized or job submitted.")
        circuit=problem.circuit(args.depth)
        from qiskit import qpy,qasm3
        with (out/'logical.qpy').open('wb') as f:qpy.dump(circuit,f)
        (out/'logical.qasm').write_text(qasm3.dumps(circuit))
        if args.backend:
            circuit,target_report=target_compile(circuit,backend,args.seed)
            (out/'target_resources.json').write_text(json.dumps(target_report,indent=2)+'\n')
            with (out/'isa.qpy').open('wb') as f:qpy.dump(circuit,f)
            if args.submit:
                sampler=SamplerV2(mode=backend);hw=args.backend!='fake'
                jobs=1 if (args.single_job and args.fixed_angles) else args.evaluations
                print(f'Estimated QPU usage: about {qpu_seconds_estimate(jobs,args.shots*args.evaluations//jobs):.0f} s for {jobs} job(s) (IBM quick formula; the cap is {args.max_qpu_seconds} s).',flush=True)
                if args.single_job and args.fixed_angles:
                    run_single_job(problem,circuit,sampler,args.depth,args.shots*args.evaluations,args.seed,out,event=lambda s:print(s,flush=True),
                                   qpu=hw,max_qpu_seconds=args.max_qpu_seconds,initial_angles=init,control=not args.no_uniform_control,backend_name=backend.name)
                else:
                    optimize_samples(problem,circuit,sampler,args.depth,args.shots,args.evaluations,args.seed,out,
                                 event=lambda s:print(s,flush=True),qpu=hw,max_qpu_seconds=args.max_qpu_seconds,
                                 initial_angles=init,control=not args.no_uniform_control,optimize=not args.fixed_angles)
        elif args.local_check:
            from qiskit.primitives import StatevectorSampler
            if args.single_job and args.fixed_angles:
                run_single_job(problem,circuit,StatevectorSampler(seed=args.seed),args.depth,args.shots*args.evaluations,args.seed,out,
                               event=lambda s:print(s,flush=True),initial_angles=init,control=not args.no_uniform_control,backend_name='ideal statevector')
            else:
                optimize_samples(problem,circuit,StatevectorSampler(seed=args.seed),args.depth,args.shots,args.evaluations,
                             args.seed,out,event=lambda s:print(s,flush=True),initial_angles=init,control=not args.no_uniform_control,optimize=not args.fixed_angles)
    print(f'Results: {out}',flush=True);return 0


# ============================================================================
# NUMPY QAOA SIMULATOR, TUNING, BASELINES, GATE COUNTS   (from paper_sim.py)
# ============================================================================
# NumPy-only research harness for the paper (no Qiskit needed).
#
# Everything here is an EVALUATION tool. It may enumerate all 2^n bitstrings of
# small instances to obtain exact probabilities and baselines; the production
# solver (hardware_solver.py) never does that.
#
# Contents
#   * exact diagonal energies for the predicate Hamiltonian and the Galle QUBO
#   * ideal QAOA statevector simulation (decision register only; clean scratch
#     returns to |0> in the ideal circuit, so it does not change outcome odds)
#   * baselines: uniform sampling, simulated annealing on the same energy, greedy
#   * logical two-qubit gate counts for both encodings (Walsh/Pauli-Z synthesis,
#     compute-uncompute arithmetic), independent of any transpiler
#   * a global depolarising + readout noise model

# ---------------------------------------------------------------- energies
def _bits(n):
    idx = np.arange(1 << n, dtype=np.int64)
    return ((idx[:, None] >> np.arange(n)) & 1).astype(np.int8)


def _row_violations(rows, X):
    viol = np.zeros(X.shape[0], dtype=np.int32)
    for row in rows:
        s = np.zeros(X.shape[0], dtype=np.int64)
        for i, c in row.terms.items():
            s += c * X[:, i]
        viol += (s != row.rhs) if row.sense == "eq" else (s > row.rhs)
    return viol


def _landscape_predicate_or_qubo(problem: Problem):
    """Return dict(E, legal, optimum, n) for an exact energy table.

    legal = the measured string replays as a legal complete plan (decision bits
    for the predicate method; physical bits for the QUBO, whatever the slack).
    """
    if problem.predicate is not None:
        pm = problem.predicate; n = pm.n; X = _bits(n); p = pm.presolve
        R = np.full(1 << n, float(p.objective_offset))
        for i, v in p.objective.items():
            R += v * X[:, i]
        viol = _row_violations([r for r, _, _ in pm.rows], X)
        E = R + pm.weight * viol
        legal = viol == 0
    else:
        q = problem.qubo; n = len(q.names); X = _bits(n); p = q.presolve
        E = np.full(1 << n, float(q.offset))
        for i, v in q.linear.items():
            E += v * X[:, i]
        for (i, j), v in q.quadratic.items():
            E += v * (X[:, i] & X[:, j])
        legal = _row_violations(p.reduced_rows, X[:, :q.physical_bits]) == 0
    return dict(E=E, legal=legal, optimum=float(E.min()), n=n)


# ---------------------------------------------------------------- QAOA
def _mix(psi, beta, n):
    c, s = math.cos(beta), -1j * math.sin(beta)
    for q in range(n):
        v = psi.reshape(-1, 2, 1 << q)
        a = v[:, 0, :].copy(); b = v[:, 1, :]
        v[:, 0, :] = c * a + s * b
        v[:, 1, :] = s * a + c * b
    return psi


def qaoa_probs(E, theta, p, scale, n):
    psi = np.full(len(E), 1 / math.sqrt(len(E)), dtype=complex)
    for layer in range(p):
        psi *= np.exp(-1j * theta[layer] * E / scale)
        psi = _mix(psi, theta[p + layer], n)
    P = np.abs(psi) ** 2
    return P / P.sum()


def ramp(p, gamma_max=1.2, beta_max=0.6):
    t = (np.arange(p) + .5) / p
    return np.r_[gamma_max * t, beta_max * (1 - t)]


def tune(L, scale, pmax=3, restarts=4, seed=0):
    """Best-effort exact-expectation tuning with warm starts p -> p+1."""
    rng = np.random.default_rng(seed); E = L["E"]; n = L["n"]; out = {}; prev = None
    for p in range(1, pmax + 1):
        starts = [ramp(p)] + [np.r_[rng.uniform(0, math.pi, p), rng.uniform(0, math.pi / 2, p)] for _ in range(restarts)]
        if prev is not None:
            g, b = prev[:p - 1], prev[p - 1:]
            x = np.linspace(0, 1, p); xp = np.linspace(0, 1, p - 1) if p > 2 else np.array([0., 1.])
            starts.insert(0, np.r_[np.interp(x, xp, g if p > 2 else np.r_[g, g]), np.interp(x, xp, b if p > 2 else np.r_[b, b])])
        best = None
        for x0 in starts:
            r = minimize(lambda t: qaoa_probs(E, t, p, scale, n) @ E, x0, method="Nelder-Mead",
                         options=dict(maxiter=300 * p, xatol=1e-4, fatol=1e-7))
            if best is None or r.fun < best.fun:
                best = r
        prev = best.x
        P = qaoa_probs(E, best.x, p, scale, n)
        out[p] = dict(theta=best.x, P=P, mean_E=float(best.fun))
    return out


def shot_protocol(L, scale, p, shots, jobs, seed, initial=None, rhobeg=.3):
    """Mirror of hardware_solver.optimize_samples on an exact simulator.

    COBYLA on sampled mean energy, jobs-1 optimisation batches, then one
    independent final batch at the best training angles.
    """
    E, n = L["E"], L["n"]; N = len(E); rng = np.random.default_rng(seed); hist = []
    class Stop(Exception): pass
    def f(t):
        if len(hist) >= jobs - 1:
            raise Stop
        P = qaoa_probs(E, t, p, scale, n); s = rng.choice(N, shots, p=P)
        hist.append((E[s].mean(), np.array(t), s)); return E[s].mean() / scale
    x0 = ramp(p) if initial is None else np.asarray(initial)
    try:
        minimize(f, x0, method="COBYLA", options=dict(maxiter=jobs - 1, rhobeg=rhobeg))
    except Stop:
        pass
    theta = min(hist, key=lambda h: h[0])[1]
    P = qaoa_probs(E, theta, p, scale, n); final = rng.choice(N, shots, p=P)
    every = np.concatenate([h[2] for h in hist] + [final])
    return dict(theta=theta, final=final, every=every, jobs=len(hist) + 1)


# ---------------------------------------------------------------- baselines
def uniform_draw(N, shots, seed):
    return np.random.default_rng(seed + 7919).integers(0, N, shots)


def simulated_annealing(L, evaluations, seed, T0=None, T1=0.05):
    """Single-bit-flip Metropolis on the SAME energy, same evaluation budget."""
    E, n = L["E"], L["n"]; rng = np.random.default_rng(seed + 104729)
    T0 = T0 or max(1.0, float(np.ptp(E)) / 4)
    x = int(rng.integers(0, 1 << n)); e = E[x]; best = x; visited = np.empty(evaluations, dtype=np.int64)
    for k in range(evaluations):
        T = T0 * (T1 / T0) ** (k / max(1, evaluations - 1))
        y = x ^ (1 << int(rng.integers(0, n)))
        if E[y] <= e or rng.random() < math.exp(-(E[y] - e) / T):
            x, e = y, E[y]
        visited[k] = x
        if e < E[best]:
            best = x
    return dict(best=best, visited=visited)


# ---------------------------------------------------------------- gate counts
def _walsh_terms(monomials):
    """Convert sum c*prod(x_S) into Z-parity terms; return {frozenset: coeff}."""
    out = {}
    for mono, c in monomials.items():
        k = len(mono)
        if k == 0:
            continue
        # prod x_i = prod (1 - Z_i)/2 = 2^-k * sum_{T subset S} (-1)^{|T|} Z_T
        for r in range(1, k + 1):
            from itertools import combinations
            for T in combinations(mono, r):
                key = frozenset(T); out[key] = out.get(key, 0.0) + c * (-1) ** r / 2 ** k
    return {k: v for k, v in out.items() if abs(v) > 1e-12}


def _gates_predicate_or_qubo(problem: Problem, p=1):
    """CX count per QAOA circuit before routing (all-to-all connectivity).

    Diagonal parts are synthesised as Z-parity rotations: a weight-w parity costs
    2(w-1) CX with a CX ladder. Reversible arithmetic rows cost 6 CX per Toffoli
    and 1 per CX, computed and uncomputed. Transpiler optimisations can lower
    these numbers; routing on real hardware raises them.
    """
    if problem.predicate is not None:
        pm = problem.predicate
        Z = _walsh_terms({k: v for k, v in pm.merged.items() if k})
        direct = sum(2 * (len(k) - 1) for k in Z)
        arith = 0
        for row, keys, oracle in pm.rows:
            if len(keys) > pm.direct_cutoff:
                for name, _ in oracle.forward_gates():
                    arith += 6 if name == "ccx" else 1 if name == "cx" else 0
        cx = p * (direct + 2 * arith)
        return dict(qubits=pm.total, decision_qubits=pm.n, cx=cx, direct_cx=p * direct, arithmetic_cx=p * 2 * arith,
                    max_parity_weight=max((len(k) for k in Z), default=0))
    q = problem.qubo
    return dict(qubits=len(q.names), decision_qubits=q.physical_bits, cx=p * 2 * len(q.quadratic),
                direct_cx=p * 2 * len(q.quadratic), arithmetic_cx=0, max_parity_weight=2)


# ---------------------------------------------------------------- noise
def fidelity(cx, p2, one_qubit=0, p1=0.0):
    return (1 - p2) ** cx * (1 - p1) ** one_qubit


def readout(P, n, r):
    """Independent symmetric readout flips with probability r on every bit."""
    if r <= 0:
        return P
    P = P.astype(float).copy()
    for q in range(n):
        v = P.reshape(-1, 2, 1 << q)
        a = v[:, 0, :].copy(); b = v[:, 1, :].copy()
        v[:, 0, :] = (1 - r) * a + r * b; v[:, 1, :] = r * a + (1 - r) * b
    return P


def noisy(P, n, F, r):
    """Global depolarising model: F*ideal + (1-F)*uniform, then readout error."""
    return readout(F * P + (1 - F) / len(P), n, r)


# ============================================================================
# INDEPENDENT PHYSICAL REPLAY CHECKER   (from revised/physical.py)
# ============================================================================
# Independent rCRP replay. No model-row or production-decoder acceptance calls.
#
# Only the public (stage, below, container) index/recovery map is shared. Relations
# are checked as strict orders, then actual top-only moves establish legality.

def replay_moves(stacks, capacity, moves, require_complete=True):
    bay = [list(s) for s in stacks]
    C = sum(map(len, bay)); target = 1; relocations = 0
    for step, move in enumerate(moves):
        source = move.get('source', move.get('from', 0)) - 1
        c = move['container']; kind = move['type']
        if not 0 <= source < len(bay) or not bay[source] or bay[source][-1] != c:
            raise ValueError(f'step {step}: container is not the source top')
        if kind == 'retrieve':
            if c != target:
                raise ValueError(f'step {step}: retrieval priority is wrong')
            bay[source].pop(); target += 1
        elif kind == 'relocate':
            destination = move.get('destination', move.get('to', 0)) - 1
            if (not 0 <= destination < len(bay) or destination == source
                    or len(bay[destination]) >= capacity or c == target
                    or target not in bay[source]):
                raise ValueError(f'step {step}: restricted relocation is illegal')
            bay[destination].append(bay[source].pop()); relocations += 1
        else:
            raise ValueError(f'step {step}: unknown move type')
    complete = target == C + 1 and not any(bay)
    if require_complete and not complete:
        raise ValueError('route is incomplete')
    return dict(valid=True, complete=complete, relocations=relocations,
                remaining_stacks=bay, next_target=target)


def _stage(model, values, stage):
    """Derive each stack's unique strict total order and check all relations."""
    C, S = model.C, model.S
    stacks = [[] for _ in range(S)]
    for c in range(stage, C + 1):
        owners = [s for s in range(S) if values[model.index[stage, C+s+1, c]]]
        if len(owners) != 1:
            raise ValueError('container has missing or multiple stack membership')
        stacks[owners[0]].append(c)
    for s, members in enumerate(stacks):
        if len(members) > model.T:
            raise ValueError('stage exceeds capacity')
        ranks = {c: sum(values[model.index[stage, d, c]] for d in members) for c in members}
        if sorted(ranks.values()) != list(range(len(members))):
            raise ValueError('below relation is cyclic or not a strict total order')
        stacks[s] = sorted(members, key=ranks.get)
    positions = {c: (s, j) for s, stack in enumerate(stacks) for j, c in enumerate(stack)}
    for c in range(stage, C + 1):
        for d in range(stage, C + 1):
            expected = int(positions[c][0] == positions[d][0] and positions[c][1] < positions[d][1])
            if values[model.index[stage, c, d]] != expected:
                raise ValueError('below relation disagrees with physical stack order')
    return stacks


def reconstruct_assignment(model, values):
    """Physical legality deliberately ignores terminal flags and all slack.

    A missing flag may fail the certificate while its stage configurations still
    yield a legal route. This difference is retained, not coerced into agreement.
    """
    if len(values) != len(model.names) or any(v not in (0, 1) for v in values):
        return dict(valid=False, complete=False, relocations=None, moves=[], reason='invalid assignment width/bits')
    moves = []
    try:
        stages = [_stage(model, values, n) for n in range(1, model.N+1)]
        if tuple(map(tuple, stages[0])) != tuple(map(tuple, model.stacks)):
            raise ValueError('initial stage differs from input bay')
        for target, (stage, following) in enumerate(zip(stages, stages[1:]), 1):
            bay = [s[:] for s in stage]
            source = next(s for s, stack in enumerate(bay) if target in stack)
            destinations = {c: s for s, stack in enumerate(following) for c in stack}
            while bay[source][-1] != target:
                c = bay[source][-1]; destination = destinations[c]
                if destination == source or len(bay[destination]) >= model.T:
                    raise ValueError('invalid blocker destination/capacity')
                bay[destination].append(bay[source].pop())
                moves.append(dict(type='relocate', container=c, source=source+1, destination=destination+1))
            bay[source].pop(); moves.append(dict(type='retrieve', container=target, source=source+1))
            if bay != following:
                raise ValueError('stage transition moves a nonblocker or reverses the wrong order')
        bay = [s[:] for s in stages[-1]]
        while any(bay):
            target = min(c for stack in bay for c in stack)
            source = next(s for s, stack in enumerate(bay) if target in stack)
            c = bay[source][-1]
            if c == target:
                bay[source].pop(); moves.append(dict(type='retrieve', container=c, source=source+1))
            else:
                destination = next(s for s, stack in enumerate(bay) if not stack)
                bay[destination].append(bay[source].pop())
                moves.append(dict(type='relocate', container=c, source=source+1, destination=destination+1))
        checked = replay_moves(model.stacks, model.T, moves)
        return dict(valid=True, complete=True, relocations=checked['relocations'], moves=moves, reason=None)
    except (ValueError, StopIteration, IndexError, KeyError) as exc:
        return dict(valid=False, complete=False, relocations=None, moves=[], reason=str(exc) or type(exc).__name__)


def encode_stages(model, stages):
    """Independent geometric encoding with tight terminal flags; no row calls."""
    values = [0] * len(model.names)
    for key, i in model.index.items():
        if key[0] == 'b':
            d = key[1]; stack = next(s for s in stages[model.N] if d in s)
            values[i] = int(any(c < d for c in stack[:stack.index(d)]))
        else:
            n, c, d = key
            stack_index = next(s for s, stack in enumerate(stages[n]) if d in stack)
            stack = stages[n][stack_index]
            values[i] = (int(stack_index == c-model.C-1) if c > model.C
                         else int(c in stack[:stack.index(d)]))
    return values


def legal_prefixes(model, max_prefixes=100000):
    """Independently enumerate all legal transitions before stage N (tiny tests)."""
    yielded = 0
    def stages_from(bay, target, stages, moves):
        nonlocal yielded
        if target == model.N:
            yielded += 1
            if yielded > max_prefixes:
                raise MemoryError('declared prefix enumeration limit exceeded')
            yield stages, moves
            return
        source = next(s for s, stack in enumerate(bay) if target in stack)
        if bay[source][-1] == target:
            nxt = [s[:] for s in bay]; nxt[source].pop()
            yield from stages_from(nxt, target+1, {**stages, target+1:nxt},
                                   moves+[dict(type='retrieve', container=target, source=source+1)])
        else:
            c = bay[source][-1]
            for destination in range(model.S):
                if destination == source or len(bay[destination]) >= model.T:
                    continue
                nxt = [s[:] for s in bay]; nxt[destination].append(nxt[source].pop())
                yield from stages_from(nxt, target, stages,
                    moves+[dict(type='relocate', container=c, source=source+1, destination=destination+1)])
    start = [list(s) for s in model.stacks]
    yield from stages_from(start, 1, {1:start}, [])


# ============================================================================
# GATE-LEVEL PAULI-FAULT NOISE   (from noise_gate_level.py)
# ============================================================================
# Gate-level noise check of the global depolarising model used in noise_study.py.
#
# The real Pauli-synthesis QAOA circuit (H, CX ladders, RZ, RX) is simulated gate
# by gate. After every CX a random non-identity two-qubit Pauli is applied with
# probability p2 (two-qubit depolarising); after every one-qubit gate a random
# X/Y/Z with probability p2/10; then 1% symmetric readout error. The noisy output
# distribution is the average over Monte-Carlo error trajectories (each trajectory
# contributes its exact statevector probabilities). Still before routing.
#
# python noise_gate_level.py  ->  results/noise_gate_level.csv

P2 = [1e-3, 3e-3, 1e-2, 3e-2, 1e-1]
TRAJ = 400
INSTANCES = ['random-S3T4C6-21', 'data3-3-8', 'data3-3-30']


def gate_list(pm, theta, p, scale):
    # F09: this simulator implements direct Pauli ladders, not arithmetic rows.
    arithmetic = sum(len(keys) > pm.direct_cutoff for _, keys, _ in pm.rows)
    if arithmetic:
        raise ValueError(f'Unsupported noise circuit: {arithmetic} arithmetic rows require clean scratch.')
    if p < 1 or len(theta) != 2 * p or not np.all(np.isfinite(theta)) or not np.isfinite(scale) or scale <= 0:
        raise ValueError('Invalid noise depth, angles or phase scale.')
    g = [('h', q) for q in range(pm.n)]
    for layer in range(p):
        for qubits, a in pm.pauli_terms:
            q = list(qubits)
            g += [('cx', q[i], q[i + 1]) for i in range(len(q) - 1)]
            g.append(('rz', 2 * theta[layer] * a / scale, q[-1]))
            g += [('cx', q[i], q[i + 1]) for i in reversed(range(len(q) - 1))]
        g += [('rx', 2 * theta[p + layer], q) for q in range(pm.n)]
    return g


def validate_gates(n, gates):
    """Validate the entire declared sequence before allocating statevectors."""
    for gt in gates:
        if not isinstance(gt, (tuple, list)) or not gt:
            raise ValueError('Malformed noise gate.')
        k = gt[0]
        if k == 'h' and len(gt) == 2:
            qs = gt[1:]
        elif k in ('rx', 'rz') and len(gt) == 3 and np.isfinite(gt[1]):
            qs = gt[2:]
        elif k == 'cx' and len(gt) == 3 and gt[1] != gt[2]:
            qs = gt[1:]
        else:
            raise ValueError(f'Unsupported or malformed noise gate: {gt!r}')
        if any(not isinstance(q, (int, np.integer)) or not 0 <= q < n for q in qs):
            raise ValueError(f'Invalid qubit in noise gate: {gt!r}')


def run_gate_level(pm, gates, p2, rng):
    validate_gates(pm.n, gates)
    if not np.isfinite(p2) or not 0 <= p2 <= 1:
        raise ValueError('Pauli fault probability must be in [0,1].')
    n = pm.n; idx = np.arange(1 << n); bit = lambda q: (idx >> q) & 1
    psi = np.zeros(1 << n, complex); psi[0] = 1
    def pauli(k, q):
        nonlocal psi
        if k in (1, 2):
            psi = psi[idx ^ (1 << q)] * (np.where(bit(q) == 1, -1j, 1j) if k == 2 else 1)
        if k == 3:
            psi = psi * np.where(bit(q) == 1, -1, 1)
    for gt in gates:
        k = gt[0]
        if k == 'h':
            q = gt[1]; v = psi.reshape(-1, 2, 1 << q); a = v[:, 0, :].copy(); b = v[:, 1, :].copy()
            v[:, 0, :] = (a + b) / math.sqrt(2); v[:, 1, :] = (a - b) / math.sqrt(2); qs = [q]
        elif k == 'rx':
            t, q = gt[1], gt[2]; c, s = math.cos(t / 2), -1j * math.sin(t / 2)
            v = psi.reshape(-1, 2, 1 << q); a = v[:, 0, :].copy(); b = v[:, 1, :].copy()
            v[:, 0, :] = c * a + s * b; v[:, 1, :] = s * a + c * b; qs = [q]
        elif k == 'rz':
            t, q = gt[1], gt[2]; psi = psi * np.where(bit(q) == 1, np.exp(1j * t / 2), np.exp(-1j * t / 2)); qs = [q]
        elif k == 'cx':
            a_, b_ = gt[1], gt[2]; psi = psi[np.where(bit(a_) == 1, idx ^ (1 << b_), idx)]; qs = [a_, b_]
        if len(qs) == 2:
            if rng.random() < p2:
                e = int(rng.integers(1, 16)); pauli(e & 3, qs[0]); pauli(e >> 2, qs[1])
        elif rng.random() < p2 / 10:
            pauli(int(rng.integers(1, 4)), qs[0])
    return np.abs(psi) ** 2


# ============================================================================
# BATCHED GATE-LEVEL NOISE   (from noise_fast.py)
# ============================================================================
# Batched version of noise_gate_level.run: the same gate-level Pauli error model,
# applied to H error histories at once (one statevector column per history).
#
# Error model (identical to noise_gate_level.py): after every CX, with probability p2 a random
# non-identity two-qubit Pauli; after every one-qubit gate, with probability p2/10 a random X/Y/Z.
# Only the order in which random numbers are drawn differs, so results agree statistically,
# not bit for bit. Gates are applied in place in single precision (complex64) for speed;
# with p2 = 0 it equals exact QAOA to about 1e-7 (see __main__).

def run_batch(n, gates, p2, rng, H, dtype=np.complex64, *, diagnostics=None, max_bytes=536870912):
    validate_gates(n, gates)
    if not isinstance(H, int) or H <= 0 or not 0 <= p2 <= 1 or not np.isfinite(p2):
        raise ValueError('Positive history count and valid Pauli fault probability required.')
    if np.dtype(dtype) not in (np.dtype('complex64'), np.dtype('complex128')):
        raise ValueError('Noise dtype must be complex64 or complex128.')
    # Conservative live-array estimate, including gate copies and real probabilities.
    needed = (1 << n) * H * np.dtype(dtype).itemsize * 5
    if needed > max_bytes:
        raise MemoryError(f'Noise batch estimated {needed} bytes exceeds {max_bytes}; reduce history chunk size.')
    N = 1 << n
    psi = np.zeros((N, H), dtype); psi[0, :] = 1
    def view1(q):
        return psi.reshape(-1, 2, 1 << q, H)
    def pauli(k, q, c):
        v = view1(q)
        if k == 1:
            t = v[:, 0, :, c].copy(); v[:, 0, :, c] = v[:, 1, :, c]; v[:, 1, :, c] = t
        elif k == 2:   # same convention as noise_gate_level: new[x] = old[x^m] * (-1j if bit else 1j)
            t = v[:, 0, :, c].copy(); v[:, 0, :, c] = 1j * v[:, 1, :, c]; v[:, 1, :, c] = -1j * t
        elif k == 3:
            v[:, 1, :, c] *= -1
    for gt in gates:
        k = gt[0]
        if k == 'h':
            q = gt[1]; v = view1(q); a = v[:, 0].copy()
            b = v[:, 1].copy(); v[:, 0] = (a + b) / math.sqrt(2); v[:, 1] = (a - b) / math.sqrt(2); qs = [q]
        elif k == 'rx':
            t, q = gt[1], gt[2]; c, s = math.cos(t / 2), -1j * math.sin(t / 2)
            v = view1(q); a = v[:, 0].copy(); b = v[:, 1].copy()
            v[:, 0] = c * a + s * b; v[:, 1] = s * a + c * b; qs = [q]
        elif k == 'rz':
            t, q = gt[1], gt[2]; v = view1(q); v[:, 0] *= np.exp(-1j * t / 2); v[:, 1] *= np.exp(1j * t / 2); qs = [q]
        elif k == 'cx':
            a_, b_ = gt[1], gt[2]; hi, lo = max(a_, b_), min(a_, b_)
            v = psi.reshape(-1, 2, 1 << (hi - lo - 1), 2, 1 << lo, H)
            if a_ == hi:
                x, y = v[:, 1, :, 0], v[:, 1, :, 1]
            else:
                x, y = v[:, 0, :, 1], v[:, 1, :, 1]
            t = x.copy(); x[...] = y; y[...] = t; qs = [a_, b_]
        if len(qs) == 2:
            for c in np.flatnonzero(rng.random(H) < p2):
                e = int(rng.integers(1, 16)); pauli(e & 3, qs[0], c); pauli(e >> 2, qs[1], c)
        else:
            for c in np.flatnonzero(rng.random(H) < p2 / 10):
                pauli(int(rng.integers(1, 4)), qs[0], c)
    probabilities = (np.abs(psi) ** 2).astype(np.float64)
    history_norms = probabilities.sum(axis=0)
    P = probabilities.mean(axis=1)
    norm = float(P.sum()); tolerance = 5e-4 if np.dtype(dtype) == np.dtype('complex64') else 1e-10
    maximum_history_norm_error = float(np.max(np.abs(history_norms - 1)))
    if not np.isfinite(norm) or maximum_history_norm_error > tolerance or abs(norm - 1) > tolerance or np.any(P < 0):
        raise ArithmeticError(f'Noise probability invariant failed before renormalization: norm={norm}')
    if diagnostics is not None:
        diagnostics.update(pre_normalization_sum=norm, norm_error=abs(norm - 1), norm_tolerance=tolerance,
                           maximum_history_norm_error=maximum_history_norm_error,
                           dtype=np.dtype(dtype).name, histories=H, estimated_peak_bytes=needed)
    return P / P.sum()


# ============================================================================
# MOVE-ENCODING RESOURCE MODEL   (from move_model.py)
# ============================================================================
# Bounded evaluation-only move encoding; cheap register counts never enumerate.
#
# Each of K verified greedy-witness relocation slots contains ceil(log2 S) bits.
# The current Walsh compiler explicitly enumerates 2**n energies. It is not a
# production large-instance QAOA compiler, and its uncomputed gates stay unknown.

DEFAULT_MAX_STATES = 1 << 20


class EnumerationLimitError(ValueError):
    """The requested truth table exceeds an explicitly declared evaluation cap."""


def count_only(stacks, T):
    stacks = tuple(tuple(s) for s in stacks)
    S = len(stacks)
    C = sum(map(len, stacks))
    if S < 2 or not isinstance(T, int) or T < 1:
        raise ValueError('Move model requires S >= 2 and positive integer capacity.')
    if any(len(s) > T for s in stacks) or sorted(x for s in stacks for x in s) != list(range(1, C + 1)):
        raise ValueError('Expected unique priorities 1..C and stacks within capacity.')
    witness = feasible_upper_bound(stacks, T)
    # Check witness independently of the heuristic's implementation.
    bay = [list(s) for s in stacks]
    target = 1
    relocations = 0
    for move in witness['moves']:
        src = move['from'] - 1
        if not bay[src] or bay[src][-1] != move['container']:
            raise ValueError('Greedy witness fails top-only replay.')
        if move['type'] == 'retrieve':
            if move['container'] != target:
                raise ValueError('Greedy witness fails retrieval order.')
            bay[src].pop(); target += 1
        elif move['type'] == 'relocate':
            dst = move['to'] - 1
            if target not in bay[src] or move['container'] == target or src == dst or len(bay[dst]) >= T:
                raise ValueError('Greedy witness fails restricted-source/capacity replay.')
            bay[dst].append(bay[src].pop()); relocations += 1
        else:
            raise ValueError('Unknown witness operation.')
    if any(bay) or relocations != witness['upper_bound']:
        raise ValueError('Greedy witness is incomplete or has inconsistent cost.')
    b = (S - 1).bit_length()
    n = relocations * b
    return dict(schema='move-count/2', containers=C, stacks=S, capacity=T,
                K=relocations, bits_per_destination=b, decision_bits=n,
                measured_bits=n, compiler_workspace_qubits=None,
                compiler_workspace_reason='No scalable reversible compiler implemented.',
                phase_cx=None, phase_cx_status='not_computed',
                compilation='evaluation-only explicit 2**n energy table then Walsh transform',
                compilation_state_count=1 << n, count_only=True,
                witness_verified=True, witness_moves=witness['moves'])


def energy_table(stacks, T, *, max_states=DEFAULT_MAX_STATES):
    info = count_only(stacks, T)
    if not isinstance(max_states, int) or isinstance(max_states, bool) or max_states < 1:
        raise ValueError('max_states must be a positive integer.')
    n, K = info['decision_bits'], info['K']
    if (1 << n) > max_states:
        raise EnumerationLimitError(f'not_computed: {n} decision bits require {1 << n} states; max_states={max_states}. No truth-table allocation performed.')
    S, b = len(stacks), info['bits_per_destination']
    W = K + 1
    E = np.zeros(1 << n)
    for m in range(1 << n):
        bay = [list(s) for s in stacks]; target = 1; used = 0; bad = False
        def drain():
            nonlocal target
            moved = True
            while moved:
                moved = False
                for s in bay:
                    if s and s[-1] == target:
                        s.pop(); target += 1; moved = True
        drain()
        for k in range(K):
            code = (m >> (k * b)) & ((1 << b) - 1)
            if not any(bay):
                if code: bad = True
                continue
            src = next(i for i, s in enumerate(bay) if target in s)
            if code >= S or code == src or len(bay[code]) >= T:
                bad = True; break
            bay[code].append(bay[src].pop()); used += 1; drain()
        if any(bay): bad = True
        E[m] = used + W * bad
    return E, n, K


def pauli_terms(E, n):
    """Exact Walsh expansion, excluding the constant mean(E), for bounded tables."""
    if not isinstance(n, int) or n < 0 or len(E) != 1 << n:
        raise ValueError('Energy length must equal 2**n.')
    f = np.asarray(E, dtype=float).copy(); h = 1
    if not np.all(np.isfinite(f)):
        raise ValueError('Finite energies required.')
    while h < len(f):
        for i in range(0, len(f), 2 * h):
            a = f[i:i+h].copy(); c = f[i+h:i+2*h].copy()
            f[i:i+h] = a+c; f[i+h:i+2*h] = a-c
        h *= 2
    f /= len(f)
    return {m: float(v) for m, v in enumerate(f) if m and abs(v) > 1e-9}


# ============================================================================
# PUBLISHED REFERENCES AND QUALITY METRICS   (from benchmark_support.py)
# ============================================================================
# Bundled references and display-only live time estimates; never solve or guide QAOA.

def reference_text(item):
    r=item.get('reference')
    if not r:return 'No answer row in the supplied PDF.'
    if r['proven_optimal']:return f"Published optimum: {r['best_known']} relocations (lower bound agrees). PDF page {r['pdf_page']}."
    return f"Published best-known: {r['best_known']}; lower bound: {r['lower_bound']:g}. Not proven optimal. PDF page {r['pdf_page']}."
def compare(item,bay,height,result):
    if item is None or item['stacks_bottom_to_top']!=[list(s) for s in bay] or item['capacity']!=height:return None
    ref=item.get('reference');value=result.get('relocations')
    if result.get('status','completed')!='completed':value=None
    record=dict(instance_id=item['id'],reference=ref,instance_sha256=item['sha256'],used_for_optimization=False)
    if ref and value is not None:
        record['difference_from_published_best']=value-ref['best_known']
        record['gap_to_proven_optimum']=value-ref['best_known'] if ref['proven_optimal'] else None
        record['below_published_lower_bound']=value+1e-9<ref['lower_bound']
    record['accuracy']=accuracy(ref,value)
    record['optimality']=optimality(ref,value)
    return record


def optimality(reference,relocations):
    """Primary quality metric: absolute and relative gap to the published value.

    Defined for every case, including 0 relocations, and never above 100% match.
    'matched' means equal to a PROVEN optimum, or equal to a best-known value.
    """
    if not reference or relocations is None:return dict(gap=None,relative_gap=None,matched=None,
        reason='No matching published answer or no completed plan.')
    best=reference['best_known'];gap=relocations-best
    return dict(gap=gap,relative_gap=gap/max(1,best),matched=gap==0,
                reference_type='proven optimum' if reference['proven_optimal'] else 'best-known (not proven optimal)',
                below_reference=gap<0,
                note='gap = plan relocations - published relocations; relative_gap divides by max(1, published).')

def remaining_estimate(event):
    """Heuristic range based on live seconds/move and remaining blocking count.
    Never uses a reference answer. None means not enough timing observations.
    """
    moves=event.get('relocations',0);elapsed=event.get('elapsed_seconds',0)
    if event.get('phase')=='done':return (0.,0.) if event.get('status')=='completed' else None
    if event.get('full_route'):
        remaining=event.get('estimated_remaining_seconds')
        if remaining is None:return None
        completed=event.get('planning_completed',0);total=event.get('planning_total',0)
        future=event.get('attempts',1)-event.get('attempt',1)
        projected=elapsed/max(1,completed)*total
        return .5*(remaining+future*projected),2*(remaining+future*projected)
    if moves<1 or elapsed<=0:return None
    remaining=event.get('remaining_blockers',0)
    if remaining<1:return None
    per_move=elapsed/moves
    # Blocking count is a lower bound; factor range is empirical uncertainty, not a confidence interval.
    low=per_move*remaining*.5;high=per_move*remaining*3
    future=event.get('attempts',1)-event.get('attempt',1)
    total=per_move*(moves+remaining)
    return max(0,low+future*.5*total),max(0,high+future*3*total)

def duration(seconds):
    if not math.isfinite(seconds):return 'unknown'
    if seconds<60:return f'{max(1,round(seconds))} s'
    if seconds<3600:return f'{seconds/60:.1f} min'
    return f'{seconds/3600:.1f} h'


def accuracy(reference,qaoa_relocations):
    """User-defined relocation ratio; never clamp or label an unproved reference optimal."""
    base=dict(percent=None,formula='published relocations / QAOA relocations * 100',reference_type=None)
    if not reference:return dict(base,reason='No matching published answer.')
    base['reference_type']='proven optimum' if reference['proven_optimal'] else 'best-known result (not proven optimal)'
    published=reference['best_known'];base.update(published_relocations=published,qaoa_relocations=qaoa_relocations)
    if qaoa_relocations is None:return dict(base,reason='No completed QAOA relocation result.')
    if not math.isfinite(qaoa_relocations) or qaoa_relocations<0:return dict(base,reason='Invalid relocation count.')
    if qaoa_relocations==0:
        if published==0:return dict(base,percent=100.0,reason='Both are zero relocations: reported as an exact match (gap 0).')
        return dict(base,reason='Plan uses fewer relocations than a published value of '+str(published)+'; check the reference.')
    return dict(base,percent=100*published/qaoa_relocations,reason=None)

def accuracy_label(comparison):
    a=comparison.get('accuracy') if comparison else None
    if not a:return 'Accuracy: N/A — no matching published answer for this input.'
    if a['percent'] is None:return 'Accuracy: N/A — '+a['reason']
    o=comparison.get('optimality') or {}
    gap='' if o.get('gap') is None else f" Optimality gap: {o['gap']:+d} relocation(s)."
    text=f"Accuracy: {a['percent']:.2f}% = {a['published_relocations']} / {a['qaoa_relocations']} × 100 ({a['reference_type']}).{gap}"
    if a['percent']>100:text+=' Above 100%; check a proven reference, or a best-known result may have been improved.'
    return text


# ============================================================================
# CORRECTED SIMULATED ANNEALING   (anneal, from revised/protocols.py; digest/rng_stream from revised/artifacts.py)
# ============================================================================
def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)

def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()

def rng_stream(protocol, instance_key, seed, purpose):
    identity = {'derivation': 'sha256-json-seedsequence-v2', 'protocol': protocol,
                'instance_key': instance_key, 'seed': int(seed), 'purpose': purpose}
    h = digest(identity)
    entropy = [int(h[i:i+8], 16) for i in range(0, 64, 8)]
    return np.random.default_rng(np.random.SeedSequence(entropy)), dict(identity, entropy=entropy, bit_generator='PCG64')


SA_PROTOCOL='single-flip-sa-replay-best/2'

def anneal(energy,outcome,*,width,weight,instance_key,seed,budget=40960,T0=None,T1=.05,rngs=None):
    if isinstance(budget,bool) or int(budget)!=budget or budget<1:raise ValueError('budget must be a positive integer')
    if width<0:raise ValueError('negative width')
    T0=max(1.,float(weight)) if T0 is None else float(T0)
    if not math.isfinite(T0) or not math.isfinite(T1) or T0<=0 or T1<=0:raise ValueError('temperatures must be finite and strictly positive')
    derived={p:rng_stream(SA_PROTOCOL,instance_key,seed,p) for p in ('initialization','proposal','metropolis')}
    streams={p:v[0] for p,v in derived.items()} if rngs is None else rngs
    actual=1 if width==0 else budget
    states=np.empty(actual,dtype=np.uint64);energies=np.empty(actual,dtype=np.int64)
    accepts=np.zeros(actual,bool);temps=np.full(actual,np.nan);costs=np.full(actual,-1,dtype=np.int32)
    cache={};oracle_calls=0;hits=0;best=None
    def evaluate(s):
        nonlocal oracle_calls,hits,best
        if s in cache:e,o=cache[s];hits+=1
        else:e,o=int(energy(s)),outcome(s);cache[s]=(e,o);oracle_calls+=1
        c=o['replayed_relocations'] if o['decoder_accepted'] else None
        if c is not None and (best is None or (c,s)<best[0]):best=((c,s),o)
        return e,-1 if c is None else c
    x=0 if width==0 else int(streams['initialization'].integers(0,1<<width))
    e,c=evaluate(x);states[0]=x;energies[0]=e;costs[0]=c;accepts[0]=True
    M=actual-1
    for k in range(M):
        T=T0*(T1/T0)**(k/max(1,M-1));y=x^(1<<int(streams['proposal'].integers(0,width)))
        ey,c=evaluate(y);accepted=ey<=e or streams['metropolis'].random()<math.exp(-(ey-e)/T)
        states[k+1]=y;energies[k+1]=ey;costs[k+1]=c;accepts[k+1]=accepted;temps[k+1]=T
        if accepted:x,e=y,ey
    selected={'state':None,'replayed_relocations':None,'status':'no_accepted_complete_candidate','trace':None} if best is None else dict(state=best[0][1],replayed_relocations=best[0][0],status='accepted_complete',trace=best[1].get('moves'))
    record=dict(protocol=SA_PROTOCOL,budget_requested=budget,candidate_evaluations=actual,initial_candidates=1,proposed_candidates=M,
                energy_oracle_calls=oracle_calls,cache_hits=hits,outcome_calls=oracle_calls,T0=T0,T1=T1,
                schedule='T0*(T1/T0)**(k/max(1,M-1)); k=0..M-1; M=B-1',initial_temperature=None,
                selection='minimum accepted complete replay cost across initial AND ALL proposals; ties smaller state integer',
                rng=({p:v[1] for p,v in derived.items()} if rngs is None else {'source':'injected_test_streams','reproducible_derivation':None}),chain_final_state=x,selected=selected,
                stopping_reason='unique zero-bit candidate' if width==0 else 'candidate evaluation budget exhausted',
                source_of_energy='direct callable; optional table adapter, temperature independent of energy range',
                constant_actual_work=width==0)
    return record,dict(states=states,energies=energies,metropolis_accepted=accepts,temperatures=temps,replay_costs=costs)


# ============================================================================
# FAKE IBM DEVICE HELPERS   (from run_fake_ibm_demo.py)
# ============================================================================
def fake_backend():
    from qiskit_ibm_runtime import fake_provider as fp
    for name in ('FakeFez', 'FakeMarrakesh', 'FakeTorino', 'FakeBrisbane', 'FakeManilaV2'):   # FIX (Sim9) 16: Heron first
        if hasattr(fp, name):
            return getattr(fp, name)()
    raise RuntimeError('No fake backend found in qiskit_ibm_runtime.fake_provider')

def bind(circuit, theta, p):
    values = {f'gamma[{i}]': float(theta[i]) for i in range(p)}
    values.update({f'beta[{i}]': float(theta[p + i]) for i in range(p)})
    return circuit.assign_parameters({par: values[par.name] for par in circuit.parameters})


# ============================================================================
# SHARED ADDITIONS: catalog, bay input, Lemma-1 solver, encoding-agnostic
# energy tables and gate lists (new code written for the merged suite)
# ============================================================================
HARDWARE_DOC = """IBM/Qiskit full-instance QAOA. Compile first; hardware submission is explicit.

No production path enumerates bitstrings, builds an energy table or imports
published solutions. Measurement outcomes alone are decoded and scored."""

METHODS = {'predicate': 'Predicate (fewest qubits)', 'hybrid': 'Hybrid (balanced)',
           'galle': 'QUBO (fewest gates, most qubits)', 'coherent': 'Coherent movement oracle (research)'}
ANGLE_MODES = {'transfer': 'Transferred angles, no training (recommended)',
               'transfer_refine': 'Transferred angles + shot-based refinement',
               'tune': 'Tune angles on this instance (exact expectation, slow)'}
BACKENDS = {'ideal': 'Ideal simulator (exact, no noise)',
            'global': 'Global depolarising + readout noise (fast model)',
            'gate_level': 'Gate-level Pauli faults (Monte Carlo)',
            'fake_ibm': 'Fake IBM chip with real noise (needs qiskit-aer)'}


# ------------------------------------------------------------------ catalog
_CATALOG = None


def _bay_file_text(stacks, capacity):
    """Exact group-4 file text (header S T C; rows 'k c1..ck' bottom->top; final newline).
    Reproduces all 880 original files byte for byte (checked against their sha256)."""
    C = sum(map(len, stacks))
    return '\n'.join([f'{len(stacks)} {capacity} {C}'] + [' '.join(map(str, [len(s)] + list(s))) for s in stacks]) + '\n'


def catalog():
    """Embedded benchmark catalog: list of dicts sorted by containers then family."""
    global _CATALOG
    if _CATALOG is None:
        raw = zlib.decompress(base64.b85decode(''.join(_CATALOG_B85)))
        if hashlib.sha256(raw).hexdigest() != _CATALOG_SHA256:
            raise RuntimeError('Embedded benchmark catalog is corrupted.')
        out = []
        for name, cap, stacks, best, lower, proven in json.loads(raw):
            m = re.match(r'data(\d+)-(\d+)-(\d+)', name)
            ref = None if best is None else dict(best_known=best, lower_bound=lower, proven_optimal=bool(proven))
            out.append(dict(id=name, name=name, capacity=cap, stacks_bottom_to_top=stacks, stacks=len(stacks),
                            containers=sum(map(len, stacks)), reference=ref,
                            family=f'data{m.group(1)}-{m.group(2)}' if m else 'other',
                            sha256=hashlib.sha256(_bay_file_text(stacks, cap).encode()).hexdigest(),
                            sort=(sum(map(len, stacks)),) + ((int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else (99, 99, 99))))
        _CATALOG = sorted(out, key=lambda r: r['sort'])
    return _CATALOG


def catalog_item(name):
    return next((r for r in catalog() if r['id'] == name), None)


def reference_for(name):
    item = catalog_item(name)
    return item['reference'] if item else None


def list_instance_folder(folder):
    """Group-4 style *.txt files in a folder (same rows as the embedded catalog)."""
    rows = []
    for f in Path(folder).glob('*.txt'):
        try:
            S_, T_, C_ = [int(v) for v in f.read_text().split('\n', 1)[0].split()][:3]
        except Exception:
            continue
        m = re.match(r'data(\d+)-(\d+)-(\d+)', f.stem)
        rows.append(dict(id=f.stem, name=f.stem, path=str(f), stacks=S_, capacity=T_, containers=C_, reference=None,
                         family=f'data{m.group(1)}-{m.group(2)}' if m else 'other',
                         sort=(C_,) + ((int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else (99, 99, 99))))
    return sorted(rows, key=lambda r: r['sort'])


def parse_bay_text(text):
    """User-typed bay: one stack per line, bottom -> top; '-' or empty marker for an empty stack."""
    rows = [r for r in text.splitlines() if r.strip()]
    return tuple(() if r.strip() == '-' else tuple(int(x) for x in r.replace(',', ' ').split()) for r in rows)


def random_bay(S, T, C, seed=0):
    rng = random.Random(seed)
    if C > S * T:
        raise ValueError('More containers than slots.')
    st = [[] for _ in range(S)]
    for c in rng.sample(range(1, C + 1), C):
        st[rng.choice([i for i in range(S) if len(st[i]) < T])].append(c)
    return tuple(tuple(s) for s in st)


def blocking_count(stacks):
    """Containers with a smaller (earlier) priority somewhere below them."""
    return sum(1 for s in stacks for j, c in enumerate(s) if s[:j] and min(s[:j]) < c)


def solve_small_bay(stacks, height):
    """FIX 1: exact answer when C <= S (Galle Lemma 1), no model or QAOA needed.

    Every blocker of the current target goes to an empty stack. With at most S
    containers left and the target's stack holding a blocker, an empty stack
    always exists, so the plan uses exactly blocking_count(stacks) relocations,
    which is also a lower bound. The plan is replay-checked independently.
    """
    bay = [list(s) for s in stacks]; moves = []
    while any(bay):
        target = min(c for s in bay for c in s); src = next(i for i, s in enumerate(bay) if target in s)
        if bay[src][-1] == target:
            bay[src].pop(); moves.append(dict(type='retrieve', container=target, source=src + 1)); continue
        empty = [i for i, s in enumerate(bay) if not s]
        if not empty:
            raise ValueError('No empty stack: Lemma 1 needs C <= S.')
        c = bay[src].pop(); bay[empty[0]].append(c)
        moves.append(dict(type='relocate', container=c, source=src + 1, destination=empty[0] + 1))
    relocations = replay_moves(stacks, height, moves)['relocations']
    if relocations != blocking_count(stacks):
        raise AssertionError('Lemma 1 plan does not match the blocking-count lower bound.')
    return dict(relocations=relocations, moves=moves)


# ------------------------------------------------------------------ energies
def _ids(n):
    return np.arange(1 << n, dtype=np.int64)


def _rows_hold(rows, ids, width_mask=None):
    ok = np.ones(len(ids), bool)
    for row in rows:
        s = np.zeros(len(ids), dtype=np.int64)
        for i, c in row.terms.items():
            s += c * ((ids >> i) & 1)
        ok &= (s == row.rhs) if row.sense == 'eq' else (s <= row.rhs)
    return ok


def _poly_energy(poly, ids):
    E = np.zeros(len(ids))
    for mono, c in poly.items():
        if not mono:
            E += c
        else:
            v = np.ones(len(ids), dtype=np.int64)
            for i in mono:
                v &= (ids >> i) & 1
            E += c * v
    return E


def qubo_polynomial(qubo):
    poly = {(): qubo.offset}
    poly.update({(i,): v for i, v in qubo.linear.items()})
    poly.update(dict(qubo.quadratic))
    return poly


def _coherent_arrays(oracle, ids, chunk=1 << 14, cancelled=_never):
    """Vectorised evaluation of the oracle's AND/XOR DAG over many decision strings."""
    nodes = oracle.logic.nodes
    E = np.zeros(len(ids)); valid = np.zeros(len(ids), bool)
    for a in range(0, len(ids), chunk):
        if cancelled():
            raise Cancelled()
        part = ids[a:a + chunk]; vals = [np.zeros(len(part), bool), np.ones(len(part), bool)]; cursor = 0
        get = lambda lit: vals[lit] if lit >= 0 else ~vals[-lit]
        for node in nodes[2:]:
            if node[0] == 'input':
                vals.append(((part >> cursor) & 1).astype(bool)); cursor += 1
            elif node[0] == 'and':
                vals.append(get(node[1]) & get(node[2]))
            else:
                vals.append(get(node[1]) ^ get(node[2]))
        E[a:a + chunk] = sum(w * get(lit).astype(np.int64) for lit, w in oracle.phases.items())
        valid[a:a + chunk] = get(oracle.valid)
    return E, valid


def landscape(problem):
    """FIX 8: exact energy table for EVERY encoding (evaluation only).

    Returns dict(E, legal, optimum, n). legal = the physical part of the string
    satisfies every constraint (decision/physical bits; slack ignored).
    """
    if problem.predicate is not None or problem.qubo is not None:
        return _landscape_predicate_or_qubo(problem)
    ids = _ids(problem.n)
    if problem.hybrid is not None:
        hm = problem.hybrid; E = _poly_energy(hm.poly, ids)
        legal = _rows_hold([r for r, _, _ in hm.pm.rows], ids)
        return dict(E=E, legal=legal, optimum=float(E.min()), n=hm.n)
    E, valid = _coherent_arrays(problem.oracle, ids)
    return dict(E=E, legal=valid, optimum=float(E.min()), n=problem.n)


def logical_two_qubit_gates(problem, p=1):
    """FIX 8: CX count per QAOA circuit before routing, for every encoding."""
    if problem.predicate is not None or problem.qubo is not None:
        return _gates_predicate_or_qubo(problem, p)
    if problem.hybrid is not None:
        r = problem.hybrid.resources(p)
        return dict(qubits=r['total_logical_qubits'], decision_qubits=r['decision_qubits'], cx=r['logical_cx'],
                    direct_cx=r['logical_cx'], arithmetic_cx=0,
                    max_parity_weight=max((len(t) for t, _ in problem.hybrid.pauli_terms), default=0))
    r = problem.oracle.resources(p)
    return dict(qubits=r['total_logical_qubits'], decision_qubits=r['decision_qubits'],
                cx=r['ccx_cx_expansion_estimate'], direct_cx=0, arithmetic_cx=r['ccx_cx_expansion_estimate'],
                max_parity_weight=None)


def evaluation_table(problem, cancelled=_never, log=None):
    """Exact per-state outcomes for small encodings (evaluation only).

    Same vocabulary as revised/scoring.py:
      accepted       the string decodes and replays as a complete legal plan
      cost           its replayed relocation count (-1 if not accepted)
      ground         the string has the minimum energy
    The best plan cost is the minimum over accepted strings, found by
    enumeration; no known optimum is used. Physical patterns are decoded once.
    """
    n = problem.n; ids = _ids(n)
    if problem.oracle is not None:
        E, valid = _coherent_arrays(problem.oracle, ids, cancelled=cancelled)
        cost = np.where(valid, E, -1).astype(np.int64)
        return dict(E=E, n=n, accepted=valid, cost=cost, ground=E == E.min(), optimum_energy=float(E.min()),
                    best_cost=int(cost[valid].min()) if valid.any() else None, physical_width=n)
    L = landscape(problem); E = L['E']
    if problem.predicate is not None:
        rows, width = problem.predicate.presolve.reduced_rows, problem.n
    elif problem.hybrid is not None:
        rows, width = problem.hybrid.presolve.reduced_rows, problem.hybrid.n_decision
    else:
        rows, width = problem.qubo.presolve.reduced_rows, problem.qubo.physical_bits
    presolve = (problem.predicate or problem.hybrid or problem.qubo).presolve
    mask = (1 << width) - 1
    certificate = _rows_hold(rows, ids & mask)
    cost = np.full(1 << n, -1, dtype=np.int64); cache = {}
    feasible = np.flatnonzero(certificate)
    for k, s in enumerate(feasible):
        if k % 2048 == 0 and cancelled():
            raise Cancelled()
        base = int(s) & mask
        if base not in cache:
            x = presolve.recover([(base >> i) & 1 for i in range(width)])
            d = decode_galle(problem.model, x)
            cache[base] = d['relocations'] if d.get('valid') else -1
        cost[s] = cache[base]
    accepted = cost >= 0
    if log:
        log(f'Energy table: {1 << n:,} strings, {int(accepted.sum()):,} decode to legal plans '
            f'({len(cache):,} distinct physical patterns replayed).')
    return dict(E=E, n=n, accepted=accepted, cost=cost, ground=E == E.min(), optimum_energy=float(E.min()),
                best_cost=int(cost[accepted].min()) if accepted.any() else None, physical_width=width)


def exact_probabilities(P, table):
    """Probability of each outcome event under an output distribution P."""
    acc = table['accepted']; best = table['best_cost']
    opt = acc & (table['cost'] == best) if best is not None else np.zeros_like(acc)
    return dict(P_accepted=float(P[acc].sum()), P_replay_optimal=float(P[opt].sum()),
                P_energy_ground=float(P[table['ground']].sum()))


def score_states(states, table, cap_histogram=True):
    """Outcome summary of a sample of state integers, using the exact cost table."""
    states = np.asarray(states, dtype=np.int64); total = len(states)
    if not total:
        return dict(samples=0, legal_fraction=0.0, distinct_legal_plans=0, best=None, cost_histogram={})
    acc = table['accepted'][states]; costs = table['cost'][states]
    best = None
    if acc.any():
        good = states[acc]; c = costs[acc]; v = int(c.min()); s = int(good[c == v].min())
        best = dict(state=s, relocations=v, count=int(np.sum(states == s)))
    hist = Counter(costs[acc].tolist())
    return dict(samples=total, legal_fraction=float(acc.mean()), distinct_legal_plans=int(len(np.unique(states[acc]))),
                best=best, cost_histogram={int(k): v / total for k, v in sorted(hist.items())},
                saw_energy_ground=bool(table['ground'][states].any()))


def shot_refinement(prob_fn, E, n, scale, p, shots, jobs, seed, initial, rhobeg=.05, cancelled=_never):
    """paper_sim.shot_protocol with a pluggable output distribution and Stop support.

    With prob_fn = ideal QAOA it consumes random numbers exactly like the original
    (checked in selftest). COBYLA on sampled mean energy, jobs-1 training batches,
    then one independent final batch at the best training angles.
    """
    from scipy.optimize import minimize
    N = len(E); rng = np.random.default_rng(seed); hist = []

    class Stop(Exception):
        pass

    def f(t):
        if cancelled():
            raise Cancelled()
        if len(hist) >= jobs - 1:
            raise Stop
        P = prob_fn(t); s = rng.choice(N, shots, p=P)
        hist.append((E[s].mean(), np.array(t), s)); return E[s].mean() / scale
    x0 = np.asarray(initial)
    try:
        minimize(f, x0, method='COBYLA', options=dict(maxiter=jobs - 1, rhobeg=rhobeg))
    except Stop:
        pass
    if not hist:
        raise RuntimeError('Refinement needs at least 2 jobs.')
    theta = min(hist, key=lambda h: h[0])[1]
    P = prob_fn(theta); final = rng.choice(N, shots, p=P)
    every = np.concatenate([h[2] for h in hist] + [final])
    return dict(theta=theta, final=final, every=every, jobs=len(hist) + 1)


def tune_angles(L, scale, pmax=3, restarts=4, seed=0, cancelled=_never, log=None):
    """paper_sim.tune with Stop support and progress (FIX 6); same algorithm and starts."""
    from scipy.optimize import minimize
    rng = np.random.default_rng(seed); E = L['E']; n = L['n']; out = {}; prev = None
    for p in range(1, pmax + 1):
        starts = [ramp(p)] + [np.r_[rng.uniform(0, math.pi, p), rng.uniform(0, math.pi / 2, p)] for _ in range(restarts)]
        if prev is not None:
            g, b = prev[:p - 1], prev[p - 1:]
            x = np.linspace(0, 1, p); xp = np.linspace(0, 1, p - 1) if p > 2 else np.array([0., 1.])
            starts.insert(0, np.r_[np.interp(x, xp, g if p > 2 else np.r_[g, g]), np.interp(x, xp, b if p > 2 else np.r_[b, b])])
        best = None

        def objective(t):
            if cancelled():
                raise Cancelled()
            return qaoa_probs(E, t, p, scale, n) @ E
        for k, x0 in enumerate(starts, 1):
            if log:
                log(f'  tuning p={p}: start {k}/{len(starts)}')
            r = minimize(objective, x0, method='Nelder-Mead', options=dict(maxiter=300 * p, xatol=1e-4, fatol=1e-7))
            if best is None or r.fun < best.fun:
                best = r
        prev = best.x
        out[p] = dict(theta=best.x, P=qaoa_probs(E, best.x, p, scale, n), mean_E=float(best.fun))
    return out


# ------------------------------------------------------------------ gate-level noise for any diagonal encoding
def pauli_hamiltonian(problem):
    """(constant, [(qubits, coeff)]) of the diagonal cost for predicate/hybrid/QUBO."""
    if problem.predicate is not None:
        return problem.predicate.pauli_constant, problem.predicate.pauli_terms
    if problem.hybrid is not None:
        return problem.hybrid.pauli_constant, problem.hybrid.pauli_terms
    if problem.qubo is not None:
        return pauli_z_terms(qubo_polynomial(problem.qubo))
    raise ValueError('The coherent oracle has no direct Pauli form (it needs clean scratch qubits).')


def gate_list_any(problem, theta, p):
    """noise_gate_level.gate_list generalised from predicate to hybrid and QUBO.

    Same gate order: H on all, then per layer Pauli-Z ladders (CX ... RZ ... CX)
    and RX mixers. Predicate models with arithmetic rows are rejected (F09).
    """
    if problem.predicate is not None:
        return gate_list(problem.predicate, theta, p, problem.scale)
    _, terms = pauli_hamiltonian(problem); n = problem.n; scale = problem.scale
    if p < 1 or len(theta) != 2 * p or not np.all(np.isfinite(theta)):
        raise ValueError('Invalid noise depth or angles.')
    g = [('h', q) for q in range(n)]
    for layer in range(p):
        for qubits, a in terms:
            q = list(qubits)
            g += [('cx', q[i], q[i + 1]) for i in range(len(q) - 1)]
            g.append(('rz', 2 * theta[layer] * a / scale, q[-1]))
            g += [('cx', q[i], q[i + 1]) for i in reversed(range(len(q) - 1))]
        g += [('rx', 2 * theta[p + layer], q) for q in range(n)]
    return g


def gate_level_distribution(problem, theta, p, p2, readout_error, histories, seed, cancelled=_never, log=None,
                            max_bytes=512 * 2 ** 20):
    """Average output distribution over Monte-Carlo Pauli-fault histories (noise_fast.run_batch)."""
    n = problem.n; gates = gate_list_any(problem, theta, p)
    chunk = max(1, min(histories, max_bytes // ((1 << n) * 8 * 5)))
    rng = np.random.default_rng(seed + 2026100909); P = np.zeros(1 << n); done = 0
    while done < histories:
        if cancelled():
            raise Cancelled()
        h = min(chunk, histories - done)
        P += run_batch(n, gates, p2, rng, h) * h; done += h
        if log:
            log(f'  noise histories {done}/{histories}')
    P /= histories
    return readout(P, n, readout_error), sum(g[0] == 'cx' for g in gates)


# ------------------------------------------------------------------ economical IBM runs (new)
def qpu_seconds_estimate(jobs, shots_per_job):
    """IBM's quick usage formula: about 2 s overhead per job plus 0.35 ms per shot
    (no error mitigation, default rep_delay). An estimate, not a quote."""
    return jobs * 2.0 + 0.00035 * jobs * shots_per_job


def run_single_job(problem, circuit, sampler, p, shots, seed, out, event=print, qpu=False, max_qpu_seconds=None,
                   initial_angles=None, control=True, backend_name=None):
    """Fixed transferred angles, ALL shots in ONE job (no optimiser).

    Same scoring and result.json fields as optimize_samples, but one job instead
    of many: on IBM hardware this saves about 2 s of QPU overhead per avoided job.
    """
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    theta = np.asarray(initial_angles, dtype=float) if initial_angles is not None else concentrated_angles(p, getattr(problem, 'method', 'predicate'))
    if theta.shape != (2 * p,):
        raise ValueError(f'initial angles need {2 * p} numbers: {p} gammas then {p} betas')
    params = {par.name: par for par in circuit.parameters}
    bindings = {params[f'gamma[{i}]']: float(theta[i]) for i in range(p) if f'gamma[{i}]' in params}
    bindings.update({params[f'beta[{i}]']: float(theta[p + i]) for i in range(p) if f'beta[{i}]' in params})
    bound = circuit.assign_parameters(bindings)
    if qpu:
        if max_qpu_seconds is None or max_qpu_seconds < 1:
            raise ValueError('Specify a positive total QPU-seconds cap.')
        sampler.options.max_execution_time = int(max_qpu_seconds)
    est = qpu_seconds_estimate(1, shots)
    event(f'Single job: {shots} shots at fixed transferred angles; estimated QPU usage about {est:.0f} s'
          + (f' (cap {max_qpu_seconds} s)' if qpu else ''))
    started = time.perf_counter(); job = sampler.run([bound], shots=shots); jobid = job.job_id()
    receipt = dict(job_id=jobid, theta=list(map(float, theta)), shots=shots, hardware=qpu, final_validation=True,
                   backend=backend_name, estimated_qpu_seconds=est)
    (out / 'job_1_receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    event(f'Submitted job {jobid}; waiting for the result (queue time on the free plan can be long)…' if qpu
          else f'Running locally (job {jobid}); no IBM account or QPU time is used…')
    result = job.result(); counts = result[0].data.decision.get_counts(); summary = stats(counts, problem)
    usage = None
    try:
        usage = job.usage()
    except Exception:
        pass
    entry = dict(receipt, counts=counts, summary=summary, wall_seconds=time.perf_counter() - started,
                 metadata=result[0].metadata, reported_usage_seconds=usage)
    (out / 'job_1.json').write_text(json.dumps(entry, indent=2, default=str) + '\n')
    best = summary['best_observed']
    res = dict(status='completed' if best else 'no_feasible_sample', hardware_execution=qpu, method=problem.method,
               shots_per_job=shots, total_shots=shots, jobs=1, best_observed=best,
               relocations=None if not best else best['relocations'], moves=[] if not best else best['moves'],
               final_validation=summary, theta=list(map(float, theta)), qpu_seconds_reserved=max_qpu_seconds if qpu else 0,
               reported_usage_seconds=usage, backend=backend_name,
               limitation='No optimality, novelty or quantum-advantage guarantee. One job at fixed transferred angles.')
    res['budget'] = dict(jobs=1, max_jobs=1, shots_per_job=shots, depth=p, initial_angles=list(map(float, theta)),
                         optimizer='none (fixed transferred angles, single job)',
                         start='transferred concentrated angles' if initial_angles is None else 'user-supplied')
    if control:
        u = uniform_control(problem, shots, seed); ub = None if not u['best_observed'] else u['best_observed']['relocations']
        res['uniform_control'] = dict(shots=shots, feasible_fraction=u['feasible_fraction'], best_relocations=ub, mean_energy=u['mean_energy'])
        res['comparison_to_uniform'] = dict(final_batch_feasible_fraction=summary['feasible_fraction'],
            feasible_amplification=None if not u['feasible_fraction'] else summary['feasible_fraction'] / u['feasible_fraction'],
            qaoa_best_relocations=res['relocations'], uniform_best_relocations=ub,
            qaoa_better_than_uniform=None if res['relocations'] is None or ub is None else res['relocations'] < ub,
            note='Same decoder, same total shots. If QAOA does not beat this control, do not claim the quantum circuit helped.')
    (out / 'result.json').write_text(json.dumps(res, indent=2, default=str) + '\n')
    event(f"Done: best legal plan {res['relocations']} relocations; legal fraction {summary['feasible_fraction']:.2%}"
          + (f"; random guessing {res['uniform_control']['feasible_fraction']:.2%}" if control else ''))
    return res


# ============================================================================
# ENGINE: one run = instance + settings -> results dict   (from rcrp_engine.py)
# ============================================================================
@dataclass
class Config:
    instance: str = ''              # embedded catalog id, or a label for a custom bay
    path: str = ''                  # group-4 style file (overrides instance)
    stacks: list = None             # explicit bay bottom->top (overrides both)
    capacity: int = None
    method: str = 'predicate'
    presolve: str = 'standard'      # FIX (Sim9) 12: 'standard' = the validated release model; 'strong' = exact for the best plan, separate model
    synthesis: str = 'pauli'
    depth: int = 2
    shots: int = 1024
    jobs: int = 40
    angles: str = 'transfer'
    backend: str = 'ideal'
    p2: float = 3e-3                # two-qubit error (noise backends); p1 = p2/10 in gate-level
    readout: float = 0.01           # symmetric readout flip probability
    histories: int = 200            # gate-level Monte-Carlo error histories
    seed: int = 0
    baselines: bool = True
    milp: bool = False
    max_qubits: int = 20
    bfs_max_containers: int = 10


PRESOLVE_LABELS = {'strong': 'strong (probing + one-hot elimination + flag dominance)',
                   'standard': 'standard (as in the published study)'}


def total_ram_bytes():
    """Installed RAM, best effort (Windows, macOS, Linux); 8 GB if unknown."""
    try:
        return os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES')
    except (ValueError, OSError, AttributeError):
        pass
    try:
        import ctypes

        class _MS(ctypes.Structure):
            _fields_ = [('dwLength', ctypes.c_ulong), ('dwMemoryLoad', ctypes.c_ulong), ('ullTotalPhys', ctypes.c_ulonglong),
                        ('ullAvailPhys', ctypes.c_ulonglong), ('ullTotalPageFile', ctypes.c_ulonglong),
                        ('ullAvailPageFile', ctypes.c_ulonglong), ('ullTotalVirtual', ctypes.c_ulonglong),
                        ('ullAvailVirtual', ctypes.c_ulonglong), ('ullAvailExtendedVirtual', ctypes.c_ulonglong)]
        st = _MS(); st.dwLength = ctypes.sizeof(_MS)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st))
        return int(st.ullTotalPhys)
    except Exception:
        return 8 * 1024 ** 3


def simulation_bytes(n):
    """Rough peak memory of one exact run in this suite (statevector plus exact
    outcome tables): about (110 + n) bytes per bitstring."""
    return float(2 ** n) * (110 + n)


def human_bytes(b):
    for unit in ('B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB'):
        if b < 1024 or unit == 'EB':
            return f'{b:.0f} {unit}' if unit == 'B' else f'{b:.1f} {unit}'
        b /= 1024


def size_check(stacks, height, method, presolve, max_qubits):
    """Build the model (no simulation) and say whether this computer can simulate it."""
    C = sum(map(len, stacks))
    if C <= len(stacks):
        return dict(qubits=0, verdict='exact', text='C ≤ S: solved exactly without QAOA (Galle Lemma 1).')
    try:
        pr = Problem(stacks, height, method, presolve=presolve)
    except InfeasibleInstance:
        return dict(qubits=None, verdict='infeasible', text='No legal retrieval sequence exists for this bay.')
    except MemoryError:
        return dict(qubits=None, verdict='too_big', text="Galle's model is too large to build on a laptop.")
    except ValueError as e:
        return dict(qubits=None, verdict='error', text=str(e)[:120])
    n = pr.n; need = simulation_bytes(n); ram = total_ram_bytes()
    if n == 0:
        return dict(qubits=0, verdict='exact', text='Presolve fixes every variable: solved exactly, no QAOA needed.')
    if n > max_qubits or need > 0.6 * ram:
        why = (f'needs about {human_bytes(need)}, this computer has {human_bytes(ram)}' if need > 0.6 * ram
               else f'above your simulation limit of {max_qubits}')
        return dict(qubits=n, verdict='too_big', text=f'{n} qubits: too large to simulate ({why}).')
    tiny = ' The reduced problem is tiny, so QAOA has little to do here.' if n <= 4 else ''
    return dict(qubits=n, verdict='fits', text=f'{n} qubits: fits (about {human_bytes(need)} of memory).' + tiny)


def resolve_bay(cfg):
    """Return (name, stacks, capacity, catalog item or None)."""
    if cfg.stacks is not None:
        if cfg.capacity is None:
            raise ValueError('A custom bay needs a capacity.')
        bay = tuple(tuple(int(v) for v in s) for s in cfg.stacks)
        item = next((r for r in catalog() if r['stacks_bottom_to_top'] == [list(s) for s in bay]
                     and r['capacity'] == cfg.capacity), None)
        return (cfg.instance or (item['id'] if item else 'custom bay')), bay, int(cfg.capacity), item
    if cfg.path:
        bay, height = read_instance(cfg.path, None, None)
        name = Path(cfg.path).stem; item = catalog_item(name)
        if item and (item['stacks_bottom_to_top'] != [list(s) for s in bay] or item['capacity'] != height):
            item = None                                  # same name, different bay: no reference
        return name, bay, height, item
    item = catalog_item(cfg.instance)
    if not item:
        raise ValueError(f'Unknown instance {cfg.instance!r}; use list to see names.')
    return item['id'], tuple(tuple(s) for s in item['stacks_bottom_to_top']), item['capacity'], item


def _norm_moves(moves):
    out = []
    for m in moves:
        src = m.get('source', m.get('from')); dst = m.get('destination', m.get('to'))
        out.append(dict(type=m['type'], container=m['container'], source=src, destination=dst))
    return out


def replay(stacks, moves):
    """Bay states after each move: [(stacks, caption)] starting with the initial bay."""
    bay = [list(s) for s in stacks]; states = [([list(s) for s in bay], 'Initial bay')]
    for i, m in enumerate(moves, 1):
        s = m['source'] - 1
        c = bay[s].pop()
        if m['type'] == 'relocate':
            bay[m['destination'] - 1].append(c)
            cap = f"{i}. Relocate {c}: stack {m['source']} → stack {m['destination']}"
        else:
            cap = f"{i}. Retrieve {c} from stack {m['source']}"
        states.append(([list(x) for x in bay], cap))
    return states


def plan_of_state(problem, state, stacks, height):
    """Decode one sampled state into checked crane moves (None if not a legal plan)."""
    o = problem.outcome([(int(state) >> i) & 1 for i in range(problem.n)])
    if not o.get('valid'):
        return None
    moves = _norm_moves(o['moves'])
    checked = replay_moves(stacks, height, moves)       # independent checker (revised/physical.py)
    if checked['relocations'] != o['relocations']:
        raise AssertionError('Decoder and independent replay disagree.')
    return dict(state=int(state), relocations=o['relocations'], moves=moves)


def encoding_resources(problem, depth):
    g = logical_two_qubit_gates(problem, p=depth)
    return dict(qubits=g['qubits'], decision_qubits=g['decision_qubits'],
                extra_qubits=g['qubits'] - g['decision_qubits'], logical_cx=g['cx'],
                measured_qubits=problem.n)


def run(cfg: Config, log=print, cancelled=_never):
    t0 = time.time()

    def check():
        if cancelled():
            raise Cancelled()
    name, bay, height, item = resolve_bay(cfg)
    validate_instance(bay, height)
    C = sum(map(len, bay)); ref = item['reference'] if item else None
    cfg_d = asdict(cfg); cfg_d['stacks'] = [list(s) for s in bay]; cfg_d['capacity'] = height
    out = dict(instance=name, stacks=[list(s) for s in bay], capacity=height, containers=C,
               config=cfg_d, reference=ref, status='ok', notes=[], version=__version__)
    log(f'Instance {name}: {len(bay)} stacks, capacity {height}, {C} containers')
    if len(bay) * height - C < height - 1:
        out['notes'].append("Galle's sufficient free-space condition S*T-C >= T-1 fails; the bay may still be solvable.")

    # FIX 1: C <= S is Galle's terminal case; solve exactly, no QAOA.
    if C <= len(bay):
        plan = solve_small_bay(bay, height)
        out.update(status='solved_by_lemma1', qaoa=None, presolve_plan=plan, known_optimum=plan['relocations'],
                   exact=dict(relocations=plan['relocations'], moves=plan['moves'], source='Galle Lemma 1 (C <= S), exact'),
                   message=f'C={C} <= S={len(bay)}: the optimum equals the blocking count ({plan["relocations"]}); '
                           'no quantum step is needed.')
        out['seconds'] = round(time.time() - t0, 2); log(out['message']); return out

    # classical references first (FIX 2: infeasibility is a result, not a crash)
    greedy = None
    try:
        g = feasible_upper_bound(bay, height)
        greedy = dict(relocations=g['upper_bound'], moves=_norm_moves(g['moves']))
    except ValueError:
        out['notes'].append('The greedy rule got stuck (no free destination).')
    if cfg.baselines and greedy:
        out['greedy'] = greedy; log(f"Greedy rule: {greedy['relocations']} relocations")
    if (cfg.baselines or greedy is None) and C <= cfg.bfs_max_containers:
        try:
            b = physical_bfs(bay, height)
            out['exact'] = dict(relocations=b['optimum'], moves=_norm_moves(b['moves']), source='breadth-first search (proven)')
            log(f"Exact optimum (BFS): {b['optimum']} relocations")
        except ValueError:
            out.update(status='infeasible', message='No legal restricted retrieval sequence exists (proven by exhaustive search). '
                                                    'No QAOA model was built.')
            out['seconds'] = round(time.time() - t0, 2); log(out['message']); return out
    check()
    if cfg.milp:
        try:
            gm = GalleModel(bay, height)
            if len(gm.rows) > 200_000:
                raise MemoryError(f'{len(gm.rows):,} rows')
            log(f"Solving Galle's CRP-I MILP with HiGHS ({len(gm.names):,} variables, {len(gm.rows):,} rows)…")
            r = solve_milp(gm, limit=60); d = decode_galle(gm, r['assignment'])
            if d.get('valid'):
                out['milp'] = dict(relocations=d['relocations'], moves=_norm_moves(d['moves']), objective=r['objective'],
                                   gap=r['gap'], source='Galle CRP-I MILP (SciPy HiGHS)')
                log(f"MILP: {d['relocations']} relocations (MIP gap {r['gap']:.3g})")
        except Exception as e:
            out['notes'].append(f'MILP reference not available: {type(e).__name__}: {e}')
    check()

    log(f"Building the {METHODS[cfg.method]} model…")
    try:
        problem = Problem(bay, height, cfg.method, synthesis=cfg.synthesis, presolve=cfg.presolve)
    except InfeasibleInstance as e:
        out.update(status='infeasible', message=str(e)); return out
    except MemoryError as e:
        rows = re.search(r'has ([\d,]+) rows', str(e))
        out.update(status='too_large_to_build',
                   message=(f"Galle's model for this bay has {rows.group(1) if rows else 'too many'} constraint rows, too large "
                            "to build on a laptop, let alone simulate. Only the classical baselines are shown; "
                            "no QAOA result is claimed." if rows else f'Model too large to build: {e}'))
        return out
    except ValueError as e:
        if 'Greedy plan is blocked' in str(e):
            out.update(status='no_qubo_bound', message='The QUBO encoding needs a greedy feasible plan to set its penalty '
                                                       'weight, and the greedy rule got stuck. Use the predicate or hybrid encoding.')
            return out
        raise
    res = encoding_resources(problem, cfg.depth); out['resources'] = res
    enc = problem.predicate or problem.hybrid or problem.qubo
    if enc is not None:
        out['reduction'] = dict(presolve=cfg.presolve, galle_variables=len(problem.model.names),
                                remaining=len(enc.presolve.roots), steps=dict(getattr(enc.presolve, 'stats', {})))
    log(f"Qubits {res['qubits']} (measured {res['measured_qubits']}), logical two-qubit gates {res['logical_cx']:,} at p={cfg.depth}")
    check()

    if problem.n == 0:
        o = problem.outcome([])
        out.update(status='solved_by_presolve', message='Presolve fixed every variable; no quantum step was needed.')
        if o.get('valid'):
            out['qaoa'] = None; out['presolve_plan'] = dict(relocations=o['relocations'], moves=_norm_moves(o['moves']))
            out['known_optimum'] = o['relocations']
        return out
    if problem.n > cfg.max_qubits:
        out.update(status='too_large_to_simulate',
                   message=(f"{problem.n} qubits is beyond the simulation limit of {cfg.max_qubits} (memory doubles per qubit). "
                            "Resources and classical baselines are shown; no QAOA result is claimed."))
        out['known_optimum'] = (out.get('exact') or out.get('milp') or {}).get('relocations', ref['best_known'] if ref else None)
        log(out['message']); return out

    log('Computing the exact outcome of every bitstring (evaluation only)…')
    table = evaluation_table(problem, cancelled=cancelled, log=log)
    n = table['n']; E = table['E']; total = cfg.shots * cfg.jobs
    if table['best_cost'] is None:
        out.update(status='infeasible', message='No bitstring of the encoding decodes to a legal plan.'); return out
    check()

    # angles
    theta = concentrated_angles(cfg.depth, cfg.method); angle_note = 'transferred concentrated angles'
    if cfg.method == 'coherent':
        angle_note += ' (no calibrated set for the coherent oracle: predicate angles reused)'
    if cfg.angles == 'tune':
        log('Tuning angles on this instance (exact expectation)…')
        t = tune_angles(dict(E=E, n=n), problem.scale, pmax=cfg.depth, restarts=2, seed=cfg.seed, cancelled=cancelled, log=log)
        theta = t[cfg.depth]['theta']
        angle_note = 'tuned on this instance (exact ideal expectation)'
        if cfg.backend != 'ideal':      # FIX 5: say what is actually done
            angle_note += f'; the same ideal-tuned angles are then run on the {BACKENDS[cfg.backend]}'
    out['angles'] = dict(theta=[float(x) for x in theta], source=angle_note)
    check()

    P_ideal = qaoa_probs(E, theta, cfg.depth, problem.scale, n)
    prob_fn = lambda t: qaoa_probs(E, t, cfg.depth, problem.scale, n)
    states = None
    if cfg.backend == 'global':
        cx = logical_two_qubit_gates(problem, cfg.depth)['cx']; F = fidelity(cx, cfg.p2)
        out['noise'] = dict(model='global depolarising, before routing', two_qubit_gates=cx, p2=cfg.p2, readout=cfg.readout,
                            fidelity=F, note='F=(1-p2)^CX; P_noisy=F*P+(1-F)/2^n, then independent readout flips')
        prob_fn = lambda t: noisy(qaoa_probs(E, t, cfg.depth, problem.scale, n), n, F, cfg.readout)
        log(f'Global noise model: {cx:,} two-qubit gates, circuit fidelity F={F:.4g}')
    elif cfg.backend == 'gate_level':
        if cfg.angles == 'transfer_refine':
            out['notes'].append('Refinement is not run under gate-level noise; the starting angles were used.')
        log(f'Gate-level Pauli-fault simulation: {cfg.histories} error histories, p2={cfg.p2}, p1=p2/10, readout {cfg.readout}…')
        try:
            P_model, cx = gate_level_distribution(problem, theta, cfg.depth, cfg.p2, cfg.readout, cfg.histories, cfg.seed,
                                                  cancelled=cancelled, log=log)
        except (ValueError, MemoryError) as e:
            out.update(status='unsupported_noise_circuit', message=f'Gate-level noise not available for this model: {e}')
            return out
        out['noise'] = dict(model='gate-level Pauli faults (logical circuit, before routing)', two_qubit_gates=cx, p2=cfg.p2,
                            p1=cfg.p2 / 10, readout=cfg.readout, histories=cfg.histories)
        prob_fn = None
        states = np.random.default_rng(cfg.seed).choice(len(P_model), total, p=P_model)
    if cfg.backend in ('ideal', 'global'):
        if cfg.angles == 'transfer_refine':
            log(f'Shot-based refinement: {cfg.jobs} jobs × {cfg.shots} shots…')
            r = shot_refinement(prob_fn, E, n, problem.scale, cfg.depth, cfg.shots, cfg.jobs, cfg.seed, theta, cancelled=cancelled)
            states = r['every']; theta = r['theta']
            out['angles'].update(theta=[float(x) for x in theta], source='transferred, then refined by COBYLA on sampled energies')
            P_ideal = qaoa_probs(E, theta, cfg.depth, problem.scale, n)
        else:
            log(f'Sampling {total:,} shots…')
            states = np.random.default_rng(cfg.seed).choice(len(E), total, p=prob_fn(theta))
        P_model = prob_fn(theta)
    elif cfg.backend == 'fake_ibm':
        log('Compiling for a fake IBM device and simulating its noise (Qiskit Aer)…')
        if cfg.method == 'coherent':
            out.update(status='unsupported', message='The fake-IBM path is not wired for the coherent oracle (needs clean scratch).')
            return out
        try:
            from qiskit.transpiler import generate_preset_pass_manager
            from qiskit_aer import AerSimulator
        except ImportError as e:
            out.update(status='missing_packages', message=f'Fake-IBM mode needs qiskit, qiskit-aer and qiskit-ibm-runtime ({e}).')
            return out
        if cfg.angles == 'transfer_refine':
            out['notes'].append('Refinement is not run on the fake chip; the starting angles were used.')
        backend = fake_backend(); pm = generate_preset_pass_manager(optimization_level=2, backend=backend, seed_transpiler=cfg.seed)
        isa = pm.run(bind(problem.circuit(cfg.depth), theta, cfg.depth))
        out['device'] = dict(name=backend.name, transpiled_two_qubit_gates=sum(len(i.qubits) == 2 for i in isa.data),
                             transpiled_depth=isa.depth())
        log(f"Device {backend.name}: {out['device']['transpiled_two_qubit_gates']} two-qubit gates after routing")
        check()
        counts = AerSimulator.from_backend(backend).run(isa, shots=total, seed_simulator=cfg.seed).result().get_counts()
        states = np.concatenate([np.full(c, int(k.replace(' ', '')[-n:], 2), dtype=np.int64) for k, c in counts.items()])
        P_model = None
    check()

    # exact probabilities (FIX 3: replay-optimal vs energy-ground)
    N = 1 << n; U = np.full(N, 1.0 / N)
    out['exact_probabilities'] = dict(ideal=exact_probabilities(P_ideal, table), uniform=exact_probabilities(U, table),
                                      model=None if P_model is None else exact_probabilities(P_model, table),
                                      best_cost_in_encoding=table['best_cost'])

    log('Scoring samples (QAOA, random guessing, annealing) with the same decoder…')
    q = score_states(states, table)
    u = score_states(np.random.default_rng(cfg.seed + 7919).integers(0, N, total), table)     # FIX 10: own stream
    q['times_random'] = q['legal_fraction'] / u['legal_fraction'] if u['legal_fraction'] else None
    out['qaoa'] = q; out['uniform'] = u
    for key in ('qaoa', 'uniform'):
        if out[key]['best']:
            out[key]['best'].update(plan_of_state(problem, out[key]['best']['state'], bay, height))
    if cfg.baselines:
        check()
        weight = getattr(problem.predicate or problem.hybrid or problem.qubo, 'weight', problem.scale) if cfg.method != 'coherent' else problem.oracle.bound + 1
        outcome = lambda s: dict(decoder_accepted=bool(table['accepted'][s]),
                                 replayed_relocations=int(table['cost'][s]) if table['accepted'][s] else None)
        rec, arrays = anneal(lambda s: float(E[s]), outcome, width=n, weight=weight,
                             instance_key=digest(dict(capacity=height, stacks=sorted([list(s) for s in bay]))),
                             seed=cfg.seed, budget=total)
        sel = rec['selected']
        sa = dict(evaluations=rec['candidate_evaluations'], protocol=SA_PROTOCOL, T0=rec['T0'], T1=rec['T1'],
                  legal_fraction=float(table['accepted'][arrays['states'].astype(np.int64)].mean()))
        if sel['state'] is not None:
            sa.update(plan_of_state(problem, sel['state'], bay, height))
        else:
            sa['relocations'] = None
        out['annealing'] = sa
    best = q['best']
    known = (out.get('exact') or out.get('milp') or {}).get('relocations', ref['best_known'] if ref else None)
    if known is None:
        known = table['best_cost']; out['known_optimum_source'] = 'minimum over the exactly enumerated encoding'
    out['known_optimum'] = known
    if best and known is not None:
        out['gap'] = best['relocations'] - known
        out['accuracy_percent'] = 100.0 if best['relocations'] == known == 0 else (100.0 * known / best['relocations'] if best['relocations'] else None)
    out['seconds'] = round(time.time() - t0, 2)
    log(f"Done in {out['seconds']} s: best QAOA plan "
        + (f"{best['relocations']} relocations" if best else 'none (no legal sample)')
        + f"; legal-plan rate {q['legal_fraction']:.2%} vs random {u['legal_fraction']:.2%}")
    return out


def summary_text(r):
    """Plain-text report of one run, shown in the Summary tab and saved with results."""
    L = [f"Instance {r['instance']}  ·  {len(r['stacks'])} stacks, capacity {r['capacity']}, {r['containers']} containers"]
    ref = r.get('reference')
    if r.get('exact'):
        L.append(f"Optimum: {r['exact']['relocations']} relocations — {r['exact']['source']}")
    if ref:
        L.append(f"Published value: {ref['best_known']} relocations ({'proven optimal' if ref['proven_optimal'] else 'best known, not proven'})")
    if r.get('milp'):
        L.append(f"Galle MILP: {r['milp']['relocations']} relocations (MIP gap {r['milp']['gap']:.3g})")
    c = r['config']
    L.append(f"Method {METHODS[c['method']]} · p={c['depth']} · {c['shots']} shots × {c['jobs']} jobs · {BACKENDS[c['backend']]}")
    if r.get('reduction'):
        z = r['reduction']
        L.append(f"Variable reduction: {PRESOLVE_LABELS[z['presolve']]}; {z['galle_variables']:,} Galle variables → {z['remaining']} remain"
                 + (' (' + ', '.join(f'{k.replace("_", " ")} {v}' for k, v in z['steps'].items() if k != 'qubits') + ')' if z['steps'] else ''))
    if r.get('resources'):
        x = r['resources']
        L.append(f"Resources: {x['qubits']} qubits ({x['measured_qubits']} measured, {x['decision_qubits']} decision), "
                 f"{x['logical_cx']:,} logical two-qubit gates")
    if r.get('noise'):
        z = r['noise']; L.append(f"Noise: {z['model']}; p2={z['p2']}, readout {z['readout']}"
                                 + (f", fidelity F={z['fidelity']:.4g}" if 'fidelity' in z else f", {z.get('histories')} histories"))
    if r.get('device'):
        d = r['device']; L.append(f"Device {d['name']}: {d['transpiled_two_qubit_gates']} two-qubit gates after routing, depth {d['transpiled_depth']}")
    if r['status'] != 'ok':
        L.append(''); L.append(f"STATUS: {r['status']}"); L.append(r.get('message', ''))
        if r.get('presolve_plan'):
            L.append(f"Exact plan: {r['presolve_plan']['relocations']} relocations")
    q = r.get('qaoa')
    if q:
        L.append('')
        L.append('QAOA RESULT')
        b = q['best']
        L.append(f"  Best legal plan: {b['relocations']} relocations (seen {b['count']} times)" if b else '  No legal plan was sampled.')
        if r.get('gap') is not None:
            L.append(f"  Gap to the optimum/reference: {r['gap']:+d}   ·   accuracy {r['accuracy_percent']:.1f}%" if r.get('accuracy_percent') is not None else f"  Gap: {r['gap']:+d}")
        L.append(f"  Legal-plan rate {q['legal_fraction']:.2%}  vs random {r['uniform']['legal_fraction']:.2%}  →  "
                 + (f"{q['times_random']:.1f}× random" if q['times_random'] else 'n/a'))
        L.append(f"  Distinct legal plans sampled: {q['distinct_legal_plans']}")
        if q['cost_histogram']:
            L.append('  Share of shots by plan cost: ' + ', '.join(f"{k} reloc: {v:.2%}" for k, v in q['cost_histogram'].items()))
        e = r.get('exact_probabilities')
        if e:
            i, u, m = e['ideal'], e['uniform'], e['model']
            L.append(f"  Exact P(legal plan)        ideal {i['P_accepted']:.3%}" + (f"  noisy {m['P_accepted']:.3%}" if m and r['config']['backend'] != 'ideal' else '') + f"  random {u['P_accepted']:.3%}")
            L.append(f"  Exact P(optimal plan)      ideal {i['P_replay_optimal']:.3%}" + (f"  noisy {m['P_replay_optimal']:.3%}" if m and r['config']['backend'] != 'ideal' else '') + f"  random {u['P_replay_optimal']:.3%}")
            L.append(f"  Exact P(lowest energy)     ideal {i['P_energy_ground']:.3%}  random {u['P_energy_ground']:.3%}"
                     "   (a subset of optimal plans)")
        L.append(f"  Angles: {', '.join(f'{x:.3f}' for x in r['angles']['theta'])}  ({r['angles']['source']})")
        L.append('')
        L.append('COMPARISON (same sample budget)')
        u = r['uniform']['best']
        L.append(f"  Random guessing best plan: {u['relocations'] if u else 'none'} relocations")
        if r.get('annealing'):
            a = r['annealing']
            L.append(f"  Simulated annealing (corrected protocol): {a['relocations'] if a['relocations'] is not None else 'none'} relocations")
    if r.get('greedy'):
        L.append(f"  Greedy rule:               {r['greedy']['relocations']} relocations")
    for n_ in r.get('notes', []):
        L.append('Note: ' + n_)
    if r.get('seconds') is not None:
        L.append(''); L.append(f"Run time {r['seconds']} s")
    L.append('')
    L.append('This is a simulation of QAOA on an ordinary computer; it is not evidence of quantum advantage.')
    return '\n'.join(L)


def galle_variable_count(S_, C):
    """Exact CRP-I variable count (Galle Table 3 convention; sum runs to N)."""
    if C <= S_:
        return 0
    N = C - S_ + 1
    return sum((C + S_ - k + 1) * (C - k + 1) for k in range(1, N + 1)) + (C - N)


def galle_row_estimate(S_, C):
    """Row count before preprocessing rows, same formula as Problem's build guard."""
    n, s = C, S_
    total_m = (n - s) * (n + s - 1) // 2
    total_m2 = (n - 1) * n * (2 * n - 1) // 6 - (s - 1) * s * (2 * s - 1) // 6
    return n * (n + s) + 2 * total_m + (1 + 2 * s) * (total_m2 - total_m) + s * (n - s) + s * (s - 1) // 2 + 3 * total_m2 + (3 * s - 3) * total_m


def resource_report(stacks, height, depth=1, methods=('predicate', 'hybrid', 'galle', 'coherent'), cancelled=_never,
                    presolves=('standard', 'strong')):
    """Build every encoding (no simulation) and compare qubits and logical gates."""
    rows = []
    C = sum(map(len, stacks)); S_ = len(stacks)
    if C > S_:
        rows.append(dict(method="Galle CRP-I (original MILP)", qubits=None, measured=None, decision=galle_variable_count(S_, C),
                         extra=None, cx=None, note=f'{galle_variable_count(S_, C):,} binary variables, '
                                                   f'about {galle_row_estimate(S_, C):,} rows before presolve'))
    for m in methods:
        for ps in (presolves if m != 'coherent' else ('standard',)):
            if cancelled():
                raise Cancelled()
            t = time.time(); label = METHODS[m] + ('' if m == 'coherent' else f' · {ps}')
            try:
                pr = Problem(stacks, height, m, presolve=ps)
                g = logical_two_qubit_gates(pr, depth)
                rows.append(dict(method=label, qubits=g['qubits'], measured=pr.n, decision=g['decision_qubits'],
                                 extra=g['qubits'] - g['decision_qubits'], cx=g['cx'],
                                 note=f'built in {time.time() - t:.2f} s; phase scale {pr.scale}'))
            except Exception as e:
                rows.append(dict(method=label, note=f'{type(e).__name__}: {str(e)[:160]}'))
    try:
        mv = count_only(stacks, height)
        rows.append(dict(method='Move encoding (greedy-witness slots)', qubits=mv['decision_bits'], measured=mv['decision_bits'],
                         decision=mv['decision_bits'], extra=None, cx=None,
                         note=f"K={mv['K']} slots × {mv['bits_per_destination']} bits; compiler workspace not counted"))
    except Exception as e:
        rows.append(dict(method='Move encoding', note=f'{type(e).__name__}: {e}'))
    return rows


def export_model(stacks, height, method, folder, depth=1, presolve='standard'):
    """Write the encoding's coefficients (and a circuit, if Qiskit is installed) to a folder."""
    folder = Path(folder); folder.mkdir(parents=True, exist_ok=True)
    pr = Problem(stacks, height, method, presolve=presolve)
    written = []
    if method == 'galle':
        pr.qubo.export(folder); written += ['qubo.json', 'provenance.json', 'original_model.json', 'full_single_QUBO.txt', 'ising.json']
    elif method in ('predicate', 'hybrid'):
        enc = pr.predicate or pr.hybrid
        poly = enc.merged if method == 'predicate' else enc.poly
        data = dict(method=method, presolve=presolve, instance=dict(stacks_bottom_to_top=[list(s) for s in stacks], capacity=height),
                    convention='E(x) = sum over monomials of coeff * prod(x_i); x binary; bit i = qubit i',
                    penalty_weight=enc.weight, measured_qubits=pr.n,
                    variables=[pr.model.names[r] for r in enc.presolve.roots] + [f'slack[{i}]' for i in range(pr.n - len(enc.presolve.roots))],
                    polynomial=[[list(k), v] for k, v in sorted(poly.items(), key=lambda a: (len(a[0]), a[0]))],
                    pauli_constant=enc.pauli_constant, pauli_terms=[[list(t), a] for t, a in enc.pauli_terms],
                    recovery=enc.presolve.mapping, original_variables=pr.model.names,
                    arithmetic_rows=([dict(terms=sorted(r.terms.items()), sense=r.sense, rhs=r.rhs)
                                      for r, keys, _ in enc.rows if len(keys) > enc.direct_cutoff]
                                     if method == 'predicate' else []))
        (folder / f'{method}_model.json').write_text(json.dumps(data, indent=1) + '\n'); written.append(f'{method}_model.json')
    (folder / 'resources.json').write_text(json.dumps(pr.resources(depth), indent=2, default=str) + '\n'); written.append('resources.json')
    try:
        from qiskit import qasm3
        if pr.n:
            (folder / f'circuit_p{depth}.qasm').write_text(qasm3.dumps(pr.circuit(depth))); written.append(f'circuit_p{depth}.qasm')
    except ImportError:
        pass
    return written


# ============================================================================
# SELF-TEST: finite checks of the merged code (run: python rcrp_qaoa_suite.py selftest)
# ============================================================================
def selftest(say=print, quick=False, cancelled=_never):
    """Returns (passed, failed). Each check prints one line. Finite checks, not proofs."""
    passed = failed = 0

    def ok(name, cond, detail=''):
        nonlocal passed, failed
        if cancelled():
            raise Cancelled()
        if cond:
            passed += 1; say(f'  PASS  {name}' + (f'  ({detail})' if detail else ''))
        else:
            failed += 1; say(f'  FAIL  {name}' + (f'  ({detail})' if detail else ''))

    def guarded(name, fn):
        nonlocal failed
        try:
            fn()
        except Cancelled:
            raise
        except Exception as e:
            failed += 1; say(f'  FAIL  {name}: {type(e).__name__}: {e}')
            say('        ' + traceback.format_exc().strip().splitlines()[-2].strip())

    t0 = time.time()
    say('Catalog')

    def t_catalog():
        cat = catalog(); ok('embedded catalog decodes', len(cat) == 840, f'{len(cat)} bays')
        ok('820+ bays carry a published reference', sum(1 for r in cat if r['reference']) >= 800)
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            bad = 0
            for r in cat[::37]:
                f = Path(d) / f"{r['id']}.txt"; f.write_text(_bay_file_text(r['stacks_bottom_to_top'], r['capacity']))
                bay, h = read_instance(str(f), None, None)
                bad += [list(s) for s in bay] != r['stacks_bottom_to_top'] or h != r['capacity']
            ok('file text round-trips through the original parser', bad == 0)
        ok('data3-3-1 is bottom-to-top as published', catalog_item('data3-3-1')['stacks_bottom_to_top'] == [[3, 7, 1], [2, 6, 5], [8, 9, 4]])
    guarded('catalog', t_catalog)

    say('Exactness of every encoding on random tiny bays (global minima = optimal legal plans)')

    def t_exact():
        rng = random.Random(20261010); bays = []
        sizes = [(3, 3, 4), (3, 3, 5), (3, 4, 5), (4, 3, 5), (3, 4, 6), (4, 3, 6), (3, 3, 6)]
        while len(bays) < (8 if quick else 18):
            S_, T_, C_ = rng.choice(sizes); bay = random_bay(S_, T_, C_, rng.randrange(10 ** 9))
            try:
                physical_bfs(bay, T_)
            except ValueError:
                continue
            bays.append((bay, T_))
        counts = Counter(); bad = []
        for bay, T_ in bays:
            opt = physical_bfs(bay, T_)['optimum']
            for m in ('predicate', 'hybrid', 'galle', 'coherent'):
                try:
                    pr = Problem(bay, T_, m)
                except InfeasibleInstance:
                    continue
                if pr.n == 0:
                    o = pr.outcome([]); counts[m] += 1
                    if not (o.get('valid') and o['relocations'] == opt):
                        bad.append((m, bay, 'presolve plan'))
                    continue
                if pr.n > 16:
                    continue
                t = evaluation_table(pr)
                g = np.flatnonzero(t['ground'])
                fine = (t['best_cost'] == opt and t['accepted'][g].all() and (t['cost'][g] == opt).all())
                if m != 'coherent':      # predicate/QUBO/hybrid: ground energy equals the optimum
                    fine &= abs(t['optimum_energy'] - opt) < 1e-9
                for s in np.flatnonzero(t['accepted'])[:40]:
                    pl = plan_of_state(pr, s, bay, T_)
                    fine &= pl is not None and pl['relocations'] == t['cost'][s]
                counts[m] += 1
                if not fine:
                    bad.append((m, bay, T_, opt, t['best_cost']))
        ok('ground states decode to optimal plans and accepted plans replay legally', not bad,
           ', '.join(f'{k}: {v} bays' for k, v in sorted(counts.items())) if not bad else str(bad[:2]))
    guarded('exactness', t_exact)

    say('Strong variable reduction (option 2) keeps every legal plan and the optimum')

    def t_strong():
        rng = random.Random(77); lost = bad = nb = 0; saved = []
        while nb < (6 if quick else 25):
            S_ = rng.choice([3, 4]); T_ = rng.choice([3, 4]); C_ = rng.randint(S_ + 1, min(S_ * T_, 7))
            bay = random_bay(S_, T_, C_, rng.randrange(10 ** 9))
            try:
                opt = physical_bfs(bay, T_)['optimum']
            except ValueError:
                continue
            nb += 1; gm = GalleModel(bay, T_)
            plans = [encode_stages(gm, st) for st, _ in legal_prefixes(gm)]
            for m in ('predicate', 'hybrid', 'galle'):
                pr = Problem(bay, T_, m, presolve='strong'); pre = (pr.predicate or pr.hybrid or pr.qubo).presolve
                for x in plans:
                    y = pre.reduce_assignment(x); yy = dict(enumerate(y))
                    lost += pre.recover(y) != x or any(not r.holds(yy) for r in pre.reduced_rows)
                if pr.n == 0:
                    bad += pr.outcome([]).get('relocations') != opt
                elif pr.n <= 16:
                    t = evaluation_table(pr); g = np.flatnonzero(t['ground'])
                    bad += not (t['best_cost'] == opt and t['accepted'][g].all() and (t['cost'][g] == opt).all())
                if m == 'predicate':
                    saved.append((Problem(bay, T_, m).n, pr.n))
        ok('every legal plan survives the reduction (encoded, recovered, all constraints hold)', lost == 0, f'{nb} bays × 3 encodings')
        ok('minimum and ground states unchanged (optimal plans)', bad == 0)
        a, b = sum(x for x, _ in saved), sum(y for _, y in saved)
        ok('the reduction never adds qubits', all(y <= x for x, y in saved), f'predicate qubits {a} → {b} in total')
        bay = tuple(map(tuple, catalog_item('data3-3-2')['stacks_bottom_to_top']))
        ok('data3-3-2 needs far fewer qubits', Problem(bay, 5, 'predicate', presolve='strong').n < Problem(bay, 5, 'predicate').n,
           f"{Problem(bay, 5, 'predicate').n} → {Problem(bay, 5, 'predicate', presolve='strong').n}")
    guarded('strong', t_strong)

    say('QUBO algebra and certificates')

    def t_qubo():
        rng = random.Random(7); bad = 0; nb = 0
        for _ in range(6 if quick else 15):
            bay = random_bay(3, 4, rng.choice([5, 6]), rng.randrange(10 ** 9))
            try:
                plan = feasible_upper_bound(bay, 4)
            except ValueError:
                continue
            gm = GalleModel(bay, 4); q = Qubo(gm, plan['upper_bound']); nb += 1
            x = gm.assignment_from_moves(plan['moves'])
            y = q.complete(x)                                   # asserts energy == model cost
            bad += q.energy(y) != gm.cost(x)
            r = np.random.default_rng(nb)
            for _ in range(50):
                z = list(r.integers(0, 2, len(q.names)))
                bad += q.energy(z) != q.component_energy(z)
            bad += max((len(k) for k in q.quadratic), default=2) != 2
        ok('expanded QUBO coefficients equal the per-constraint penalty expression', bad == 0, f'{nb} bays × 50 strings')
        for _ in range(500):
            K = rng.randrange(0, 300); w = bounded_weights(K)
            sums = {sum(c for c, b in zip(w, bits) if b) for bits in product((0, 1), repeat=len(w))} if len(w) <= 12 else None
            if sums is not None and sums != set(range(K + 1)):
                bad += 1
        ok('bounded slack weights represent exactly 0..K', bad == 0)
        bad = 0
        for r_ in range(-60, 61):
            P = r_ * (r_ + 1) // 2
            bad += P < 0 or (P == 0) != (r_ in (0, -1))
        ok('compact penalty r(r+1)/2 is zero exactly at r in {0,-1}, else >= 1', bad == 0)
    guarded('qubo', t_qubo)

    say('Independent physical checker')

    def t_physical():
        bay, T_ = ((1, 3), (2, 4), ()), 3
        b = physical_bfs(bay, T_)
        ok('tiny bay [[1,3],[2,4],[]] T=3 has optimum 2', b['optimum'] == 2)
        ok('BFS plan replays legally', replay_moves(bay, T_, b['moves'])['relocations'] == 2)
        for moves, why in (([dict(type='relocate', container=3, source=1, destination=1)], 'own stack'),
                           ([dict(type='retrieve', container=2, source=2)], 'wrong order'),
                           ([dict(type='relocate', container=4, source=2, destination=3)], 'non-blocker move')):
            try:
                replay_moves(bay, T_, moves, require_complete=False); ok(f'rejects {why}', False)
            except ValueError:
                ok(f'rejects {why}', True)
        try:
            replay_moves(((1, 3), (2, 4)), 2, [dict(type='relocate', container=3, source=1, destination=2)], require_complete=False)
            ok('rejects capacity breach', False)
        except ValueError:
            ok('rejects capacity breach', True)
        gm = GalleModel(((1, 3, 2), (), (5, 4)), 3)
        good = gm.assignment_from_moves([dict(type='relocate', container=2, **{'from': 1, 'to': 2}),
                                         dict(type='relocate', container=3, **{'from': 1, 'to': 2}),
                                         dict(type='retrieve', container=1, **{'from': 1}),
                                         dict(type='relocate', container=3, **{'from': 2, 'to': 1}),
                                         dict(type='retrieve', container=2, **{'from': 2})])
        ok('two blockers sharing a destination reverse order (zero violations)', not gm.violations(good))
        ok('reconstruct_assignment agrees with decode_galle', reconstruct_assignment(gm, good)['relocations'] == decode_galle(gm, good)['relocations'])
    guarded('physical', t_physical)

    say('Lemma 1 (C <= S) and infeasibility (FIX 1, FIX 2)')

    def t_small():
        rng = random.Random(3); bad = 0; n_ = 0
        for _ in range(200):
            S_ = rng.randint(2, 5); C_ = rng.randint(1, S_); T_ = rng.randint(1, 4)
            if C_ > S_ * T_:
                continue
            bay = random_bay(S_, T_, C_, rng.randrange(10 ** 9))
            try:
                opt = physical_bfs(bay, T_)['optimum']
            except ValueError:
                continue
            n_ += 1; bad += solve_small_bay(bay, T_)['relocations'] != opt
        ok('Lemma 1 plan equals the BFS optimum', bad == 0, f'{n_} bays')
        r = run(Config(stacks=[[1, 2], [3], []], capacity=3, shots=8, jobs=1), log=lambda s: None)
        ok('engine solves a C <= S bay without crashing', r['status'] == 'solved_by_lemma1' and r['known_optimum'] == 1)
        r = run(Config(stacks=[[1, 3], [2, 4]], capacity=2, shots=8, jobs=1), log=lambda s: None)
        ok('engine reports an infeasible bay as infeasible', r['status'] == 'infeasible')
    guarded('small', t_small)

    say('Simulator refactors reproduce the originals exactly')

    def t_sim():
        pr = Problem(tuple(map(tuple, catalog_item('data3-3-8')['stacks_bottom_to_top'])), 5, 'predicate'); L = landscape(pr)
        a = shot_protocol(L, pr.scale, 2, 64, 8, 5, initial=concentrated_angles(2))
        b = shot_refinement(lambda t: qaoa_probs(L['E'], t, 2, pr.scale, L['n']), L['E'], L['n'], pr.scale, 2, 64, 8, 5,
                            concentrated_angles(2), rhobeg=.3)
        ok('shot_refinement == paper_sim.shot_protocol (same seed)', np.array_equal(a['every'], b['every']) and np.allclose(a['theta'], b['theta']))
        if not quick:
            t1 = tune(L, pr.scale, pmax=1, restarts=1, seed=2); t2 = tune_angles(L, pr.scale, pmax=1, restarts=1, seed=2)
            ok('tune_angles == paper_sim.tune (same seed)', np.allclose(t1[1]['theta'], t2[1]['theta']))
        for m in ('predicate', 'hybrid', 'galle'):
            pr = Problem(((1, 3), (4, 5), (2,)), 3, m); L = landscape(pr)
            if pr.n == 0 or pr.n > 12:
                continue
            th = concentrated_angles(2, m)
            P0 = qaoa_probs(L['E'], th, 2, pr.scale, L['n'])
            P1, _ = gate_level_distribution(pr, th, 2, 0.0, 0.0, 4, 0)
            ok(f'gate-level noise at p2=0 equals exact QAOA ({m}, {pr.n} qubits)', np.abs(P0 - P1).max() < 2e-5, f'max diff {np.abs(P0 - P1).max():.1e}')
        P = noisy(P0, L['n'], .7, .02)
        ok('global noise channel keeps total probability 1', abs(P.sum() - 1) < 1e-12)
    guarded('simulator', t_sim)

    say('Corrected simulated annealing (protocol /2)')

    def t_sa():
        pr = Problem(tuple(map(tuple, catalog_item('data3-3-8')['stacks_bottom_to_top'])), 5, 'predicate'); t = evaluation_table(pr)
        out = lambda s: dict(decoder_accepted=bool(t['accepted'][s]), replayed_relocations=int(t['cost'][s]) if t['accepted'][s] else None)
        for B in (1, 2, 17, 4096):
            rec, arr = anneal(lambda s: float(t['E'][s]), out, width=t['n'], weight=pr.predicate.weight, instance_key='selftest', seed=1, budget=B)
            ok(f'SA evaluates exactly B={B} candidates', rec['candidate_evaluations'] == B and len(arr['states']) == B)
        seen = arr['states'].astype(np.int64); acc = t['accepted'][seen]
        best = int(t['cost'][seen][acc].min()) if acc.any() else None
        ok('SA returns the best replayed plan among ALL evaluated candidates', rec['selected']['replayed_relocations'] == best)
    guarded('sa', t_sa)

    say('Qiskit circuits match the NumPy simulator (skipped if Qiskit is missing)')

    def t_qiskit():
        try:
            from qiskit.quantum_info import Statevector
        except ImportError:
            say('  SKIP  qiskit not installed'); return
        bay, T_ = ((1, 3), (4, 5), (2,)), 3
        for m, syn in (('predicate', 'pauli'), ('predicate', 'mcp'), ('hybrid', 'pauli'), ('galle', 'pauli')):
            pr = Problem(bay, T_, m, synthesis=syn)
            if pr.n == 0:
                continue
            p = 2; th = concentrated_angles(p, m)
            qc = bind(pr.circuit(p), th, p).remove_final_measurements(inplace=False)
            Pq = Statevector(qc).probabilities(list(range(pr.n)))
            L = landscape(pr); Pn = qaoa_probs(L['E'], th, p, pr.scale, pr.n)
            ok(f'{m}/{syn}: circuit distribution equals NumPy QAOA', np.abs(Pq - Pn).max() < 1e-9,
               f'{qc.num_qubits} qubits, max diff {np.abs(Pq - Pn).max():.1e}')
    guarded('qiskit', t_qiskit)

    def t_coherent_gates():
        # The coherent oracle needs hundreds of scratch qubits, too many for a
        # statevector. Its compute/uncompute part is classical-reversible (X, CX,
        # CCX), so run it on every basis input and check the phase bits and the
        # clean return of all scratch.
        oracle = build_oracle(((1, 3), (4, 5), (2,)), 3); mapping, work = oracle.wiring()
        gates = list(oracle.forward_gates()); n = len(oracle.logic.inputs); bad = 0
        for x in range(1 << n):
            bits = [(x >> i) & 1 for i in range(n)] + [0] * len(work)
            for name, args in gates:
                if name == 'x': bits[args[0]] ^= 1
                elif name == 'cx': bits[args[1]] ^= bits[args[0]]
                else: bits[args[2]] ^= bits[args[0]] & bits[args[1]]
            phase = sum(w * (1 if lit == 1 else bits[mapping[lit]] if lit > 0 else 1 - bits[mapping[-lit]])
                        for lit, w in oracle.phases.items())
            bad += phase != oracle.evaluate([(x >> i) & 1 for i in range(n)])['energy']
            for name, args in reversed(gates):
                if name == 'x': bits[args[0]] ^= 1
                elif name == 'cx': bits[args[1]] ^= bits[args[0]]
                else: bits[args[2]] ^= bits[args[0]] & bits[args[1]]
            bad += any(bits[n:]) or bits[:n] != [(x >> i) & 1 for i in range(n)]
        ok('coherent oracle: reversible circuit computes every phase and uncomputes all scratch', bad == 0,
           f'{1 << n} inputs, {len(work)} scratch qubits, {len(gates)} gates')
    guarded('coherent gates', t_coherent_gates)

    say('Engine end to end')

    def t_engine():
        r = run(Config(instance='data3-3-8', shots=256, jobs=8, seed=1, presolve='standard'), log=lambda s: None)
        b = r['qaoa']['best']
        ok('data3-3-8 predicate run completes with a legal replayed plan', r['status'] == 'ok' and b is not None)
        ok('known optimum agrees with BFS and the published value', r['known_optimum'] == 2 == r['reference']['best_known'])
        e = r['exact_probabilities']['ideal']
        ok('P(optimal plan) >= P(lowest energy) (FIX 3)', e['P_replay_optimal'] >= e['P_energy_ground'] - 1e-15,
           f"{e['P_replay_optimal']:.3%} vs {e['P_energy_ground']:.3%}")
        r = run(Config(instance='data3-3-8', backend='global', shots=128, jobs=4, presolve='standard'), log=lambda s: None)
        ok('global-noise backend runs', r['status'] == 'ok' and r['noise']['fidelity'] < 1)
        r = run(Config(instance='data3-3-2', shots=256, jobs=8, presolve='strong'), log=lambda s: None)
        ok('data3-3-2 (36 qubits before) now runs with the strong reduction', r['status'] == 'ok' and r['qaoa']['best'] is not None
           and r['known_optimum'] == 5, f"{r['resources']['qubits']} qubits, best {r['qaoa']['best']['relocations'] if r['qaoa']['best'] else None}")
        pr = Problem(tuple(map(tuple, catalog_item('data3-3-8')['stacks_bottom_to_top'])), 5, 'predicate'); L = landscape(pr)
        stop = {'n': 0}

        def cancel():
            stop['n'] += 1; return stop['n'] > 25
        t = time.time()
        try:
            tune_angles(L, pr.scale, pmax=3, restarts=4, cancelled=cancel); ok('Stop interrupts tuning (FIX 6)', False)
        except Cancelled:
            ok('Stop interrupts tuning (FIX 6)', time.time() - t < 5, f'stopped after {time.time() - t:.2f} s')
    guarded('engine', t_engine)

    say(f'\n{passed} passed, {failed} failed in {time.time() - t0:.1f} s. Finite checks, not a proof for every instance.')
    return passed, failed


# ============================================================================
# GUI   (QAOA_Workbench.py + Hardware_Panel.py, merged and redesigned)
# ============================================================================
RESULTS_DIR = Path.home() / 'rcrp_qaoa_results'
HW_METHODS = {'Predicate (fewest qubits)': 'predicate', 'Hybrid (fewest gates per qubit)': 'hybrid',
              'QUBO (baseline)': 'galle', 'Coherent oracle (research)': 'coherent'}
REDUCTIONS = {'Standard (as in the published study)': 'standard', 'Strong (fewer qubits; separate model, exact for the best plan)': 'strong'}  # FIX (Sim9) 12
PALETTE = dict(bg='#EEF1F4', card='#FFFFFF', ink='#17212B', muted='#5F6B78', line='#D5DBE1', accent='#1F6F8B',
               accent_dark='#16566C', target='#17212B', moved='#E07A3F', box='#2F7F9A', good='#2E7D4F', warn='#B26A00',
               bad='#B5473A', tile='#F7F9FA', qaoa='#1F6F8B', random='#E07A3F', grid='#C9CED4')


def launch_gui():
    try:
        import tkinter as tk
    except ImportError:
        raise SystemExit('tkinter is not installed. Windows/macOS: reinstall Python from python.org (it includes Tcl/Tk); '
                         'Debian/Ubuntu: sudo apt install python3-tk. Everything else works from the command line, e.g.  '
                         'python rcrp_qaoa_suite.py run --instance data3-3-8')
    root = tk.Tk()
    Suite(root)
    root.mainloop()
    return 0


class Suite:
    """One window: choose a bay (left), set up the run, read results (right)."""

    # ================================================================== setup
    def __init__(self, root):
        import tkinter as tk
        from tkinter import ttk, font as tkfont
        self.tk, self.ttk = tk, ttk
        self.root = root
        root.title('rCRP · QAOA Suite')
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()      # fit small laptop screens too
        w, h = min(1400, sw - 40), min(880, sh - 80); root.geometry(f'{w}x{h}+{max(0, (sw - w) // 2)}+{max(0, (sh - h) // 3)}')
        root.minsize(min(1120, w), min(640, h))
        root.configure(background=PALETTE['bg'])
        self.events = queue.Queue(); self.worker = None; self.cancel = False
        self.result = None; self.instances = catalog(); self.states = []; self.plans = {}; self.capacity = 1
        self.selected_key = None; self.size_gen = 0; self.size_cache = {}
        self.hw_process = None; self.hw_preview_key = None; self.hw_latest = None; self.hw_resolved = None
        self._fonts(tkfont); self._style()
        self._header(root)
        body = ttk.PanedWindow(root, orient='horizontal'); body.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        side = ttk.Frame(body, style='App.TFrame'); main = ttk.Frame(body, style='App.TFrame')
        body.add(side, weight=0); body.add(main, weight=1)
        self._sidebar(side); self._results(main)
        self.fill_list(); self._toggle_noise()
        root.after(100, self.poll)
        root.protocol('WM_DELETE_WINDOW', self.close)

    def _fonts(self, tkfont):
        base = tkfont.nametofont('TkDefaultFont'); size = max(10, abs(base.cget('size')))
        base.configure(size=size); tkfont.nametofont('TkTextFont').configure(size=size)
        fam = base.cget('family')
        self.f_title = tkfont.Font(family=fam, size=size + 6, weight='bold')
        self.f_head = tkfont.Font(family=fam, size=size + 2, weight='bold')
        self.f_sub = tkfont.Font(family=fam, size=size - 1)
        self.f_bold = tkfont.Font(family=fam, size=size, weight='bold')
        self.f_tile = tkfont.Font(family=fam, size=size + 9, weight='bold')
        mono = tkfont.nametofont('TkFixedFont'); self.f_mono = tkfont.Font(family=mono.cget('family'), size=size)
        self.f_box = tkfont.Font(family=mono.cget('family'), size=size + 1, weight='bold')
        self.row_h = int(size * 2.4)

    def _style(self):
        ttk = self.ttk; P = PALETTE; st = ttk.Style()
        try:
            st.theme_use('clam')
        except self.tk.TclError:
            pass
        st.configure('.', background=P['bg'], foreground=P['ink'])
        st.configure('App.TFrame', background=P['bg'])
        st.configure('Card.TFrame', background=P['card'], relief='flat')
        st.configure('Tile.TFrame', background=P['tile'])
        for name, extra in (('Card.TLabel', {}), ('CardHead.TLabel', dict(font=self.f_head)),
                            ('CardMuted.TLabel', dict(foreground=P['muted'], font=self.f_sub)),
                            ('CardBold.TLabel', dict(font=self.f_bold))):
            st.configure(name, background=P['card'], **extra)
        st.configure('Section.TLabel', background=P['card'], foreground=P['accent'], font=self.f_bold)
        st.configure('Title.TLabel', background=P['bg'], font=self.f_title)
        st.configure('Sub.TLabel', background=P['bg'], foreground=P['muted'])
        st.configure('TileCap.TLabel', background=P['tile'], foreground=P['muted'], font=self.f_sub)
        st.configure('TileVal.TLabel', background=P['tile'], font=self.f_tile)
        st.configure('TileDet.TLabel', background=P['tile'], foreground=P['muted'], font=self.f_sub)
        st.configure('TileSec.TLabel', background=P['tile'], foreground=P['accent'], font=self.f_bold)
        st.configure('TileVal2.TLabel', background=P['tile'], foreground=P['ink'], font=self.f_bold)
        for k, col in (('Good', P['good']), ('Warn', P['warn']), ('Bad', P['bad'])):
            st.configure(f'{k}.TLabel', background=P['card'], foreground=col, font=self.f_bold)
        st.configure('Card.TCheckbutton', background=P['card']); st.map('Card.TCheckbutton', background=[('active', P['card'])])
        st.configure('Tile.TCheckbutton', background=P['tile']); st.map('Tile.TCheckbutton', background=[('active', P['tile'])])
        st.configure('Accent.TButton', background=P['accent'], foreground='white', font=self.f_bold, padding=(14, 6), borderwidth=0)
        st.map('Accent.TButton', background=[('disabled', '#9DB7C2'), ('active', P['accent_dark'])], foreground=[('disabled', '#EEF3F5')])
        st.configure('TButton', padding=(10, 4))
        st.configure('TNotebook', background=P['bg'], borderwidth=0)
        st.configure('TNotebook.Tab', padding=(14, 6))
        st.map('TNotebook.Tab', background=[('selected', P['card'])])
        st.configure('Inner.TNotebook', background=P['card'])
        st.configure('Treeview', rowheight=self.row_h, background='white', fieldbackground='white')
        st.configure('Treeview.Heading', font=self.f_bold, padding=(4, 4))
        st.configure('Horizontal.TProgressbar', background=P['accent'])

    def _flow(self, label, pad=0):
        """Make a label re-wrap to whatever width it is given (pack it with fill='x')."""
        label.bind('<Configure>', lambda e: label.configure(wraplength=max(120, e.width - pad)))
        return label

    def _card(self, parent, title=None, pad=12):
        outer = self.ttk.Frame(parent, style='Card.TFrame', padding=pad)
        if title:
            self.ttk.Label(outer, text=title, style='CardHead.TLabel').pack(anchor='w', pady=(0, 6))
        return outer

    def _header(self, root):
        ttk = self.ttk
        h = ttk.Frame(root, style='App.TFrame', padding=(14, 10, 14, 8)); h.pack(fill='x')
        ttk.Label(h, text='rCRP · QAOA Suite', style='Title.TLabel').pack(side='left')
        ttk.Label(h, text='   Container relocation on exact Galle CRP-I encodings · simulation, noise models and IBM Quantum',
                  style='Sub.TLabel').pack(side='left', pady=(6, 0))
        self.chip = ttk.Label(h, text='No bay selected', style='Sub.TLabel'); self.chip.pack(side='right', pady=(6, 0))

    # ================================================================== sidebar
    def _sidebar(self, outer):
        tk, ttk = self.tk, self.ttk
        actions = ttk.Frame(outer, style='Card.TFrame', padding=12); actions.pack(side='bottom', fill='x', pady=(8, 0))
        holder = ttk.Frame(outer, style='App.TFrame'); holder.pack(side='top', fill='both', expand=True)
        sc = tk.Canvas(holder, highlightthickness=0, background=PALETTE['bg'], width=430)
        bar = ttk.Scrollbar(holder, orient='vertical', command=sc.yview); sc.configure(yscrollcommand=bar.set)
        bar.pack(side='right', fill='y'); sc.pack(side='left', fill='both', expand=True)
        inner = ttk.Frame(sc, style='App.TFrame'); sc.create_window((0, 0), window=inner, anchor='nw')
        inner.bind('<Configure>', lambda e: (sc.configure(scrollregion=sc.bbox('all')), sc.configure(width=inner.winfo_reqwidth())))
        self._wheel(sc)
        self._bay_card(inner); self._settings_card(inner); self._actions(actions)

    def _wheel(self, canvas):
        def scroll(e):
            if not str(e.widget).startswith(str(canvas)):
                return
            if getattr(e, 'num', None) in (4, 5):
                canvas.yview_scroll(-1 if e.num == 4 else 1, 'units')
            else:
                canvas.yview_scroll(-1 if e.delta > 0 else 1, 'units')
        for seq in ('<MouseWheel>', '<Button-4>', '<Button-5>'):
            canvas.bind_all(seq, scroll, add='+')

    def _bay_card(self, parent):
        tk, ttk = self.tk, self.ttk
        c = self._card(parent, '1 · Bay'); c.pack(fill='x', pady=(0, 8))
        self.src_tabs = ttk.Notebook(c, style='Inner.TNotebook'); self.src_tabs.pack(fill='x')
        lib = ttk.Frame(self.src_tabs, style='Card.TFrame', padding=(0, 8, 0, 0)); self.src_tabs.add(lib, text='Benchmark library')
        cus = ttk.Frame(self.src_tabs, style='Card.TFrame', padding=(0, 8, 0, 0)); self.src_tabs.add(cus, text='Custom / random bay')
        self.src_tabs.bind('<<NotebookTabChanged>>', lambda e: self._source_changed())
        row = ttk.Frame(lib, style='Card.TFrame'); row.pack(fill='x')
        ttk.Label(row, text='Family', style='Card.TLabel').pack(side='left')
        self.family = tk.StringVar(value='All')
        self.family_box = ttk.Combobox(row, textvariable=self.family, width=8, state='readonly')
        self.family_box.pack(side='left', padx=(4, 10)); self.family_box.bind('<<ComboboxSelected>>', lambda e: self.fill_list())
        ttk.Label(row, text='Search', style='Card.TLabel').pack(side='left')
        self.search = tk.StringVar(); ttk.Entry(row, textvariable=self.search, width=10).pack(side='left', padx=4)
        self.search.trace_add('write', lambda *a: self.fill_list())
        ttk.Button(row, text='Open folder…', command=self.browse).pack(side='right')
        cols = ('C', 'S', 'T', 'ref')
        self.tree = ttk.Treeview(lib, columns=cols, show='tree headings', height=7, selectmode='browse')
        self.tree.heading('#0', text='Bay'); self.tree.column('#0', width=112)
        for col, t, w in zip(cols, ('Boxes', 'Stacks', 'Height', 'Published'), (58, 56, 58, 76)):
            self.tree.heading(col, text=t); self.tree.column(col, width=w, anchor='e')
        self.tree.pack(fill='x', pady=(8, 0)); self.tree.bind('<<TreeviewSelect>>', lambda e: self.on_select())
        ttk.Label(cus, text='One stack per line, bottom → top. Use - for an empty stack.', style='CardMuted.TLabel').pack(anchor='w')
        self.bay_text = tk.Text(cus, height=5, width=36, font=self.f_mono, relief='solid', borderwidth=1)
        self.bay_text.pack(fill='x', pady=4); self.bay_text.insert('1.0', '1 3\n4 5\n2')
        r2 = ttk.Frame(cus, style='Card.TFrame'); r2.pack(fill='x', pady=2)
        ttk.Label(r2, text='Capacity', style='Card.TLabel').pack(side='left')
        self.cap = tk.IntVar(value=3); ttk.Spinbox(r2, from_=1, to=20, textvariable=self.cap, width=4).pack(side='left', padx=(4, 10))
        ttk.Button(r2, text='Use this bay', command=self.show_custom).pack(side='left')
        ttk.Button(r2, text='Load file…', command=self.load_file).pack(side='left', padx=6)
        r3 = ttk.Frame(cus, style='Card.TFrame'); r3.pack(fill='x', pady=(6, 0))
        ttk.Label(r3, text='Random:', style='CardBold.TLabel').pack(side='left', padx=(0, 6))
        self.gS, self.gT, self.gC, self.gseed = tk.IntVar(value=3), tk.IntVar(value=4), tk.IntVar(value=6), tk.IntVar(value=1)
        for lab, var, hi in (('stacks', self.gS, 12), ('height', self.gT, 12), ('boxes', self.gC, 60), ('seed', self.gseed, 10 ** 6)):
            ttk.Label(r3, text=lab, style='CardMuted.TLabel').pack(side='left')
            ttk.Spinbox(r3, from_=1, to=hi, textvariable=var, width=4).pack(side='left', padx=(2, 6))
        ttk.Button(cus, text='Generate random bay', command=self.random_custom).pack(anchor='w', pady=(6, 0))
        self.inst_info = self._flow(ttk.Label(c, text='Pick a bay from the list.', style='CardMuted.TLabel', justify='left'))
        self.inst_info.pack(fill='x', pady=(8, 0))
        self.fit = self._flow(ttk.Label(c, text='', style='Card.TLabel', justify='left')); self.fit.pack(fill='x', pady=(4, 0))

    def _settings_card(self, parent):
        tk, ttk = self.tk, self.ttk
        c = self._card(parent, '2 · Settings'); c.pack(fill='x')
        self.method = tk.StringVar(value=METHODS['predicate']); self.reduction = tk.StringVar(value=next(iter(REDUCTIONS)))
        self.angles = tk.StringVar(value=ANGLE_MODES['transfer']); self.backend = tk.StringVar(value=BACKENDS['ideal'])
        self.synthesis = tk.StringVar(value='pauli')
        self.depth = tk.IntVar(value=2); self.shots = tk.IntVar(value=1024); self.jobs = tk.IntVar(value=40)
        self.seed = tk.IntVar(value=0); self.maxq = tk.IntVar(value=22)
        self.p2 = tk.DoubleVar(value=0.003); self.ro = tk.DoubleVar(value=0.01); self.hist = tk.IntVar(value=200)
        self.baselines = tk.BooleanVar(value=True); self.milp = tk.BooleanVar(value=False)
        g = ttk.Frame(c, style='Card.TFrame'); g.pack(fill='x'); g.columnconfigure(1, weight=1); g.columnconfigure(3, weight=1)
        r = [0]

        def section(text):
            ttk.Label(g, text=text.upper(), style='Section.TLabel').grid(row=r[0], column=0, columnspan=4, sticky='w', pady=(8 if r[0] else 0, 2)); r[0] += 1

        def wide(label, widget):
            ttk.Label(g, text=label, style='Card.TLabel').grid(row=r[0], column=0, sticky='w', pady=2, padx=(0, 8))
            widget.grid(row=r[0], column=1, columnspan=3, sticky='ew', pady=2); r[0] += 1

        def pair(l1, w1, l2=None, w2=None):
            ttk.Label(g, text=l1, style='Card.TLabel').grid(row=r[0], column=0, sticky='w', pady=2, padx=(0, 8)); w1.grid(row=r[0], column=1, sticky='w', pady=2)
            if l2:
                ttk.Label(g, text=l2, style='Card.TLabel').grid(row=r[0], column=2, sticky='w', pady=2, padx=(12, 8)); w2.grid(row=r[0], column=3, sticky='w', pady=2)
            r[0] += 1
        combo = lambda var, vals, w=30: ttk.Combobox(g, textvariable=var, values=vals, state='readonly', width=w)
        spin = lambda var, a, b, inc=1: ttk.Spinbox(g, from_=a, to=b, increment=inc, textvariable=var, width=8)
        section('Model')
        wide('Encoding', combo(self.method, list(METHODS.values())))
        wide('Variable reduction', combo(self.reduction, list(REDUCTIONS)))
        pair('Circuit synthesis', combo(self.synthesis, ['pauli', 'mcp'], 8))
        section('QAOA')
        wide('Angles', combo(self.angles, list(ANGLE_MODES.values())))
        pair('Depth p', spin(self.depth, 1, 6), 'Seed', spin(self.seed, 0, 10 ** 6))
        pair('Shots per job', spin(self.shots, 16, 100000, 256), 'Jobs', spin(self.jobs, 1, 500))
        section('Simulator')
        wide('Backend', combo(self.backend, list(BACKENDS.values())))
        self.noise_widgets = [spin(self.p2, 0, 0.2, 0.001), spin(self.ro, 0, 0.2, 0.005), spin(self.hist, 1, 5000, 50)]
        pair('Max qubits', spin(self.maxq, 4, 30), '2-qubit error', self.noise_widgets[0])
        pair('Readout error', self.noise_widgets[1], 'Histories', self.noise_widgets[2])
        section('Compare with')
        ttk.Checkbutton(g, text='Greedy, exact search (≤10 containers), annealing, random', variable=self.baselines,
                        style='Card.TCheckbutton').grid(row=r[0], column=0, columnspan=4, sticky='w'); r[0] += 1
        ttk.Checkbutton(g, text="Galle's CRP-I MILP (SciPy HiGHS, up to 60 s)", variable=self.milp,
                        style='Card.TCheckbutton').grid(row=r[0], column=0, columnspan=4, sticky='w'); r[0] += 1
        ttk.Label(c, text='Samples = shots × jobs. Memory doubles with every qubit. "Strong" reduction is exact: '
                          'it removes only variables the constraints force, so no legal plan is lost.',
                  style='CardMuted.TLabel', wraplength=400, justify='left').pack(anchor='w', pady=(8, 0))
        for var in (self.method, self.reduction, self.maxq):
            var.trace_add('write', lambda *a: self.refresh_size())
        self.backend.trace_add('write', lambda *a: self._toggle_noise())

    def _toggle_noise(self):
        noisy_ = self.backend.get() in (BACKENDS['global'], BACKENDS['gate_level'])
        for w in self.noise_widgets[:2]:
            w.state(['!disabled'] if noisy_ else ['disabled'])
        self.noise_widgets[2].state(['!disabled'] if self.backend.get() == BACKENDS['gate_level'] else ['disabled'])

    def _actions(self, f):
        ttk = self.ttk
        b = ttk.Frame(f, style='Card.TFrame'); b.pack(fill='x')
        self.run_btn = ttk.Button(b, text='▶  Run', style='Accent.TButton', command=self.start); self.run_btn.pack(side='left')
        self.stop_btn = ttk.Button(b, text='Stop', command=self.stop, state='disabled'); self.stop_btn.pack(side='left', padx=6)
        ttk.Button(b, text='Export model…', command=self.export).pack(side='right')
        ttk.Button(b, text='Save results…', command=self.save).pack(side='right', padx=6)
        self.progress = ttk.Progressbar(f, mode='indeterminate'); self.progress.pack(fill='x', pady=(10, 2))
        self.status = self._flow(ttk.Label(f, text='Ready', style='CardMuted.TLabel')); self.status.pack(fill='x')

    # ================================================================== results area
    def _results(self, main):
        ttk = self.ttk
        self.tabs = ttk.Notebook(main); self.tabs.pack(fill='both', expand=True)
        self.tab = {}
        for key, title, build in (('overview', 'Overview', self._tab_overview), ('plan', 'Plan', self._tab_plan),
                                  ('compare', 'Compare', self._tab_compare), ('resources', 'Resources', self._tab_resources),
                                  ('ibm', 'IBM Quantum', self._tab_ibm), ('selftest', 'Self-test', self._tab_selftest),
                                  ('log', 'Log', self._tab_log)):
            fr = ttk.Frame(self.tabs, style='Card.TFrame', padding=14); self.tabs.add(fr, text=title); self.tab[key] = fr; build(fr)

    def _text(self, parent, height=12):
        from tkinter.scrolledtext import ScrolledText
        return ScrolledText(parent, wrap='word', height=height, font=self.f_mono, relief='flat',
                            background='#FBFCFD', borderwidth=0, padx=10, pady=8)

    def _tab_overview(self, f):
        ttk = self.ttk
        self.ov_title = ttk.Label(f, text='No results yet', style='CardHead.TLabel'); self.ov_title.pack(anchor='w')
        self.ov_sub = self._flow(ttk.Label(f, text='Choose a bay and settings on the left, then press Run.', style='CardMuted.TLabel'))
        self.ov_sub.pack(fill='x', pady=(2, 8))
        self.ov_banner = self._flow(ttk.Label(f, text='', style='Warn.TLabel', justify='left')); self.ov_banner.pack(fill='x')
        tiles = ttk.Frame(f, style='Card.TFrame'); tiles.pack(fill='x', pady=(6, 10)); self.tiles = {}
        for i, (key, cap) in enumerate((('best', 'Best QAOA plan'), ('opt', 'Optimum'), ('legal', 'Legal-plan rate'), ('popt', 'P(optimal plan)'))):
            t = ttk.Frame(tiles, style='Tile.TFrame', padding=(14, 10)); t.grid(row=0, column=i, sticky='nsew', padx=(0 if i == 0 else 8, 0))
            tiles.columnconfigure(i, weight=1, uniform='tile')
            ttk.Label(t, text=cap, style='TileCap.TLabel').pack(anchor='w')
            v = ttk.Label(t, text='—', style='TileVal.TLabel'); v.pack(anchor='w')
            d = self._flow(ttk.Label(t, text='', style='TileDet.TLabel', justify='left')); d.pack(fill='x')
            self.tiles[key] = (v, d)
        ttk.Label(f, text='Full report', style='CardBold.TLabel').pack(anchor='w')
        self.summary = self._text(f, 16); self.summary.pack(fill='both', expand=True, pady=(4, 0))
        self.summary.insert('1.0', 'Fixed in this merged version:' + FIXES)

    def _tab_plan(self, f):
        tk, ttk = self.tk, self.ttk
        pane = ttk.PanedWindow(f, orient='horizontal'); pane.pack(fill='both', expand=True)
        left = ttk.Frame(pane, style='Card.TFrame'); right = ttk.Frame(pane, style='Card.TFrame', padding=(12, 0, 0, 0))
        pane.add(left, weight=1); pane.add(right, weight=1)
        top = ttk.Frame(left, style='Card.TFrame'); top.pack(fill='x')
        ttk.Label(top, text='Plan', style='CardBold.TLabel').pack(side='left')
        self.plan_choice = tk.StringVar(value='')
        self.plan_box = ttk.Combobox(top, textvariable=self.plan_choice, state='readonly', width=26)
        self.plan_box.pack(side='left', padx=8); self.plan_box.bind('<<ComboboxSelected>>', lambda e: self.show_plan())
        self.plan_info = self._flow(ttk.Label(left, text='Run something to see its crane moves.', style='CardMuted.TLabel')); self.plan_info.pack(fill='x', pady=(6, 4))
        cols = ('step', 'action', 'container', 'from', 'to')
        self.moves = ttk.Treeview(left, columns=cols, show='headings')
        for col, w in zip(cols, (50, 90, 80, 60, 60)):
            self.moves.heading(col, text=col.capitalize()); self.moves.column(col, width=w, anchor='center')
        self.moves.tag_configure('reloc', background='#FCEFE7')
        self.moves.pack(fill='both', expand=True); self.moves.bind('<<TreeviewSelect>>', lambda e: self.jump_to_move())
        self.canvas = tk.Canvas(right, background='white', highlightthickness=1, highlightbackground=PALETTE['line'])
        self.canvas.pack(fill='both', expand=True)
        ctl = ttk.Frame(right, style='Card.TFrame'); ctl.pack(fill='x', pady=(8, 0))
        ttk.Button(ctl, text='◀', width=3, command=lambda: self.step(-1)).pack(side='left')
        ttk.Button(ctl, text='▶', width=3, command=lambda: self.step(1)).pack(side='left', padx=4)
        self.pos = tk.IntVar(value=0)
        self.slider = ttk.Scale(ctl, from_=0, to=0, orient='horizontal', command=lambda x: self.draw(int(float(x))))
        self.slider.pack(side='left', fill='x', expand=True, padx=8)
        self.caption = ttk.Label(right, text='', style='CardBold.TLabel'); self.caption.pack(anchor='w', pady=(6, 0))
        self.canvas.bind('<Configure>', lambda e: self.draw(self.pos.get()))

    def _tab_compare(self, f):
        tk, ttk = self.tk, self.ttk
        ttk.Label(f, text='Same sample budget for QAOA, random guessing and annealing. Exact methods give the reference optimum.',
                  style='CardMuted.TLabel').pack(anchor='w', pady=(0, 6))
        cols = ('method', 'reloc', 'gap', 'legal', 'note')
        self.cmp = ttk.Treeview(f, columns=cols, show='headings', height=7)
        for col, t, w in zip(cols, ('Method', 'Relocations', 'Gap', 'Legal-plan rate', 'Note'), (250, 95, 60, 120, 420)):
            self.cmp.heading(col, text=t); self.cmp.column(col, width=w, anchor='w' if col in ('method', 'note') else 'e')
        self.cmp.pack(fill='x')
        ttk.Label(f, text='Where the samples landed', style='CardBold.TLabel').pack(anchor='w', pady=(12, 4))
        self.dist = tk.Canvas(f, background='white', highlightthickness=1, highlightbackground=PALETTE['line'])
        self.dist.pack(fill='both', expand=True); self.dist.bind('<Configure>', lambda e: self.draw_distribution())

    def _tab_resources(self, f):
        ttk = self.ttk
        row = ttk.Frame(f, style='Card.TFrame'); row.pack(fill='x')
        ttk.Button(row, text='Compare encodings for the selected bay', style='Accent.TButton', command=self.start_resources).pack(side='left')
        ttk.Label(row, text='  Builds every model with both reductions (no simulation). Uses depth p from Settings.',
                  style='CardMuted.TLabel').pack(side='left')
        cols = ('method', 'qubits', 'measured', 'decision', 'extra', 'cx', 'note')
        self.res = ttk.Treeview(f, columns=cols, show='headings', height=12)
        for col, t, w in zip(cols, ('Encoding', 'Total qubits', 'Measured', 'Decision', 'Extra', 'Logical CX', 'Note'),
                             (290, 95, 80, 75, 60, 95, 420)):
            self.res.heading(col, text=t); self.res.column(col, width=w, anchor='w' if col in ('method', 'note') else 'e')
        self.res.pack(fill='both', expand=True, pady=10)
        self._flow(ttk.Label(f, text='Logical CX = two-qubit gates before routing (all-to-all connectivity); real devices need more. '
                                     'The coherent-oracle count is an unoptimised 6-CX-per-Toffoli estimate including uncomputation.',
                             style='CardMuted.TLabel')).pack(fill='x')

    def _tab_ibm(self, f):
        tk, ttk = self.tk, self.ttk
        ttk.Label(f, text='Compile → inspect → rehearse → run on IBM Quantum', style='CardHead.TLabel').pack(anchor='w')
        self._flow(ttk.Label(f, text='Uses the bay chosen on the left. Steps A–B are free and offline. Steps 1–2 need a saved IBM account '
                                     '(see the IBM manual) and use your QPU time only when you press Submit, never above the cap.',
                             style='CardMuted.TLabel', justify='left')).pack(fill='x', pady=(2, 10))
        top = ttk.Frame(f, style='Card.TFrame'); top.pack(fill='x')
        top.columnconfigure(0, weight=1, uniform='ibm'); top.columnconfigure(1, weight=1, uniform='ibm')
        form = ttk.Frame(top, style='Tile.TFrame', padding=12); form.grid(row=0, column=0, sticky='nsew')
        act = ttk.Frame(top, style='Tile.TFrame', padding=12); act.grid(row=0, column=1, sticky='nsew', padx=(10, 0))
        form.columnconfigure(1, weight=1)
        self.hw = {k: tk.StringVar(value=v) for k, v in dict(method=next(iter(HW_METHODS)), reduction=next(iter(REDUCTIONS)),
                                                              depth='1', shots='1024', evaluations='40', seed='0',
                                                              backend='auto', budget='60').items()}
        self.hw_fixed = tk.BooleanVar(value=True); self.hw_single = tk.BooleanVar(value=True); self.hw_synth = tk.StringVar(value='pauli')
        ttk.Label(form, text='SETTINGS', style='TileSec.TLabel').grid(row=0, column=0, columnspan=4, sticky='w', pady=(0, 4))
        cb = lambda var, vals, w: ttk.Combobox(form, textvariable=var, values=vals, state='readonly', width=w)
        en = lambda key, w=8: ttk.Entry(form, textvariable=self.hw[key], width=w)
        lab = lambda text, r, c: ttk.Label(form, text=text, style='TileCap.TLabel').grid(row=r, column=c, sticky='w', pady=2, padx=(0 if c == 0 else 12, 8))
        lab('Encoding', 1, 0); cb(self.hw['method'], list(HW_METHODS), 28).grid(row=1, column=1, columnspan=3, sticky='ew', pady=2)
        lab('Reduction', 2, 0); cb(self.hw['reduction'], list(REDUCTIONS), 28).grid(row=2, column=1, columnspan=3, sticky='ew', pady=2)
        lab('Synthesis', 3, 0); cb(self.hw_synth, ['pauli', 'mcp'], 7).grid(row=3, column=1, sticky='w', pady=2)
        lab('Depth p', 3, 2); en('depth').grid(row=3, column=3, sticky='w', pady=2)
        lab('Shots per job', 4, 0); en('shots').grid(row=4, column=1, sticky='w', pady=2)
        lab('Jobs', 4, 2); en('evaluations').grid(row=4, column=3, sticky='w', pady=2)
        lab('Seed', 5, 0); en('seed').grid(row=5, column=1, sticky='w', pady=2)
        lab('QPU-s cap', 5, 2); en('budget').grid(row=5, column=3, sticky='w', pady=2)
        lab('IBM backend', 6, 0); en('backend', 16).grid(row=6, column=1, columnspan=3, sticky='w', pady=2)
        ttk.Label(form, text='a device name such as ibm_brisbane, or auto = least busy', style='TileDet.TLabel').grid(row=7, column=1, columnspan=3, sticky='w')
        ttk.Checkbutton(form, text='Fixed transferred angles (no optimiser)', variable=self.hw_fixed,
                        style='Tile.TCheckbutton').grid(row=8, column=0, columnspan=4, sticky='w', pady=(6, 0))
        ttk.Checkbutton(form, text='Send all shots as ONE job (saves free QPU time)', variable=self.hw_single,
                        style='Tile.TCheckbutton').grid(row=9, column=0, columnspan=4, sticky='w')
        self.hw_est = self._flow(ttk.Label(form, text='', style='TileDet.TLabel', justify='left'))
        self.hw_est.grid(row=10, column=0, columnspan=4, sticky='ew', pady=(8, 0))
        for v in list(self.hw.values()) + [self.hw_fixed, self.hw_single]:
            v.trace_add('write', lambda *a: self._hw_estimate())
        self._hw_estimate()
        act.columnconfigure(0, weight=1); act.columnconfigure(1, weight=1)
        ttk.Label(act, text='OFFLINE · FREE', style='TileSec.TLabel').grid(row=0, column=0, columnspan=2, sticky='w', pady=(0, 4))
        for i, (text, mode) in enumerate((('A. Resource report', 'report'), ('Export circuits', 'export'),
                                          ('B. Ideal check', 'local'), ('B. Rehearse on fake IBM', 'rehearse'))):
            ttk.Button(act, text=text, command=lambda m=mode: self.hw_run(m)).grid(row=1 + i // 2, column=i % 2, sticky='ew', padx=(0, 6), pady=2)
        ttk.Label(act, text='IBM ACCOUNT · USES QPU TIME ON SUBMIT', style='TileSec.TLabel').grid(row=3, column=0, columnspan=2, sticky='w', pady=(12, 4))
        ttk.Button(act, text='1. Compile for IBM', command=lambda: self.hw_run('prepare')).grid(row=4, column=0, sticky='ew', padx=(0, 6), pady=2)
        ttk.Button(act, text='2. Submit capped run', style='Accent.TButton', command=lambda: self.hw_run('submit')).grid(row=4, column=1, sticky='ew', padx=(0, 6), pady=2)
        ttk.Button(act, text='Stop local process', command=self.hw_stop).grid(row=5, column=0, sticky='ew', padx=(0, 6), pady=2)
        self.hw_state = tk.StringVar(value='Ready. No hardware jobs submitted.')
        self.hw_acc = tk.StringVar(value='Accuracy: N/A — only computed after a completed measured plan.')
        self._flow(ttk.Label(act, textvariable=self.hw_state, style='TileVal2.TLabel', justify='left')).grid(row=6, column=0, columnspan=2, sticky='ew', pady=(10, 0))
        self._flow(ttk.Label(act, textvariable=self.hw_acc, style='TileDet.TLabel', justify='left')).grid(row=7, column=0, columnspan=2, sticky='ew', pady=(2, 0))
        self._flow(ttk.Label(act, text='Stopping the local process does not cancel a job already on IBM (cancel it by job ID on the IBM '
                                       f'dashboard). Output folder: {RESULTS_DIR / "hardware"}', style='TileDet.TLabel',
                             justify='left')).grid(row=8, column=0, columnspan=2, sticky='ew', pady=(6, 0))
        pw = ttk.PanedWindow(f, orient='vertical'); pw.pack(fill='both', expand=True, pady=(10, 0))
        self.hw_log = self._text(pw, 10); pw.add(self.hw_log, weight=3)
        self.hw_moves = ttk.Treeview(pw, columns=('type', 'container', 'source', 'dest'), show='headings', height=5)
        for key, label in (('type', 'Action'), ('container', 'Container'), ('source', 'From stack'), ('dest', 'To stack / OUT')):
            self.hw_moves.heading(key, text=label)
        pw.add(self.hw_moves, weight=1)

    def _tab_selftest(self, f):
        tk, ttk = self.tk, self.ttk
        row = ttk.Frame(f, style='Card.TFrame'); row.pack(fill='x')
        self.quick = tk.BooleanVar(value=True)
        ttk.Button(row, text='Run self-test', style='Accent.TButton', command=self.start_selftest).pack(side='left')
        ttk.Checkbutton(row, text='Quick', variable=self.quick, style='Card.TCheckbutton').pack(side='left', padx=10)
        ttk.Label(row, text='Exactness of every encoding and of the strong reduction, the physical checker, simulators, '
                            'annealing and Qiskit circuits.', style='CardMuted.TLabel').pack(side='left')
        self.st_text = self._text(f, 20); self.st_text.pack(fill='both', expand=True, pady=(10, 0))

    def _tab_log(self, f):
        self.log = self._text(f, 20); self.log.pack(fill='both', expand=True)

    # ================================================================== bay selection
    def browse(self):
        from tkinter import filedialog
        d = filedialog.askdirectory(title='Folder of group-4 .txt files', initialdir=str(Path.home()))
        if d:
            rows = list_instance_folder(d)
            if not rows:
                self.inst_info.config(text=f'No group-4 .txt files in {d}.'); return
            self.selected_key = None; self.instances = rows; self.fill_list()
            self.inst_info.config(text=f'{len(rows)} files from {d}. Click a bay to choose it.')

    def fill_list(self):
        fams = sorted({r['family'] for r in self.instances}, key=lambda s: [int(x) for x in s[4:].split('-')] if s.startswith('data') else [999])
        self.family_box.config(values=['All'] + fams)
        self.tree.delete(*self.tree.get_children())
        fam, s = self.family.get(), self.search.get().strip().lower()
        for r in self.instances:
            if (fam != 'All' and r['family'] != fam) or (s and s not in r['name'].lower()):
                continue
            ref = r.get('reference') or reference_for(r['name'])
            self.tree.insert('', 'end', iid=r.get('path', r['id']), text=r['name'],
                             values=(r['containers'], r['stacks'], r['capacity'], '' if not ref else ref['best_known']))
        if self.selected_key and self.tree.exists(self.selected_key):      # filtering must not lose the chosen bay
            self.tree.selection_set(self.selected_key); self.tree.see(self.selected_key)

    def _selected_row(self):
        sel = self.tree.selection()
        key = sel[0] if sel else self.selected_key
        return next((x for x in self.instances if x.get('path', x['id']) == key), None) if key else None

    def _row_bay(self, r):
        if 'stacks_bottom_to_top' in r:
            return tuple(tuple(s) for s in r['stacks_bottom_to_top']), r['capacity']
        return read_instance(r['path'], None, None)

    def on_select(self):
        sel = self.tree.selection()
        if sel:
            self.selected_key = sel[0]
        r = self._selected_row()
        if not r:
            return
        ref = r.get('reference') or reference_for(r['name'])
        txt = f"{r['name']}: {r['containers']} containers in {r['stacks']} stacks, capacity {r['capacity']}."
        if ref:
            txt += f" Published: {ref['best_known']} relocations ({'proven optimal' if ref['proven_optimal'] else 'best known'})."
        self.inst_info.config(text=txt); self.chip.config(text=f"Bay: {r['name']}")
        try:
            bay, cap = self._row_bay(r)
            self.states = [([list(s) for s in bay], 'Initial bay — press Run to see a plan')]; self.capacity = cap
            self.slider.config(to=0); self.draw(0)
        except Exception as e:
            self.inst_info.config(text=f'Cannot read {r["name"]}: {e}')
        self.refresh_size()

    def _source_changed(self):
        """Switching between library and custom bay: show what will actually be used."""
        if self.src_tabs.index('current') == 1:
            self.show_custom()
        elif self._selected_row():
            self.on_select()
        else:
            self.inst_info.config(text='Pick a bay from the list.'); self.chip.config(text='No bay selected'); self.refresh_size()

    def _custom_bay(self):
        bay = parse_bay_text(self.bay_text.get('1.0', 'end')); cap = int(self.cap.get())
        validate_instance(bay, cap)
        return bay, cap

    def show_custom(self):
        try:
            bay, cap = self._custom_bay()
        except Exception as e:
            self.inst_info.config(text=f'This bay is not valid: {e}'); return
        self.inst_info.config(text=f'Custom bay: {sum(map(len, bay))} containers in {len(bay)} stacks, capacity {cap}.')
        self.chip.config(text='Bay: custom')
        self.states = [([list(s) for s in bay], 'Custom bay')]; self.capacity = cap; self.slider.config(to=0); self.draw(0)
        self.refresh_size()

    def random_custom(self):
        try:
            bay = random_bay(int(self.gS.get()), int(self.gT.get()), int(self.gC.get()), int(self.gseed.get()))
        except Exception as e:
            self.inst_info.config(text=str(e)); return
        self.bay_text.delete('1.0', 'end'); self.bay_text.insert('1.0', '\n'.join(' '.join(map(str, s)) if s else '-' for s in bay))
        self.cap.set(int(self.gT.get())); self.show_custom()

    def load_file(self):
        from tkinter import filedialog
        f = filedialog.askopenfilename(title='Group-4 instance file', filetypes=[('Text', '*.txt'), ('All', '*')])
        if f:
            try:
                bay, cap = read_instance(f, None, None)
            except Exception as e:
                self.inst_info.config(text=f'Cannot read file: {e}'); return
            self.bay_text.delete('1.0', 'end'); self.bay_text.insert('1.0', '\n'.join(' '.join(map(str, s)) if s else '-' for s in bay))
            self.cap.set(cap); self.show_custom()

    def current_bay(self):
        """(name, bay, capacity, Config source fields) of the bay being used."""
        if self.src_tabs.index('current') == 1:
            bay, cap = self._custom_bay()
            return 'custom bay', bay, cap, dict(stacks=[list(s) for s in bay], capacity=cap, instance='custom bay')
        r = self._selected_row()
        if not r:
            raise ValueError('No bay is chosen yet. Click one row in the list so it is highlighted, then press Run '
                             '(or build a bay in the Custom / random bay tab).')
        bay, cap = self._row_bay(r)
        return r['name'], bay, cap, (dict(instance=r['id']) if 'stacks_bottom_to_top' in r else dict(path=r['path']))

    def refresh_size(self):
        """Background check: how many qubits does this bay need, and does it fit this computer?"""
        try:
            name, bay, cap, _ = self.current_bay()
            method = next(k for k, x in METHODS.items() if x == self.method.get())
            presolve = REDUCTIONS[self.reduction.get()]; maxq = int(self.maxq.get())
        except Exception:
            self.fit.config(text='', style='Card.TLabel'); return
        key = (bay, cap, method, presolve, maxq)
        self.size_gen += 1; gen = self.size_gen
        if key in self.size_cache:
            self._show_size(self.size_cache[key]); return
        self.fit.config(text='Checking size…', style='CardMuted.TLabel')

        def work():
            try:
                res = size_check(bay, cap, method, presolve, maxq)
            except Exception as e:
                res = dict(verdict='error', text=f'{type(e).__name__}: {e}')
            self.events.put(('size', (gen, key, res)))
        threading.Thread(target=work, daemon=True).start()

    def _show_size(self, res):
        style = {'fits': 'Good.TLabel', 'exact': 'Good.TLabel', 'too_big': 'Bad.TLabel'}.get(res['verdict'], 'Warn.TLabel')
        self.fit.config(text=('✓ ' if style == 'Good.TLabel' else '✗ ' if style == 'Bad.TLabel' else '! ') + res['text'], style=style)

    # ================================================================== running
    def config(self):
        name, bay, cap, src = self.current_bay()
        inv = lambda d, v: next(k for k, x in d.items() if x == v)
        return Config(method=inv(METHODS, self.method.get()), presolve=REDUCTIONS[self.reduction.get()], synthesis=self.synthesis.get(),
                      depth=int(self.depth.get()), shots=int(self.shots.get()), jobs=int(self.jobs.get()),
                      angles=inv(ANGLE_MODES, self.angles.get()), backend=inv(BACKENDS, self.backend.get()),
                      p2=float(self.p2.get()), readout=float(self.ro.get()), histories=int(self.hist.get()),
                      seed=int(self.seed.get()), baselines=bool(self.baselines.get()), milp=bool(self.milp.get()),
                      max_qubits=int(self.maxq.get()), **src)

    def _busy(self, on, text='Running…'):
        self.run_btn.state(['disabled'] if on else ['!disabled']); self.stop_btn.state(['!disabled'] if on else ['disabled'])
        if on:
            self._spin(True); self.status.config(text=text)
        else:
            self._spin(False)

    def _spin(self, on):
        if on:
            self.progress.configure(mode='indeterminate'); self.progress.start(12)
        else:
            self.progress.stop(); self.progress.configure(mode='determinate', value=0)

    def _spawn(self, kind, fn):
        if self.worker and self.worker.is_alive():
            from tkinter import messagebox
            messagebox.showinfo('Busy', 'A run is already in progress. Press Stop first.'); return False
        self.cancel = False

        def work():
            try:
                self.events.put((kind, fn()))
            except Cancelled:
                self.events.put(('cancelled', None))
            except Exception:
                self.events.put(('error', traceback.format_exc()))
        self.worker = threading.Thread(target=work, daemon=True); self.worker.start()
        return True

    def start(self):
        from tkinter import messagebox
        try:
            cfg = self.config()
        except Exception as e:
            messagebox.showwarning('Choose a bay', str(e)); return
        if cfg.angles == 'tune' and cfg.backend != 'ideal':
            messagebox.showinfo('Angles', 'Angles are tuned on the ideal simulator; the same angles are then run on the noisy simulator.')
        if cfg.backend == 'gate_level' and cfg.method == 'coherent':
            messagebox.showwarning('Simulator', 'Gate-level noise needs a direct Pauli circuit; the coherent oracle is not supported.'); return
        log = lambda s: self.events.put(('log', s))
        if self._spawn('done', lambda: run(cfg, log=log, cancelled=lambda: self.cancel)):
            self.log.delete('1.0', 'end'); self._busy(True)

    def start_resources(self):
        try:
            name, bay, cap, _ = self.current_bay()
        except Exception as e:
            self.status.config(text=str(e)); return
        depth = int(self.depth.get())
        if self._spawn('resources', lambda: (name, resource_report(bay, cap, depth, cancelled=lambda: self.cancel))):
            self._busy(True, f'Building every encoding for {name}…')

    def start_selftest(self):
        quick = bool(self.quick.get())      # read Tk state on the main thread
        say = lambda s: self.events.put(('st', s))
        if self._spawn('selftest', lambda: selftest(say=say, quick=quick, cancelled=lambda: self.cancel)):
            self.st_text.delete('1.0', 'end'); self._busy(True, 'Self-test running…')

    def stop(self):
        self.cancel = True; self.status.config(text='Stopping…')

    def poll(self):
        try:
            while True:
                kind, data = self.events.get_nowait()
                if kind == 'log':
                    self.log.insert('end', data + '\n'); self.log.see('end'); self.status.config(text=data[:100])
                elif kind == 'st':
                    self.st_text.insert('end', data + '\n'); self.st_text.see('end')
                elif kind == 'size':
                    gen, key, res = data; self.size_cache[key] = res
                    if gen == self.size_gen:
                        self._show_size(res)
                elif kind == 'hw_line':
                    self.hw_log.insert('end', data); self.hw_log.see('end')
                    if data.startswith('Results: '):
                        self.hw_latest = Path(data[9:].strip())
                    if data.startswith('Backend: '):
                        self.hw_resolved = data[9:].split(' (')[0].strip()
                elif kind == 'hw_done':
                    self.hw_finished(data)
                else:
                    self._busy(False)
                    if kind == 'done':
                        self.show(data); self.status.config(text=f"Finished: {data['status'].replace('_', ' ')}")
                    elif kind == 'resources':
                        self.fill_resources(*data); self.status.config(text='Resource comparison finished')
                    elif kind == 'selftest':
                        self.status.config(text=f'Self-test: {data[0]} passed, {data[1]} failed')
                    elif kind == 'cancelled':
                        self.status.config(text='Stopped')
                    else:
                        self.log.insert('end', data); self.status.config(text='Error — see the Log tab'); self.tabs.select(self.tab['log'])
        except queue.Empty:
            pass
        self.root.after(100, self.poll)

    # ================================================================== showing results
    def show(self, r):
        self.result = r
        c = r['config']
        self.ov_title.config(text=f"{r['instance']} · {len(r['stacks'])} stacks, capacity {r['capacity']}, {r['containers']} containers")
        sub = f"{METHODS[c['method']]} · {c.get('presolve', 'standard')} reduction · p={c['depth']} · {c['shots']}×{c['jobs']} samples · {BACKENDS[c['backend']]}"
        if r.get('resources'):
            sub += f" · {r['resources']['qubits']} qubits, {r['resources']['logical_cx']:,} logical CX"
        self.ov_sub.config(text=sub)
        self.ov_banner.config(text='' if r['status'] == 'ok' else f"{r['status'].replace('_', ' ').upper()}: {r.get('message', '')}",
                              style='Good.TLabel' if r['status'] in ('solved_by_lemma1', 'solved_by_presolve') else 'Warn.TLabel')
        q = r.get('qaoa'); known = r.get('known_optimum'); e = (r.get('exact_probabilities') or {})

        def tile(k, v, d=''):
            self.tiles[k][0].config(text=v); self.tiles[k][1].config(text=d)
        if q and q.get('best'):
            b = q['best']; tile('best', f"{b['relocations']} reloc.", (f"gap {r['gap']:+d} · " if r.get('gap') is not None else '') + f"seen {b['count']}×")
        else:
            tile('best', '—', 'no legal plan sampled' if q else 'no QAOA run')
        src = (r.get('exact') or {}).get('source') or ('Galle MILP' if r.get('milp') else ('published value' if r.get('reference') else r.get('known_optimum_source', '')))
        tile('opt', '—' if known is None else f'{known} reloc.', src)
        if q:
            tile('legal', f"{q['legal_fraction']:.2%}", f"random {r['uniform']['legal_fraction']:.2%}" + (f" · {q['times_random']:.1f}× random" if q.get('times_random') else ''))
        else:
            tile('legal', '—')
        if e.get('ideal'):
            noisy_ = e.get('model') and c['backend'] != 'ideal'; m = e['model'] if noisy_ else e['ideal']
            tile('popt', f"{m['P_replay_optimal']:.2%}", f"exact, {'noisy' if noisy_ else 'ideal'} · random {e['uniform']['P_replay_optimal']:.2%}")
        else:
            tile('popt', '—')
        self.summary.delete('1.0', 'end'); self.summary.insert('1.0', summary_text(r))
        plans = {}
        if q and q.get('best'):
            plans['QAOA best'] = q['best']
        if r.get('presolve_plan'):
            plans['Exact plan (no QAOA needed)'] = r['presolve_plan']
        for key, label in (('exact', 'Exact optimum'), ('milp', 'Galle MILP'), ('greedy', 'Greedy rule'), ('annealing', 'Simulated annealing')):
            if r.get(key) and r[key].get('moves'):
                plans[label] = r[key]
        if r.get('uniform') and r['uniform'].get('best'):
            plans['Random guessing best'] = r['uniform']['best']
        self.plans = plans
        self.plan_box.config(values=list(plans)); self.plan_choice.set(next(iter(plans), ''))
        self.show_plan(); self.fill_comparison(r); self.draw_distribution(); self.tabs.select(self.tab['overview'])

    def show_plan(self):
        self.moves.delete(*self.moves.get_children())
        p = self.plans.get(self.plan_choice.get()) if self.result else None
        if not p:
            self.plan_info.config(text='No plan to show.'); return
        self.plan_info.config(text=f"{p['relocations']} relocations · {len(p['moves'])} crane actions · select a row to jump there")
        for i, mv in enumerate(p['moves'], 1):
            rel = mv['type'] == 'relocate'
            self.moves.insert('', 'end', iid=str(i), tags=('reloc',) if rel else (),
                              values=(i, 'Relocate' if rel else 'Retrieve', mv['container'], f"S{mv['source']}", f"S{mv['destination']}" if rel else '—'))
        self.states = replay(self.result['stacks'], p['moves']); self.capacity = self.result['capacity']
        self.slider.config(to=len(self.states) - 1); self.slider.set(0); self.draw(0)

    def jump_to_move(self):
        sel = self.moves.selection()
        if sel:
            k = int(sel[0]); self.slider.set(k); self.draw(k)

    def step(self, d):
        k = max(0, min(len(self.states) - 1, self.pos.get() + d)); self.slider.set(k); self.draw(k)

    def draw(self, k):
        P = PALETTE; cv = self.canvas; cv.delete('all')
        if not self.states:
            return
        k = max(0, min(k, len(self.states) - 1)); self.pos.set(k)
        stacks, cap = self.states[k]; self.caption.config(text=cap)
        moved = None
        if k > 0 and self.result:
            p = self.plans.get(self.plan_choice.get())
            if p and k - 1 < len(p['moves']):
                moved = p['moves'][k - 1]['container']
        remaining = [c for s in stacks for c in s]; target = min(remaining) if remaining else None
        W, H = max(cv.winfo_width(), 300), max(cv.winfo_height(), 240)
        n, T = len(stacks), max(self.capacity, max((len(s) for s in stacks), default=1))
        bw = min(72, (W - 80) / max(n, 1) - 12); bh = min(44, (H - 100) / max(T, 1) - 5)
        x0 = (W - n * (bw + 12)) / 2; base = H - 44
        cv.create_line(x0 - 12, base + 3, x0 + n * (bw + 12), base + 3, width=3, fill=P['ink'])
        for i, s in enumerate(stacks):
            x = x0 + i * (bw + 12)
            for t in range(T):
                y = base - (t + 1) * (bh + 5)
                cv.create_rectangle(x, y, x + bw, y + bh, outline=P['grid'], dash=(3, 3))
            for t, c in enumerate(s):
                y = base - (t + 1) * (bh + 5)
                fill = P['moved'] if c == moved else (P['target'] if c == target else P['box'])
                cv.create_rectangle(x, y, x + bw, y + bh, fill=fill, outline='')
                cv.create_text(x + bw / 2, y + bh / 2, text=str(c), fill='white', font=self.f_box)
            cv.create_text(x + bw / 2, base + 18, text=f'S{i + 1}', fill=P['muted'], font=self.f_sub)
        lx = 14
        for col, lab in ((P['target'], 'next to retrieve'), (P['moved'], 'just moved'), (P['box'], 'other containers')):
            cv.create_rectangle(lx, 12, lx + 12, 24, fill=col, outline='')
            cv.create_text(lx + 18, 18, anchor='w', text=lab, fill=P['muted'], font=self.f_sub); lx += 34 + self.f_sub.measure(lab)

    def fill_comparison(self, r):
        self.cmp.delete(*self.cmp.get_children())
        known = r.get('known_optimum')
        gap = lambda x: '' if known is None or x is None else f'{x - known:+d}'
        q = r.get('qaoa')
        if q:
            b = q['best']
            self.cmp.insert('', 'end', values=('QAOA', b['relocations'] if b else '—', gap(b['relocations'] if b else None),
                                               f"{q['legal_fraction']:.2%}", f"{q['times_random']:.1f}× random" if q.get('times_random') else ''))
            u = r['uniform']; ub = u['best']
            self.cmp.insert('', 'end', values=('Random guessing (same samples)', ub['relocations'] if ub else '—', gap(ub['relocations'] if ub else None),
                                               f"{u['legal_fraction']:.2%}", 'the control QAOA must beat'))
        if r.get('annealing'):
            a = r['annealing']
            self.cmp.insert('', 'end', values=('Simulated annealing (corrected)', a['relocations'] if a['relocations'] is not None else '—',
                                               gap(a['relocations']), f"{a['legal_fraction']:.2%}", f"{a['evaluations']:,} candidate evaluations"))
        if r.get('greedy'):
            g = r['greedy']; self.cmp.insert('', 'end', values=('Greedy rule', g['relocations'], gap(g['relocations']), '', 'classical, instant'))
        if r.get('milp'):
            mm = r['milp']; self.cmp.insert('', 'end', values=('Galle CRP-I MILP', mm['relocations'], gap(mm['relocations']), '', mm['source']))
        if r.get('exact'):
            self.cmp.insert('', 'end', values=('Exact optimum', r['exact']['relocations'], '+0', '', r['exact']['source']))
        if r.get('reference'):
            ref = r['reference']; self.cmp.insert('', 'end', values=('Published value', ref['best_known'], gap(ref['best_known']), '',
                                                                      'proven optimal' if ref['proven_optimal'] else 'best known'))

    def draw_distribution(self):
        P = PALETTE; cv = self.dist; cv.delete('all'); r = self.result
        W, H = max(cv.winfo_width(), 400), max(cv.winfo_height(), 240)
        if not r or not r.get('qaoa'):
            cv.create_text(W / 2, H / 2, text='Run QAOA to see how its samples spread over plan costs.', fill=P['muted'], font=self.f_bold)
            return
        series = [('QAOA', r['qaoa'], P['qaoa']), ('Random guessing', r['uniform'], P['random'])]
        costs = sorted({k for _, s, _ in series for k in s['cost_histogram']})
        cv.create_text(16, 16, anchor='w', fill=P['ink'], font=self.f_bold, text='Share of ALL samples that were legal plans of each cost (the rest were illegal)')
        if not costs:
            cv.create_text(W / 2, H / 2, text='No legal plans were sampled.', fill=P['bad'], font=self.f_bold); return
        top = max(max(s['cost_histogram'].values(), default=0) for _, s, _ in series) or 1
        left, bottom, height = 50, H - 64, H - 130; gw = (W - left - 30) / len(costs); bw = min(46, gw / 3)
        cv.create_line(left, bottom, W - 20, bottom, fill=P['ink'])
        known = r.get('known_optimum')
        for i, k in enumerate(costs):
            x = left + i * gw + gw / 2
            for j, (lab, s, col) in enumerate(series):
                v = s['cost_histogram'].get(k, 0); h = height * v / top; xx = x + (j - 0.5) * bw * 1.15
                cv.create_rectangle(xx - bw / 2, bottom - h, xx + bw / 2, bottom, fill=col, outline='')
                if v:
                    cv.create_text(xx, bottom - h - 9, text=f'{v:.2%}', fill=P['muted'], font=self.f_sub)
            cv.create_text(x, bottom + 16, text=f'{k} relocations' + ('  (optimal)' if k == known else ''),
                           fill=P['accent'] if k == known else P['ink'], font=self.f_bold if k == known else self.f_sub)
        for j, (lab, s, col) in enumerate(series):
            x = left + j * 260; y = H - 22
            cv.create_rectangle(x, y - 7, x + 14, y + 7, fill=col, outline='')
            cv.create_text(x + 20, y, anchor='w', text=f"{lab}: {s['legal_fraction']:.2%} legal", fill=P['ink'], font=self.f_sub)

    def fill_resources(self, name, rows):
        self.res.delete(*self.res.get_children())
        for r in rows:
            self.res.insert('', 'end', values=(r['method'], *(('' if r.get(k) is None else f"{r[k]:,}") for k in ('qubits', 'measured', 'decision', 'extra', 'cx')), r.get('note', '')))
        self.tabs.select(self.tab['resources'])

    def save(self):
        from tkinter import filedialog, messagebox
        if not self.result:
            messagebox.showinfo('Save', 'Run something first.'); return
        f = filedialog.asksaveasfilename(defaultextension='.json', initialfile=f"{self.result['instance'].replace(' ', '_')}_result.json",
                                         filetypes=[('JSON (everything)', '*.json'), ('Text report', '*.txt')])
        if f:
            Path(f).write_text(summary_text(self.result) if f.endswith('.txt') else json.dumps(self.result, indent=2, default=_json_default))

    def export(self):
        from tkinter import filedialog, messagebox
        try:
            name, bay, cap, _ = self.current_bay()
            method = next(k for k, x in METHODS.items() if x == self.method.get()); presolve = REDUCTIONS[self.reduction.get()]
        except Exception as e:
            messagebox.showwarning('Export', str(e)); return
        d = filedialog.askdirectory(title='Folder for the exported model')
        if d:
            target = Path(d) / f'{name.replace(" ", "_")}_{method}_{presolve}'
            try:
                files = export_model(bay, cap, method, target, int(self.depth.get()), presolve=presolve)
                messagebox.showinfo('Export', f'Wrote {len(files)} files to {target}:\n' + '\n'.join(files))
            except Exception as e:
                messagebox.showerror('Export', f'{type(e).__name__}: {e}')

    # ================================================================== IBM Quantum (Hardware_Panel.py)
    def _hw_estimate(self):
        try:
            ev = int(self.hw['evaluations'].get()); shots = int(self.hw['shots'].get())
            jobs = 1 if (self.hw_fixed.get() and self.hw_single.get()) else ev
            est = qpu_seconds_estimate(jobs, shots * ev // jobs); cap = int(self.hw['budget'].get() or 0)
            self.hw_est.config(text=f'Estimated QPU use: about {est:.0f} s for {jobs} job(s), {shots * ev:,} shots in total '
                                    f'(IBM quick formula). Free plan: up to 600 s per 28 days.'
                                    + ('' if est <= cap else f'  ⚠ Above your cap of {cap} s — raise the cap or use fewer shots.'))
        except (ValueError, self.tk.TclError):
            self.hw_est.config(text='')

    def hw_spec(self):
        name, bay, height, src = self.current_bay()
        method = HW_METHODS[self.hw['method'].get()]; presolve = REDUCTIONS[self.hw['reduction'].get()]
        args = [sys.executable, '-u', str(SCRIPT), 'hardware', '--stacks', ';'.join(','.join(map(str, s)) for s in bay),
                '--height', str(height), '--method', method, '--synthesis', self.hw_synth.get(), '--presolve', presolve]
        for key in ('depth', 'shots', 'evaluations', 'seed'):
            args += ['--' + key, str(int(self.hw[key].get()))]
        args += ['--output', str(RESULTS_DIR / 'hardware')]
        if self.hw_fixed.get():
            args += ['--fixed-angles'] + (['--single-job'] if self.hw_single.get() else [])
        key = (bay, height, tuple((k, v.get()) for k, v in self.hw.items() if k != 'budget'), self.hw_fixed.get(), self.hw_single.get(), self.hw_synth.get())
        return args, name, bay, height, key

    def hw_run(self, mode):
        from tkinter import messagebox
        if self.hw_process:
            messagebox.showinfo('Busy', 'An IBM-tab process is still running.'); return
        try:
            args, name, bay, height, key = self.hw_spec()
            if mode in ('prepare', 'submit'):
                if not self.hw['backend'].get().strip():
                    raise ValueError('Enter an IBM backend name (for example ibm_kingston) or auto for the least busy device.')
                args += ['--backend', self.hw['backend'].get().strip()]
            if mode == 'submit':
                if key != self.hw_preview_key:
                    raise ValueError('First press "1. Compile for IBM" with exactly these settings and check the resource report.')
                budget = int(self.hw['budget'].get())
                ev = int(self.hw['evaluations'].get()); jobs = 1 if (self.hw_fixed.get() and self.hw_single.get()) else ev
                if budget < jobs:
                    raise ValueError('Set a total QPU-seconds cap at least as large as the number of jobs.')
                if not messagebox.askyesno('Submit to IBM Quantum', f'This sends {jobs} job(s) to {self.hw["backend"].get()} and may use up to '
                                           f'{budget} QPU seconds of your account. Continue?'):
                    return
                args += ['--submit', '--max-qpu-seconds', str(budget)]
            elif mode == 'rehearse':
                args += ['--backend', 'fake', '--submit', '--max-qpu-seconds', '600']
            elif mode == 'local':
                args += ['--local-check']
            elif mode == 'export':
                args += ['--export-circuit']
            RESULTS_DIR.mkdir(parents=True, exist_ok=True)
            self.hw_process = subprocess.Popen(args, cwd=str(RESULTS_DIR), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        except Exception as exc:
            messagebox.showerror('Check settings', str(exc)); return
        self.hw_mode, self.hw_key, self.hw_bay, self.hw_height, self.hw_name = mode, key, bay, height, name
        self.hw_acc.set('Accuracy: pending — computed from the measured result.' if mode in ('local', 'submit', 'rehearse')
                        else 'Accuracy: N/A — compiling does not solve the bay.')
        self.hw_latest = None; self.hw_resolved = None; self.hw_started = time.monotonic(); self._spin(True)
        self.hw_state.set('Working… ' + ('Hardware jobs may be submitted within your cap.' if mode == 'submit' else 'No hardware jobs will be submitted.'))
        self.hw_log.insert('end', f'\n━━ {mode.upper()} — {name} ━━\n')

        def read(process):
            for line in process.stdout:
                self.events.put(('hw_line', line))
            process.stdout.close(); self.events.put(('hw_done', process.wait()))
        threading.Thread(target=read, args=(self.hw_process,), daemon=True).start()

    def hw_finished(self, code):
        self.hw_process = None; self._spin(False)
        self.hw_state.set(f'Finished (exit {code}) after {time.monotonic() - self.hw_started:.1f} s.')
        if code != 0 or not self.hw_latest:
            return
        if self.hw_mode == 'prepare':
            if self.hw['backend'].get().strip() == 'auto' and self.hw_resolved:
                self.hw['backend'].set(self.hw_resolved)          # submit to the device that was compiled for
                self.hw_log.insert('end', f'Backend field set to {self.hw_resolved}, the device this circuit was compiled for.\n')
            self.hw_preview_key = self.hw_spec()[4]
            tr = self.hw_latest / 'target_resources.json'
            if tr.exists():
                rep = json.loads(tr.read_text())
                self.hw_log.insert('end', f"TARGET: {rep['backend']} · {rep['active_qubits']} active qubits · {rep['two_qubit_gates']} two-qubit gates · "
                                          f"depth {rep['depth']}. Ready to submit with these exact settings.\n")
        result = self.hw_latest / 'result.json'
        if result.exists():
            r = json.loads(result.read_text())
            item = next((x for x in catalog() if x['stacks_bottom_to_top'] == [list(s) for s in self.hw_bay] and x['capacity'] == self.hw_height), None)
            c = compare(item, self.hw_bay, self.hw_height, r)
            self.hw_acc.set(accuracy_label(c))
            kind = ('ACTUAL IBM HARDWARE' if r['hardware_execution'] else
                    'REHEARSAL ON A FAKE DEVICE — NOT HARDWARE' if self.hw_mode == 'rehearse' else 'IDEAL SIMULATION — NOT HARDWARE')
            self.hw_log.insert('end', kind + '\n' + accuracy_label(c) + '\n')
            if r.get('comparison_to_uniform'):
                cu = r['comparison_to_uniform']; amp = cu['feasible_amplification']
                self.hw_log.insert('end', f"Legal-plan rate {cu['final_batch_feasible_fraction']:.2%}"
                                          + (f" = {amp:.2f}× random guessing" if amp else '')
                                          + f"; best plan: QAOA {cu['qaoa_best_relocations']} vs random {cu['uniform_best_relocations']}\n")
            if r['hardware_execution'] and r.get('reported_usage_seconds') is not None:
                self.hw_log.insert('end', f"IBM-reported QPU usage: {r['reported_usage_seconds']} s\n")
            if c:
                (self.hw_latest / 'published_comparison.json').write_text(json.dumps(c, indent=2) + '\n')
            self.hw_moves.delete(*self.hw_moves.get_children())
            for m in r['moves']:
                self.hw_moves.insert('', 'end', values=(m['type'], m['container'], m['source'], m.get('destination', 'OUT')))
        self.hw_log.see('end')

    def hw_stop(self):
        if self.hw_process:
            self.hw_process.terminate()
            self.hw_state.set('Local process stopped. An already submitted IBM job keeps running: manage it by its job ID.')

    def close(self):
        from tkinter import messagebox
        if self.hw_process and not messagebox.askyesno('Close?', 'An IBM job already submitted keeps running under its cap. Close the window?'):
            return
        self.cancel = True; self.hw_stop(); self.root.destroy()


# ============================================================================
# COMMAND LINE
# ============================================================================
def _json_default(o):
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


def _bay_args(ap):
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument('--instance', help='embedded benchmark name, e.g. data3-3-8')
    src.add_argument('--file', help='group-4 style file')
    src.add_argument('--stacks', help='bottom->top stacks, e.g. "1,3;4,5;2" (empty stack: ";;")')
    src.add_argument('--random', metavar='S,T,C', help='random bay with S stacks, height T, C containers')
    ap.add_argument('--height', type=int, help='capacity for --stacks / --random')
    ap.add_argument('--bay-seed', type=int, default=0)


def _bay_from_args(a):
    if a.instance:
        return Config(instance=a.instance)
    if a.file:
        return Config(path=a.file)
    if a.random:
        S_, T_, C_ = (int(v) for v in a.random.split(','))
        return Config(instance=f'random-S{S_}T{T_}C{C_}-{a.bay_seed}', stacks=[list(s) for s in random_bay(S_, T_, C_, a.bay_seed)], capacity=T_)
    if a.height is None:
        raise SystemExit('--height is required with --stacks')
    return Config(stacks=[[int(v) for v in r.replace(',', ' ').split()] for r in a.stacks.split(';')], capacity=a.height)


# ============================================================================
# IBM HARDWARE STUDY WORKFLOW v2   (Sim9.2, 12 Oct 2026)
# ============================================================================
# Science (unchanged from Sim9): standard presolve, p = 2; predicate (Pauli synthesis, cutoff 5) with the
# release's leave-one-out angles loo:<bay>:p2 and QUBO (Galle CRP-I) with fresh:galle:p2; compile with
# optimization_level 3, seed_transpiler 11; check that the compiled circuit's ideal output equals the logical
# circuit (<= 1e-9); 8 (bay, method) items x 5 jobs x 2,000 shots = 40 jobs, 80,000 shots; SamplerV2,
# no dynamical decoupling, no twirling, no readout correction; 30 s per-job and 300 s study caps; the known
# optimum is used only for scoring after sampling.
# Workflow (new in Sim9.2): a study folder with a persistent, locked job registry; budget reserved before
# each submission; ONE job per "submit"; separate "collect" for results and IBM accounting; "reconcile"
# for uncertain submissions (unique job tags); "replace" for exactly one failed slot; explicit named
# account + Open Plan CRN, never a fallback.
# Commands: ibm plan | check | account | backends | init | prepare | submit | collect | reconcile |
#           replace | status | summarize
IBM_STUDY_DATA = json.loads(r'''{"bays":{"data3-3-3":{"capacity":5,"loo_predicate":{"1":[0.2458926996730333,-0.5536990683825883],"2":[0.1890154920164095,0.34828050608427163,-0.5522082029399951,-0.2533214357321605],"3":[0.13140944997964066,0.2468142132486938,0.45244814062247174,-0.5359844373661226,-0.3503822869070048,-0.15964552284790312]},"optimum_for_scoring_only":2,"sealed_predicate_p2_probabilities":{"accepted_complete":0.0009834479640864577,"accepted_replay_optimal":0.0007904340298421409,"energy_ground":0.00022687346963339548},"sealed_uniform":{"accepted_complete":1.9073486328125e-05,"accepted_replay_optimal":1.1444091796875e-05,"energy_ground":2.86102294921875e-06},"stacks":[[8,1,4],[7,5,2],[9,6,3]]},"data3-3-30":{"capacity":5,"loo_predicate":{"1":[0.23473889745704518,-0.561832443310751],"2":[0.18047204389825558,0.3402714873349897,-0.5645835545486001,-0.2665598289545603],"3":[0.12302375924262074,0.22207328230798526,0.4086336761924352,-0.5885578637761063,-0.35522931347193687,-0.15964552284790312]},"optimum_for_scoring_only":6,"sealed_predicate_p2_probabilities":{"accepted_complete":0.011814850307206184,"accepted_replay_optimal":0.0031076313735807055,"energy_ground":0.0015697224626448018},"sealed_uniform":{"accepted_complete":0.00128173828125,"accepted_replay_optimal":0.0003662109375,"energy_ground":0.00018310546875},"stacks":[[3,5,4],[7,1,2],[6,9,8]]},"data3-3-8":{"capacity":5,"loo_predicate":{"1":[0.2458926996730333,-0.5536990683825883],"2":[0.1890154920164095,0.34828050608427163,-0.5522082029399951,-0.2533214357321605],"3":[0.12997949225568797,0.2401080415784995,0.45244814062247174,-0.5359844373661226,-0.3503822869070048,-0.15964552284790312]},"optimum_for_scoring_only":2,"sealed_predicate_p2_probabilities":{"accepted_complete":0.04248253374581281,"accepted_replay_optimal":0.012680778105792118,"energy_ground":0.003761732756565173},"sealed_uniform":{"accepted_complete":0.005859375,"accepted_replay_optimal":0.001953125,"energy_ground":0.00048828125},"stacks":[[9,2,4],[8,7,1],[5,6,3]]},"random-S3T4C6-12":{"capacity":4,"loo_predicate":{"1":[0.23473889745704518,-0.5536990683825883],"2":[0.18047204389825558,0.3402714873349897,-0.5522082029399951,-0.2533214357321605],"3":[0.12302375924262074,0.22207328230798526,0.4086336761924352,-0.5359844373661226,-0.3503822869070048,-0.15932799225931688]},"optimum_for_scoring_only":2,"sealed_predicate_p2_probabilities":{"accepted_complete":0.022326077950307978,"accepted_replay_optimal":0.015470760349327725,"energy_ground":0.004419970273601772},"sealed_uniform":{"accepted_complete":0.001220703125,"accepted_replay_optimal":0.000732421875,"energy_ground":0.00018310546875},"stacks":[[1,4],[5,2],[6,3]]},"random-S3T4C6-21":{"capacity":4,"loo_predicate":{"1":[0.23473889745704518,-0.561832443310751],"2":[0.18047204389825558,0.3402714873349897,-0.5522082029399951,-0.2607101873221711],"3":[0.12302375924262074,0.22207328230798526,0.4086336761924352,-0.5359844373661226,-0.35522931347193687,-0.15932799225931688]},"optimum_for_scoring_only":1,"sealed_predicate_p2_probabilities":{"accepted_complete":0.2486199823382284,"accepted_replay_optimal":0.08659230978890603,"energy_ground":0.023984239631701824},"sealed_uniform":{"accepted_complete":0.046875,"accepted_replay_optimal":0.015625,"energy_ground":0.00390625},"stacks":[[1],[4,3],[6,2,5]]},"random-S3T4C6-24":{"capacity":4,"loo_predicate":{"1":[0.23473889745704518,-0.56169135554427],"2":[0.18047204389825558,0.3402714873349897,-0.5645835545486001,-0.2665598289545603],"3":[0.12302375924262074,0.22207328230798526,0.4086336761924352,-0.5359844373661226,-0.35522931347193687,-0.15945071631339153]},"optimum_for_scoring_only":2,"sealed_predicate_p2_probabilities":{"accepted_complete":0.10313583369370184,"accepted_replay_optimal":0.03462839558654105,"energy_ground":0.018838123969022354},"sealed_uniform":{"accepted_complete":0.0234375,"accepted_replay_optimal":0.0078125,"energy_ground":0.00390625},"stacks":[[5,2,6,1],[4],[3]]},"random-S3T4C7-32":{"capacity":4,"loo_predicate":{"1":[0.23473889745704518,-0.5536990683825883],"2":[0.18047204389825558,0.3402714873349897,-0.5522082029399951,-0.2665598289545603],"3":[0.12302375924262074,0.22207328230798526,0.4086336761924352,-0.5359844373661226,-0.35522931347193687,-0.15964552284790312]},"optimum_for_scoring_only":1,"sealed_predicate_p2_probabilities":{"accepted_complete":0.11464063023210139,"accepted_replay_optimal":0.037557805873169516,"energy_ground":0.011116798405382175},"sealed_uniform":{"accepted_complete":0.0234375,"accepted_replay_optimal":0.0078125,"energy_ground":0.001953125},"stacks":[[7],[6,2,4],[5,3,1]]},"random-S3T4C7-7":{"capacity":4,"loo_predicate":{"1":[0.23473889745704518,-0.5536990683825883],"2":[0.18475450182353567,0.3402714873349897,-0.5522082029399951,-0.2533214357321605],"3":[0.12302375924262074,0.22207328230798526,0.4086336761924352,-0.5359844373661226,-0.3503822869070048,-0.15932799225931688]},"optimum_for_scoring_only":3,"sealed_predicate_p2_probabilities":{"accepted_complete":0.002607019238921109,"accepted_replay_optimal":0.00034439078678192095,"energy_ground":0.00018722518238589646},"sealed_uniform":{"accepted_complete":0.0001220703125,"accepted_replay_optimal":1.52587890625e-05,"energy_ground":7.62939453125e-06},"stacks":[[3],[7,1,4,2],[5,6]]},"random-S3T5C7-27":{"capacity":5,"loo_predicate":{"1":[0.23473889745704518,-0.561832443310751],"2":[0.18047204389825558,0.3402714873349897,-0.5522082029399951,-0.2533214357321605],"3":[0.12302375924262074,0.22207328230798526,0.4086336761924352,-0.5547704288240227,-0.35522931347193687,-0.15932799225931688]},"optimum_for_scoring_only":4,"sealed_predicate_p2_probabilities":{"accepted_complete":0.002715105266192658,"accepted_replay_optimal":0.0008992994768668278,"energy_ground":0.0004806823610260469},"sealed_uniform":{"accepted_complete":9.1552734375e-05,"accepted_replay_optimal":3.0517578125e-05,"energy_ground":1.52587890625e-05},"stacks":[[3,4],[6],[5,1,2,7]]},"random-S4T3C6-16":{"capacity":3,"loo_predicate":{"1":[0.2458926996730333,-0.561832443310751],"2":[0.18047204389825558,0.3421377912084009,-0.5645835545486001,-0.2665598289545603],"3":[0.13140944997964066,0.2468142132486938,0.45244814062247174,-0.5885578637761063,-0.35522931347193687,-0.15932799225931688]},"optimum_for_scoring_only":2,"sealed_predicate_p2_probabilities":{"accepted_complete":0.10438918800425409,"accepted_replay_optimal":0.09211266754537678,"energy_ground":0.027156850696932838},"sealed_uniform":{"accepted_complete":0.0390625,"accepted_replay_optimal":0.03125,"energy_ground":0.0078125},"stacks":[[],[6],[3,5],[2,4,1]]},"random-S4T3C7-44":{"capacity":3,"loo_predicate":{"1":[0.24036564375020614,-0.561832443310751],"2":[0.1890154920164095,0.34828050608427163,-0.5645835545486001,-0.2665598289545603],"3":[0.13140944997964066,0.2468142132486938,0.45244814062247174,-0.5885578637761063,-0.35522931347193687,-0.15964552284790312]},"optimum_for_scoring_only":1,"sealed_predicate_p2_probabilities":{"accepted_complete":0.12208402053963587,"accepted_replay_optimal":0.10979713230199117,"energy_ground":0.016828639113390144},"sealed_uniform":{"accepted_complete":0.0390625,"accepted_replay_optimal":0.03125,"energy_ground":0.00390625},"stacks":[[2],[1],[6,3,5],[7,4]]},"random-S4T4C7-25":{"capacity":4,"loo_predicate":{"1":[0.2458926996730333,-0.561832443310751],"2":[0.1890154920164095,0.34828050608427163,-0.5645835545486001,-0.2665598289545603],"3":[0.13140944997964066,0.2468142132486938,0.44139743491659367,-0.5885578637761063,-0.3503822869070048,-0.15964552284790312]},"optimum_for_scoring_only":2,"sealed_predicate_p2_probabilities":{"accepted_complete":0.00823825765713484,"accepted_replay_optimal":0.00335981173465623,"energy_ground":0.00046883905320329396},"sealed_uniform":{"accepted_complete":0.00244140625,"accepted_replay_optimal":0.0009765625,"energy_ground":0.0001220703125},"stacks":[[6],[1],[4],[3,5,7,2]]},"random-S4T4C7-31":{"capacity":4,"loo_predicate":{"1":[0.2458926996730333,-0.5536990683825883],"2":[0.1890154920164095,0.34828050608427163,-0.5645835545486001,-0.2533214357321605],"3":[0.13140944997964066,0.2468142132486938,0.45244814062247174,-0.5885578637761063,-0.3503822869070048,-0.15932799225931688]},"optimum_for_scoring_only":2,"sealed_predicate_p2_probabilities":{"accepted_complete":0.008671260037037347,"accepted_replay_optimal":0.007533373873297723,"energy_ground":0.0017946164743037202},"sealed_uniform":{"accepted_complete":0.000274658203125,"accepted_replay_optimal":0.0001220703125,"energy_ground":3.0517578125e-05},"stacks":[[1],[4,3],[5,6,2,7],[]]},"random-S4T4C7-43":{"capacity":4,"loo_predicate":{"1":[0.2458926996730333,-0.5536990683825883],"2":[0.1890154920164095,0.34828050608427163,-0.5630618295592691,-0.2533214357321605],"3":[0.13140944997964066,0.2468142132486938,0.45244814062247174,-0.5885578637761063,-0.3503822869070048,-0.15932799225931688]},"optimum_for_scoring_only":1,"sealed_predicate_p2_probabilities":{"accepted_complete":0.005095032592051142,"accepted_replay_optimal":0.0036675753364347374,"energy_ground":0.0005258012866883143},"sealed_uniform":{"accepted_complete":0.000244140625,"accepted_replay_optimal":6.103515625e-05,"energy_ground":7.62939453125e-06},"stacks":[[6,2,5],[7,4],[3],[1]]},"random-S4T4C8-42":{"capacity":4,"loo_predicate":{"1":[0.2458926996730333,-0.561832443310751],"2":[0.1890154920164095,0.34828050608427163,-0.5645835545486001,-0.2665598289545603],"3":[0.13140944997964066,0.2468142132486938,0.45244814062247174,-0.5885578637761063,-0.35044074240079703,-0.15964552284790312]},"optimum_for_scoring_only":3,"sealed_predicate_p2_probabilities":{"accepted_complete":0.012045492102948186,"accepted_replay_optimal":0.012045492102948186,"energy_ground":0.0037866469141608463},"sealed_uniform":{"accepted_complete":0.00439453125,"accepted_replay_optimal":0.00439453125,"energy_ground":0.0010986328125},"stacks":[[7,8],[4,5,6,1],[3],[2]]}},"fresh":{"galle":{"1":[0.696,-0.482],"2":[0.647,-2.595,-0.409,0.211],"3":[0.511,-0.391,-3.013,-1.02,0.49,0.212]},"hybrid":{"1":[0.141,-0.501],"2":[0.129,0.86,-0.512,-0.181],"3":[0.089,0.222,5.5,-0.494,-0.19,0.154]},"predicate":{"1":[0.24,-0.554],"2":[0.185,0.346,-0.554,-0.259],"3":[0.124,0.229,0.42,-0.57,-0.355,-0.16]}},"source":{"active_manifest_sha256":"8d0212d4621d43eba09d79675891924660db65b01f942a5aae8b224a65472068","angles_json":"<baseline>/release_evidence/calibration/angles.json","angles_sha256":"2aa449cd3e22ca36f932e93f40d47ad653a1d49a8cf957bbf10f773178529ac9","cases_json":"<baseline>/clean_release_verified_2026_10_09/artifacts/main/cases.json","cases_sha256":"38373c05724b70ca03a941bfeb8447bfa64c77a5d9419df4ac366c6bc0979b4b"}}''')
IBM_LADDER = {'predicate': ['random-S3T4C6-21', 'random-S3T4C6-24', 'random-S3T4C7-32', 'random-S4T3C6-16', 'data3-3-8'],
              'galle': ['random-S3T4C6-21', 'random-S3T4C6-24', 'random-S3T4C7-32']}
IBM_SETTINGS = dict(p=2, presolve='standard', direct_cutoff=5, synthesis='pauli', optimization_level=3, seed_transpiler=11,
                    batches=5, shots_per_batch=2000, max_execution_time_per_job_seconds=30, total_qpu_seconds_cap=300,
                    mitigation='none: dynamical decoupling off, gate and measurement twirling off, no readout correction',
                    fake_device='FakeFez', check_tolerance=1e-9, enumeration_qubit_guard=22)
IBM_METHOD_NAMES = {'predicate': 'Predicate QAOA', 'galle': 'QUBO QAOA (Galle CRP-I)'}


def _ibm_now():
    import datetime as _dt
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def _ibm_json(path, obj):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True, default=_json_default) + '\n'); os.replace(tmp, path)


def _ibm_seed(*parts):
    return int.from_bytes(hashlib.sha256('|'.join(map(str, parts)).encode()).digest()[:8], 'little')


def _ibm_wilson(k, n, z=1.96):
    if not n:
        return [None, None]
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [max(0.0, c - h), min(1.0, c + h)]


def ibm_build(case, method):
    """Frozen bay, standard-presolve problem and frozen p=2 angles for one method."""
    if method not in IBM_LADDER:
        raise ValueError("IBM study methods are 'predicate' and 'galle' (QUBO)")
    bay = IBM_STUDY_DATA['bays'].get(case)
    if bay is None:
        raise ValueError(f'{case} is not one of the 15 frozen benchmark bays: {sorted(IBM_STUDY_DATA["bays"])}')
    kw = dict(synthesis='pauli', direct_cutoff=5) if method == 'predicate' else {}
    problem = Problem(bay['stacks'], bay['capacity'], method, presolve='standard', **kw)
    if method == 'predicate':
        theta, angle_id = bay['loo_predicate']['2'], f'loo:{case}:p2'
        if problem.predicate.scratch:
            raise NotImplementedError(f'{case}: needs scratch arithmetic rows; not part of this study')
    else:
        theta, angle_id = IBM_STUDY_DATA['fresh']['galle']['2'], 'fresh:galle:p2'
    return bay, problem, [float(t) for t in theta], angle_id


def ibm_circuit(problem, theta, p=2):
    return bind(problem.circuit(p), theta, p)


def _ibm_logical_probs(qc):
    from qiskit.quantum_info import Statevector
    return np.abs(Statevector(qc.remove_final_measurements(inplace=False)).data) ** 2


def _ibm_isa_probs(isa, n_measured, guard):
    """Exact ideal output of a compiled circuit over its classical bits (layout-aware)."""
    from qiskit import QuantumCircuit
    from qiskit.quantum_info import Statevector
    active = sorted({isa.find_bit(q).index for inst in isa.data for q in inst.qubits if inst.operation.name != 'barrier'})
    if len(active) > guard:
        return None, len(active)
    pos = {q: i for i, q in enumerate(active)}
    body = QuantumCircuit(len(active)); body.global_phase = isa.global_phase; meas = {}
    for inst in isa.data:
        idx = [isa.find_bit(q).index for q in inst.qubits]
        if inst.operation.name == 'measure':
            meas[isa.find_bit(inst.clbits[0]).index] = pos[idx[0]]
        elif inst.operation.name != 'barrier':
            if any(pos[i] in meas.values() for i in idx):
                raise RuntimeError('gate after measurement on a measured qubit')
            body.append(inst.operation, [pos[i] for i in idx])
    if sorted(meas) != list(range(n_measured)):
        raise RuntimeError('compiled measurement map does not cover the measured register')
    P = np.abs(Statevector(body).data) ** 2; full = np.arange(len(P)); out = np.zeros(len(P), dtype=np.int64)
    for clbit, q in meas.items():
        out |= ((full >> q) & 1) << clbit
    return np.bincount(out, weights=P, minlength=1 << n_measured), len(active)


def _ibm_score(states, table, problem, bay):
    """Legal / replay-optimal / ground outcome of ordered shots; independent replay of the reported plan."""
    s = np.asarray(states, dtype=np.int64); n = len(s); opt = bay['optimum_for_scoring_only']
    acc = table['accepted'][s]; cost = table['cost'][s]; best = acc & (cost == opt)
    out = dict(shots=n, accepted_count=int(acc.sum()), accepted_rate=float(acc.mean()) if n else None,
               accepted_rate_ci95=_ibm_wilson(int(acc.sum()), n), replay_optimal_count=int(best.sum()),
               replay_optimal_rate=float(best.mean()) if n else None, replay_optimal_rate_ci95=_ibm_wilson(int(best.sum()), n),
               energy_ground_count=int(table['ground'][s].sum()), mean_energy=float(table['E'][s].mean()) if n else None,
               best_accepted_relocations=int(cost[acc].min()) if acc.any() else None,
               median_accepted_relocations=float(np.median(cost[acc])) if acc.any() else None, distinct_states=int(len(np.unique(s))))
    plan = None
    if acc.any():
        v = int(cost[acc].min()); state = int(s[acc][cost[acc] == v].min())
        width = table['physical_width']; enc = problem.predicate or problem.qubo
        x = enc.presolve.recover([(state >> i) & 1 for i in range(width)])
        indep = reconstruct_assignment(problem.model, x)
        if not indep['valid'] or indep['relocations'] != v:
            raise RuntimeError('independent replay disagrees with the decoder')
        plan = dict(state=state, relocations=v, independent_replay_relocations=indep['relocations'], is_replay_optimal=v == opt,
                    moves=indep['moves'])
    out['reported_plan'] = plan; out['no_valid_plan'] = plan is None
    return out


IBM_ORDER = [('random-S3T4C6-21', 'predicate'), ('random-S3T4C6-21', 'galle'), ('random-S3T4C6-24', 'galle'),
             ('random-S3T4C6-24', 'predicate'), ('random-S3T4C7-32', 'predicate'), ('random-S3T4C7-32', 'galle'),
             ('random-S4T3C6-16', 'predicate'), ('data3-3-8', 'predicate')]   # Sim9 pamphlet run order
IBM_SETTINGS.update(protocol_id='sim9-ladder-v1: 8 items x 5 jobs x 2000 shots', preparation_max_age_hours=24)
assert sorted(IBM_ORDER) == sorted((c, m) for m, cs in IBM_LADDER.items() for c in cs)




def _ibm_check_with_backend(case, method, be, live, out=None, say=print):
    """Checks A, B and C for one (bay, method) on a given backend object. Science identical to Sim9's
    ibm_check: same model, angles, circuit, compiler settings, tolerances. Submits nothing."""
    from qiskit import qpy
    from qiskit.transpiler import generate_preset_pass_manager
    bay, problem, theta, angle_id = ibm_build(case, method)
    n = problem.n; guard = IBM_SETTINGS['enumeration_qubit_guard']
    if n > guard:
        raise IBMStudyError(f'{case}/{method}: {n} qubits exceed the {guard}-qubit laptop guard for exact checks')
    qc = ibm_circuit(problem, theta); table = evaluation_table(problem)
    P = _ibm_logical_probs(qc); P_table = qaoa_probs(table['E'].astype(float), theta, 2, problem.scale, n)
    opt = bay['optimum_for_scoring_only']; acc = table['accepted']; best = acc & (table['cost'] == opt)
    ideal = dict(accepted=float(P[acc].sum()), replay_optimal=float(P[best].sum()), energy_ground=float(P[table['ground']].sum()))
    uniform = dict(accepted=float(acc.mean()), replay_optimal=float(best.mean()), energy_ground=float(table['ground'].mean()))
    rec = dict(case=case, method=method, method_name=IBM_METHOD_NAMES[method], qubits=n, angle_id=angle_id, theta=theta,
               settings=IBM_SETTINGS, ideal=ideal, uniform=uniform, created_utc=_ibm_now(), data_kind='CHECK (no shots)',
               check_A_max_abs_prob_diff=float(np.max(np.abs(P - P_table))),
               best_cost_by_enumeration=table['best_cost'], optimum_for_scoring_only=opt,
               check_B_enumerated_optimum_equals_BFS=table['best_cost'] == opt,
               check_B_every_ground_string_replays_optimal=bool(np.all(best[table['ground']])))
    if method == 'predicate':
        sealed = bay['sealed_predicate_p2_probabilities']
        rec['check_B_max_rel_diff_vs_sealed_release'] = max(abs(ideal[a] - sealed[b]) / sealed[b] for a, b in
                                                            (('accepted', 'accepted_complete'), ('replay_optimal', 'accepted_replay_optimal'), ('energy_ground', 'energy_ground')))
    if n > be.num_qubits:
        raise IBMStudyError(f'{n} qubits do not fit {be.name} ({be.num_qubits})')
    t = time.perf_counter()
    isa = generate_preset_pass_manager(optimization_level=IBM_SETTINGS['optimization_level'], backend=be,
                                       seed_transpiler=IBM_SETTINGS['seed_transpiler']).run(qc)
    P_isa, active = _ibm_isa_probs(isa, n, guard)
    lay = isa.layout
    rec.update(backend=be.name, live_target=live, compile_seconds=round(time.perf_counter() - t, 2), active_qubits=active,
               compiled_two_qubit=sum(1 for i in isa.data if i.operation.num_qubits == 2), compiled_depth=isa.depth(),
               compiled_two_qubit_depth=isa.depth(lambda i: i.operation.num_qubits == 2), compiled_ops=dict(isa.count_ops()),
               layout_initial=None if lay is None else lay.initial_index_layout(filter_ancillas=True),
               layout_final=None if lay is None else lay.final_index_layout(filter_ancillas=True),
               check_C_max_abs_prob_diff=None if P_isa is None else float(np.max(np.abs(P_isa - P))))
    tol = IBM_SETTINGS['check_tolerance']
    rec['passed'] = bool(rec['check_A_max_abs_prob_diff'] <= tol and rec['check_B_enumerated_optimum_equals_BFS']
                         and rec['check_B_every_ground_string_replays_optimal']
                         and rec.get('check_B_max_rel_diff_vs_sealed_release', 0) <= tol
                         and rec['check_C_max_abs_prob_diff'] is not None and rec['check_C_max_abs_prob_diff'] <= tol)
    if out:
        out = Path(out); out.mkdir(parents=True, exist_ok=True)
        _ibm_write_qpy(out / 'isa.qpy', isa); _ibm_write_qpy(out / 'logical.qpy', qc)
        _ibm_write(out / 'check.json', rec)
    say(f"{case} {method}: {n} qubits, {rec['compiled_two_qubit']} two-qubit gates on {be.name}; "
        f"A {rec['check_A_max_abs_prob_diff']:.1e}, C {rec['check_C_max_abs_prob_diff']}, passed={rec['passed']}")
    return rec, isa, problem, table


def ibm_check(case, method, backend_name='fake', out=None, say=print):
    """Stand-alone check on the fake device (no account). Live checks run inside a study (ibm prepare)."""
    if backend_name != 'fake':
        raise IBMStudyError('Live-device checks need an explicit account and instance: use "ibm init" then "ibm prepare".')
    be = _ibm_fake_backend()
    rec, isa, problem, table = _ibm_check_with_backend(case, method, be, False, out, say)
    return rec, isa, problem, table, be, False


# ----------------------------------------------------------------------------
# Durable files, locking and the job registry (Sim9.2)
# ----------------------------------------------------------------------------
class IBMStudyError(Exception):
    """A deliberate stop. The message says what to do; nothing was submitted unless it says so."""


IBM_STUDY_SCHEMA = 'sim9.2-ibm-study/1'
IBM_ATTEMPT_SCHEMA = 'sim9.2-ibm-attempt/1'
IBM_STATES = ('submitting', 'submitted', 'uncertain', 'awaiting', 'completed', 'failed', 'cancelled', 'reconciled_no_job')
IBM_STATE_TEXT = {'submitting': 'submission in progress', 'submitted': 'submitted, IBM job ID recorded',
                  'uncertain': 'submission outcome uncertain (no job ID saved)', 'awaiting': 'results saved, awaiting final accounting',
                  'completed': 'completed: results and final accounting', 'failed': 'failed', 'cancelled': 'cancelled',
                  'reconciled_no_job': 'reconciled: no IBM job exists'}
IBM_ACCOUNTING = ('reserved', 'pending', 'unavailable', 'final', 'final_zero')
IBM_TERMINAL_JOB = ('DONE', 'ERROR', 'CANCELLED')
_IBM_RECONCILE_MIN_GAP_SECONDS = 600


def _ibm_fake_backend():
    from qiskit_ibm_runtime import fake_provider as fp
    return getattr(fp, IBM_SETTINGS['fake_device'])()


def _ibm_fsync_dir(path):
    try:
        fd = os.open(str(path), os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError:
        pass


def _ibm_write(path, obj):
    """Atomic, durable JSON write: temp file, fsync, rename, fsync directory."""
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(obj, indent=2, sort_keys=True, default=_json_default) + '\n').encode()
    tmp = path.with_name(f'.{path.name}.{os.getpid()}.tmp')
    with open(tmp, 'wb') as f:
        f.write(data); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path); _ibm_fsync_dir(path.parent)


def _ibm_write_new(path, obj):
    """Exclusive create: fails if the file already exists (no silent overwrite)."""
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(obj, indent=2, sort_keys=True, default=_json_default) + '\n').encode()
    with open(path, 'xb') as f:
        f.write(data); f.flush(); os.fsync(f.fileno())
    _ibm_fsync_dir(path.parent)


def _ibm_write_qpy(path, circuit):
    from qiskit import qpy
    path = Path(path); tmp = path.with_name(f'.{path.name}.{os.getpid()}.tmp')
    with open(tmp, 'wb') as f:
        qpy.dump(circuit, f); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path); _ibm_fsync_dir(path.parent)


def _ibm_load_qpy(path):
    from qiskit import qpy
    with open(path, 'rb') as f:
        circuits = qpy.load(f)
    if len(circuits) != 1:
        raise IBMStudyError(f'{path} must hold exactly one circuit')
    return circuits[0]


def _ibm_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _ibm_read(path):
    try:
        return json.loads(Path(path).read_text())
    except FileNotFoundError:
        raise IBMStudyError(f'Missing file: {path}') from None
    except (ValueError, OSError) as exc:
        raise IBMStudyError(f'Unreadable or corrupt file {path} ({type(exc).__name__}); submissions are stopped until it is repaired') from None


def _ibm_event(root, event_name, **fields):
    line = json.dumps(dict(time_utc=_ibm_now(), event=event_name, **fields), sort_keys=True, default=_json_default) + '\n'
    with open(Path(root) / 'events.jsonl', 'a') as f:
        f.write(line); f.flush(); os.fsync(f.fileno())


class _IBMStudyLock:
    """One process at a time may change a study (submit, collect, reconcile, replace, prepare)."""

    def __init__(self, root):
        self.path = Path(root) / 'study.lock'; self.f = None

    def __enter__(self):
        import fcntl
        self.f = open(self.path, 'a+')
        try:
            fcntl.flock(self.f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.f.close(); self.f = None
            raise IBMStudyError('Another Sim9.2 process is using this study right now. Wait for it to finish; nothing was submitted.') from None
        return self

    def __exit__(self, *exc):
        import fcntl
        if self.f is not None:
            fcntl.flock(self.f.fileno(), fcntl.LOCK_UN); self.f.close()
        return False


def _ibm_versions():
    out = dict(python=sys.version.split()[0], numpy=np.__version__)
    for mod in ('qiskit', 'qiskit_aer', 'qiskit_ibm_runtime'):
        try:
            out[mod] = __import__(mod).__version__
        except Exception as exc:
            out[mod] = f'unavailable: {type(exc).__name__}'
    try:
        out['sim_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    except Exception:
        out['sim_sha256'] = None
    return out


def ibm_slots():
    """The declared protocol: 8 (bay, method) items x 5 repetitions, in the pamphlet's order."""
    slots = []
    for case, method in IBM_ORDER:
        for rep in range(IBM_SETTINGS['batches']):
            slots.append(dict(index=len(slots), slot_id=f'{len(slots) + 1:02d}_{case}__{method}__rep{rep + 1}',
                              case=case, method=method, repetition=rep + 1, shots=IBM_SETTINGS['shots_per_batch']))
    return slots


def _ibm_paths(root):
    root = Path(root)
    return dict(root=root, study=root / 'study.json', prep=root / 'prep', registry=root / 'registry', results=root / 'results')


def ibm_init(root, backend, account_name=None, instance_crn=None, approval=None, say=print):
    """Create a new study folder. Live studies record the exact saved account name and Open Plan CRN."""
    p = _ibm_paths(root)
    if p['study'].exists():
        raise IBMStudyError(f'{p["study"]} already exists. Resume that study; do not re-create it.')
    live = backend != 'fake'
    if live:
        if not account_name or not instance_crn or not str(instance_crn).startswith('crn:'):
            raise IBMStudyError('A live study needs --account NAME and --instance CRN (the Open Plan CRN from IBM Instances).')
        if not approval:
            raise IBMStudyError('A live study needs --approval FILE (filled in after Radin approves the run and budget).')
        appr = _ibm_read(approval)
        _ibm_validate_approval(appr, backend)
    else:
        appr = None
    p['root'].mkdir(parents=True, exist_ok=True)
    slots = ibm_slots()
    study = dict(schema=IBM_STUDY_SCHEMA, created_utc=_ibm_now(), kind='live' if live else 'fake',
                 data_kind='HARDWARE' if live else 'SIMULATION (fake device; not hardware data)',
                 backend=backend if live else IBM_SETTINGS['fake_device'], account_name=account_name, instance_crn=instance_crn,
                 expected_plan='open', approval=appr, approval_sha256=_ibm_sha(approval) if approval else None,
                 approval_path=str(Path(approval).resolve()) if approval else None,
                 protocol=dict(id=IBM_SETTINGS['protocol_id'], order=IBM_ORDER, batches=IBM_SETTINGS['batches'],
                               shots_per_job=IBM_SETTINGS['shots_per_batch'], jobs=len(slots), total_shots=sum(s['shots'] for s in slots),
                               analysis_rule=IBM_ANALYSIS_RULE, replacement_rule=IBM_REPLACEMENT_RULE),
                 caps=dict(per_job_seconds=IBM_SETTINGS['max_execution_time_per_job_seconds'],
                           study_seconds=IBM_SETTINGS['total_qpu_seconds_cap']),
                 settings=IBM_SETTINGS, slots=slots, versions=_ibm_versions())
    _ibm_write_new(p['study'], study)
    for d in ('prep', 'registry', 'results'):
        p[d].mkdir(exist_ok=True)
    _ibm_event(root, 'study_created', kind=study['kind'], backend=study['backend'])
    say(f"Study created: {p['root']} ({study['kind']}, {len(slots)} planned jobs, {study['protocol']['total_shots']:,} shots)")
    return study


IBM_ANALYSIS_RULE = ('For each slot, the analysed attempt is the FIRST attempt (in attempt order) whose results were saved and '
                     'passed the identity checks. Attempts without results are reported but not analysed. A replacement is only '
                     'allowed when no earlier attempt of that slot has results, so there is never a choice between result sets.')
IBM_REPLACEMENT_RULE = ('At most one replacement per slot, one job, only after the original attempt is failed/cancelled (or '
                        'reconciled as no job) AND its accounting is final. Both attempts and both costs are kept.')


def _ibm_validate_approval(a, backend):
    if not isinstance(a, dict):
        raise IBMStudyError('Approval file is not a JSON object')
    msg = str(a.get('approved_by_radin_message', '')).strip()
    if not msg or '<' in msg or '__' in msg:
        raise IBMStudyError('Approval file has no completed approving message (replace the placeholder text and date)')
    if a.get('backend') != backend:
        raise IBMStudyError(f'Approval names backend {a.get("backend")!r}, not {backend!r}')
    want = {m: list(c) for m, c in IBM_LADDER.items()}
    got = a.get('cases_by_method')
    if not isinstance(got, dict) or {m: sorted(v) for m, v in got.items()} != {m: sorted(v) for m, v in want.items()}:
        raise IBMStudyError(f'Approval cases_by_method must be exactly {want}')
    for k, v in (('batches', IBM_SETTINGS['batches']), ('shots_per_batch', IBM_SETTINGS['shots_per_batch']),
                 ('max_execution_time_per_job_seconds', IBM_SETTINGS['max_execution_time_per_job_seconds']),
                 ('total_qpu_seconds_cap', IBM_SETTINGS['total_qpu_seconds_cap'])):
        if a.get(k) != v:
            raise IBMStudyError(f'Approval {k} must be {v} (found {a.get(k)!r})')


def _ibm_load_study(root):
    p = _ibm_paths(root)
    study = _ibm_read(p['study'])
    if study.get('schema') != IBM_STUDY_SCHEMA:
        raise IBMStudyError('study.json has an unknown schema; submissions stopped')
    for k in ('kind', 'backend', 'slots', 'caps', 'protocol'):
        if k not in study:
            raise IBMStudyError(f'study.json lacks {k}; submissions stopped')
    if [s['slot_id'] for s in study['slots']] != [s['slot_id'] for s in ibm_slots()]:
        raise IBMStudyError('study.json slots differ from the declared protocol; submissions stopped')
    if study['kind'] == 'live':
        if study.get('approval_path') and Path(study['approval_path']).exists() and _ibm_sha(study['approval_path']) != study['approval_sha256']:
            raise IBMStudyError('The approval file changed after the study was created; submissions stopped')
    return study


_IBM_ATTEMPT_FIELDS = ('schema', 'attempt_id', 'slot_id', 'attempt_no', 'state', 'tag', 'created_utc', 'reservation_seconds',
                       'accounting', 'prep', 'planned_shots', 'backend', 'history')


def _ibm_check_attempt(rec, path):
    if not isinstance(rec, dict) or rec.get('schema') != IBM_ATTEMPT_SCHEMA:
        raise IBMStudyError(f'Registry record {path.name} has an unknown schema; submissions stopped')
    missing = [k for k in _IBM_ATTEMPT_FIELDS if k not in rec]
    if missing:
        raise IBMStudyError(f'Registry record {path.name} is incomplete (missing {missing}); submissions stopped')
    if rec['state'] not in IBM_STATES:
        raise IBMStudyError(f'Registry record {path.name} has unknown state {rec["state"]!r}; submissions stopped')
    acc = rec['accounting']
    if not isinstance(acc, dict) or acc.get('status') not in IBM_ACCOUNTING:
        raise IBMStudyError(f'Registry record {path.name} has invalid accounting; submissions stopped')
    if path.stem != rec['attempt_id']:
        raise IBMStudyError(f'Registry record {path.name} does not match its attempt id; submissions stopped')


def _ibm_registry(root, study, recover=True):
    """Load every attempt record. Crash recovery: a 'submitting' record whose process is gone becomes
    'submitted' (job ID found in its side file) or 'uncertain'. Corrupt data stops everything."""
    reg_dir = _ibm_paths(root)['registry']
    stray = [x.name for x in reg_dir.iterdir() if x.suffix not in ('.json', '.jobid') and not x.name.startswith('.')]
    if stray:
        raise IBMStudyError(f'Unexpected files in registry {stray}; submissions stopped')
    recs = {}
    slot_ids = {s['slot_id'] for s in study['slots']}
    for path in sorted(reg_dir.glob('*.json')):
        rec = _ibm_read(path); _ibm_check_attempt(rec, path)
        if rec['slot_id'] not in slot_ids:
            raise IBMStudyError(f'Registry record {path.name} names an unknown slot; submissions stopped')
        recs[rec['attempt_id']] = rec
    for side in reg_dir.glob('*.jobid'):
        if side.stem not in recs:
            raise IBMStudyError(f'Job-ID side file {side.name} has no registry record; reconcile manually; submissions stopped')
    if recover:
        for rec in recs.values():
            if rec['state'] == 'submitting':
                side = reg_dir / f'{rec["attempt_id"]}.jobid'
                if side.exists() and side.read_text().strip():
                    _ibm_transition(root, rec, 'submitted', 'recovered job ID from side file after interruption',
                                    job_id=side.read_text().strip())
                else:
                    _ibm_transition(root, rec, 'uncertain', 'process stopped during submission before a job ID was saved; '
                                    'the job may exist on IBM. Run "ibm reconcile".')
    return recs


def _ibm_attempt_path(root, attempt_id):
    return _ibm_paths(root)['registry'] / f'{attempt_id}.json'


def _ibm_transition(root, rec, state, note, **updates):
    if state not in IBM_STATES:
        raise IBMStudyError(f'internal: unknown state {state}')
    rec.update(updates); old = rec['state']; rec['state'] = state
    rec['history'].append(dict(utc=_ibm_now(), from_state=old, to_state=state, note=note))
    _ibm_write(_ibm_attempt_path(root, rec['attempt_id']), rec)
    _ibm_event(root, 'attempt_state', attempt=rec['attempt_id'], from_state=old, to_state=state, note=note)


def _ibm_accounting_final(rec):
    return rec['accounting']['status'] in ('final', 'final_zero') or rec['state'] == 'reconciled_no_job'


def _ibm_committed_seconds(rec):
    """Seconds this attempt counts against the study cap: final usage if final, else the full reservation."""
    acc = rec['accounting']
    if rec['state'] == 'reconciled_no_job':
        return 0.0
    if acc['status'] in ('final', 'final_zero'):
        return float(acc['seconds'])
    return float(rec['reservation_seconds'])


def _ibm_unresolved(recs):
    """Attempts that may still be chargeable or may still produce results."""
    out = []
    for r in recs.values():
        if r['state'] in ('submitting', 'submitted', 'uncertain', 'awaiting') or not _ibm_accounting_final(r):
            out.append(r)
    return out


def ibm_budget(study, recs):
    final = sum(float(r['accounting']['seconds']) for r in recs.values()
                if r['accounting']['status'] in ('final', 'final_zero') and r['state'] != 'reconciled_no_job')
    reserved = sum(float(r['reservation_seconds']) for r in recs.values() if not _ibm_accounting_final(r))
    cap = float(study['caps']['study_seconds'])
    return dict(study_cap_seconds=cap, final_confirmed_seconds=final, unresolved_reserved_seconds=reserved,
                committed_seconds=final + reserved, study_headroom_seconds=cap - final - reserved)


# ----------------------------------------------------------------------------
# IBM account and service (explicit account + Open Plan CRN, never a fallback)
# ----------------------------------------------------------------------------
def _ibm_default_service_factory(**kw):
    from qiskit_ibm_runtime import QiskitRuntimeService
    return QiskitRuntimeService(**kw)


def _ibm_default_sampler_factory(mode, options):
    from qiskit_ibm_runtime import SamplerV2
    return SamplerV2(mode=mode, options=options)


IBM_HOOKS = dict(service=_ibm_default_service_factory, sampler=_ibm_default_sampler_factory, fake_backend=_ibm_fake_backend)


def _ibm_open_service(study):
    """Connect with the study's named account and CRN and verify the instance is Open Plan.
    Never prints account details (the saved account contains the API key)."""
    if study['kind'] != 'live':
        raise IBMStudyError('internal: fake studies do not use an IBM account')
    try:
        svc = IBM_HOOKS['service'](name=study['account_name'], channel='ibm_quantum_platform', instance=study['instance_crn'])
    except IBMStudyError:
        raise
    except Exception as exc:
        raise IBMStudyError(f'Could not open the saved IBM account {study["account_name"]!r} ({type(exc).__name__}). '
                            'Check the account name and API key; nothing was submitted.') from None
    try:
        active = svc.active_instance()
        insts = list(svc.instances())
    except Exception as exc:
        raise IBMStudyError(f'Could not read the IBM instance list ({type(exc).__name__}); nothing was submitted.') from None
    if active != study['instance_crn']:
        raise IBMStudyError('The active IBM instance is not the study instance CRN; refusing (no fallback to another instance).')
    match = [i for i in insts if isinstance(i, dict) and i.get('crn') == study['instance_crn']]
    if len(match) != 1:
        raise IBMStudyError('The study instance CRN is not (uniquely) visible to this account; refusing.')
    if str(match[0].get('plan', '')).strip().lower() != 'open':
        raise IBMStudyError(f'The study instance plan is {match[0].get("plan")!r}, not Open; refusing (no paid instances).')
    return svc


def _ibm_allowance(svc):
    """IBM-reported instance usage (Open Plan window). Returns evidence; never raises."""
    try:
        u = dict(svc.usage())
    except Exception as exc:
        return dict(available=False, error=type(exc).__name__)
    keep = {k: v for k, v in u.items() if k.startswith('usage_') or k in ('period',)}
    rem = keep.get('usage_remaining_seconds')
    ok = isinstance(rem, (int, float)) and not isinstance(rem, bool) and math.isfinite(rem)
    return dict(available=ok, remaining_seconds=float(rem) if ok else None, raw=keep)


def _ibm_status_str(job):
    s = job.status()
    return str(getattr(s, 'name', s)).split('.')[-1].upper()


def _ibm_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and v >= 0


def ibm_read_usage(job, terminal):
    """Interpret IBM accounting for one job (Runtime >= 0.30: metrics()['usage'] with 'status' and
    'qpu_charge_time_seconds'; job.usage() returns 0 while 'pending'). Legacy 'quantum_seconds' without a
    status field is accepted only for a job in a terminal state. Returns a dict with status in
    final / final_zero / pending / unavailable and the raw evidence."""
    out = dict(observed_utc=_ibm_now(), job_terminal=bool(terminal))
    try:
        metrics = job.metrics()
    except Exception as exc:
        out.update(status='unavailable', seconds=None, field=None, error=f'metrics() failed: {type(exc).__name__}')
        return out
    usage = metrics.get('usage') if isinstance(metrics, dict) else None
    out['raw_usage'] = usage
    try:
        out['sdk_job_usage'] = job.usage()          # recorded as evidence only (0 while pending)
    except Exception as exc:
        out['sdk_job_usage'] = f'error: {type(exc).__name__}'
    if not isinstance(usage, dict):
        out.update(status='unavailable', seconds=None, field=None, error='metrics() has no usage object')
        return out
    st = usage.get('status')
    if st is not None:
        if str(st).strip().lower() == 'pending':
            out.update(status='pending', seconds=None, field='metrics.usage.status == pending')
            return out
        q = usage.get('qpu_charge_time_seconds')
        if _ibm_number(q):
            out.update(status='final_zero' if float(q) == 0 else 'final', seconds=float(q),
                       field=f'metrics.usage.qpu_charge_time_seconds (status {st!r})')
        else:
            out.update(status='unavailable', seconds=None, field=None,
                       error=f'usage status {st!r} but qpu_charge_time_seconds is {q!r}')
        return out
    legacy = usage.get('quantum_seconds')
    if legacy is not None and _ibm_number(legacy) and terminal:
        out.update(status='final_zero' if float(legacy) == 0 else 'final', seconds=float(legacy),
                   field='metrics.usage.quantum_seconds (legacy format, no status field, terminal job)')
        return out
    out.update(status='unavailable', seconds=None, field=None, error='no recognised accounting fields')
    return out


# ----------------------------------------------------------------------------
# Preparation (live compile + checks), frozen per (bay, method)
# ----------------------------------------------------------------------------
def _ibm_item(case, method):
    return f'{case}__{method}'


def ibm_prepare(root, items=None, say=print):
    """Compile and check (A, B, C) each (bay, method) for the study's backend; save frozen circuits.
    Contacts IBM only to read device information. Submits nothing."""
    with _IBMStudyLock(root):
        study = _ibm_load_study(root); live = study['kind'] == 'live'
        if live:
            svc = _ibm_open_service(study)
            try:
                be = svc.backend(study['backend'])
            except Exception as exc:
                raise IBMStudyError(f'Backend {study["backend"]!r} is not available to this instance ({type(exc).__name__})') from None
            _ibm_check_real_backend(be, study)
        else:
            be = IBM_HOOKS['fake_backend']()
        todo = items or IBM_ORDER
        done = []
        for case, method in todo:
            if (case, method) not in [tuple(x) for x in IBM_ORDER]:
                raise IBMStudyError(f'{case}/{method} is not part of this study')
            base = _ibm_paths(root)['prep'] / _ibm_item(case, method)
            version = 1 + len([d for d in base.glob('v*') if d.is_dir()]) if base.exists() else 1
            out = base / f'v{version}'
            rec, isa, problem, table = _ibm_check_with_backend(case, method, be, live, out, say)
            if not rec['passed']:
                raise IBMStudyError(f'{case}/{method} failed its circuit checks on {be.name}; nothing can be submitted for it')
            snap = _ibm_backend_snapshot(be)
            _ibm_write(out / 'backend_snapshot.json', snap)
            prep = dict(item=_ibm_item(case, method), version=version, case=case, method=method, prepared_utc=_ibm_now(),
                        backend=be.name, backend_version=snap.get('backend_version'),
                        isa_sha256=_ibm_sha(out / 'isa.qpy'), logical_sha256=_ibm_sha(out / 'logical.qpy'),
                        check_sha256=_ibm_sha(out / 'check.json'), snapshot_sha256=_ibm_sha(out / 'backend_snapshot.json'),
                        qubits=problem.n, theta=rec['theta'], angle_id=rec['angle_id'],
                        compile=dict(optimization_level=IBM_SETTINGS['optimization_level'], seed_transpiler=IBM_SETTINGS['seed_transpiler']),
                        compiled_two_qubit=rec['compiled_two_qubit'], versions=_ibm_versions())
            _ibm_write(out / 'prep.json', prep)
            _ibm_event(root, 'prepared', item=prep['item'], version=version, isa_sha256=prep['isa_sha256'])
            done.append(prep)
        return done


def _ibm_backend_snapshot(be):
    snap = dict(name=be.name, captured_utc=_ibm_now(), num_qubits=getattr(be, 'num_qubits', None),
                backend_version=str(getattr(be, 'backend_version', None)))
    try:
        props = be.properties()
        snap['properties'] = None if props is None else props.to_dict()
    except Exception as exc:
        snap['properties'] = f'unavailable: {type(exc).__name__}'
    try:
        snap['configuration'] = be.configuration().to_dict()
    except Exception as exc:
        snap['configuration'] = f'unavailable: {type(exc).__name__}'
    return snap


def _ibm_check_real_backend(be, study):
    if be.name != study['backend']:
        raise IBMStudyError(f'IBM returned backend {be.name!r}, not {study["backend"]!r}')
    try:
        sim = bool(getattr(be, 'simulator', False) or be.configuration().simulator)
    except Exception:
        sim = False
    if sim:
        raise IBMStudyError('The selected backend is a simulator; refusing to label it hardware')
    try:
        st = be.status()
        if not st.operational:
            raise IBMStudyError(f'Backend {be.name} is not operational right now; nothing was submitted')
    except IBMStudyError:
        raise
    except Exception as exc:
        raise IBMStudyError(f'Could not read backend status ({type(exc).__name__}); nothing was submitted') from None


def _ibm_current_prep(root, case, method):
    """Latest prepared version of an item, verified against its file hashes."""
    base = _ibm_paths(root)['prep'] / _ibm_item(case, method)
    versions = sorted((int(d.name[1:]), d) for d in base.glob('v*') if d.is_dir() and d.name[1:].isdigit()) if base.exists() else []
    if not versions:
        raise IBMStudyError(f'{case}/{method} is not prepared yet: run "ibm prepare" first')
    out = versions[-1][1]; prep = _ibm_read(out / 'prep.json')
    for f, k in (('isa.qpy', 'isa_sha256'), ('logical.qpy', 'logical_sha256'), ('check.json', 'check_sha256'),
                 ('backend_snapshot.json', 'snapshot_sha256')):
        if not (out / f).exists() or _ibm_sha(out / f) != prep[k]:
            raise IBMStudyError(f'Prepared file {out / f} is missing or changed; prepare again (nothing was submitted)')
    return prep, out


def _ibm_prep_fresh(prep, live):
    import datetime as _dt
    age = (_dt.datetime.now(_dt.timezone.utc) - _dt.datetime.fromisoformat(prep['prepared_utc'])).total_seconds()
    if live and age > IBM_SETTINGS['preparation_max_age_hours'] * 3600:
        raise IBMStudyError(f'Preparation of {prep["item"]} is {age / 3600:.1f} h old (limit '
                            f'{IBM_SETTINGS["preparation_max_age_hours"]} h). Run "ibm prepare" again; nothing was submitted.')
    return age


def _ibm_target_supports(be, isa, prep):
    if str(getattr(be, 'backend_version', None)) != str(prep['backend_version']):
        raise IBMStudyError('Backend version changed since preparation; run "ibm prepare" again (nothing was submitted)')
    tgt = be.target
    for inst in isa.data:
        if inst.operation.name == 'barrier':
            continue
        q = tuple(isa.find_bit(x).index for x in inst.qubits)
        if not tgt.instruction_supported(operation_name=inst.operation.name, qargs=q):
            raise IBMStudyError(f'The device no longer supports {inst.operation.name} on {q}; prepare again (nothing was submitted)')


# ----------------------------------------------------------------------------
# Submit one job, collect, reconcile, replace
# ----------------------------------------------------------------------------
_IBM_LOCAL_JOBS = {}   # fake studies only: local primitive jobs of this process


def ibm_submit(root, slot_id=None, remaining_seconds=None, say=print, _replaces=None, _reason=None):
    """Submit exactly ONE job for one slot, after every check. Returns the attempt record.
    Real studies do not wait for the result; run "ibm collect" afterwards."""
    with _IBMStudyLock(root):
        study = _ibm_load_study(root); live = study['kind'] == 'live'
        recs = _ibm_registry(root, study)
        unresolved = _ibm_unresolved(recs)
        if unresolved:
            names = ', '.join(f'{r["attempt_id"]} ({IBM_STATE_TEXT[r["state"]]}; accounting {r["accounting"]["status"]})' for r in unresolved)
            raise IBMStudyError(f'Unresolved attempt(s): {names}. Run "ibm collect" or "ibm reconcile" first; nothing was submitted.')
        slots = {s['slot_id']: s for s in study['slots']}
        by_slot = {}
        for r in sorted(recs.values(), key=lambda r: (r['slot_id'], r['attempt_no'])):
            by_slot.setdefault(r['slot_id'], []).append(r)
        if _replaces is None:
            if slot_id is None:
                free = [s for s in study['slots'] if s['slot_id'] not in by_slot]
                if not free:
                    raise IBMStudyError('Every planned slot has been attempted. Nothing to submit (use "ibm replace" for a failed slot).')
                slot = free[0]
            else:
                if slot_id not in slots:
                    raise IBMStudyError(f'Unknown slot {slot_id!r}')
                if slot_id in by_slot:
                    raise IBMStudyError(f'Slot {slot_id} already has an attempt; use "ibm replace" if it failed. Nothing was submitted.')
                slot = slots[slot_id]
            attempt_no = 1
        else:
            slot = slots[_replaces['slot_id']]; mine = by_slot.get(slot['slot_id'], [])
            if len(mine) != 1 or mine[-1]['attempt_id'] != _replaces['attempt_id'] or any(r.get('results') for r in mine):
                raise IBMStudyError(f'Slot {slot["slot_id"]} changed since the replacement was requested; nothing was submitted')
            attempt_no = 2
        cap = float(study['caps']['per_job_seconds'])
        budget = ibm_budget(study, recs)
        if budget['committed_seconds'] + cap > budget['study_cap_seconds']:
            raise IBMStudyError(f'Study budget: {budget["committed_seconds"]:.1f} s committed + {cap:.0f} s reservation would exceed '
                                f'the {budget["study_cap_seconds"]:.0f} s study cap. Nothing was submitted.')
        case, method = slot['case'], slot['method']
        prep, prep_dir = _ibm_current_prep(root, case, method)
        age = _ibm_prep_fresh(prep, live)
        isa = _ibm_load_qpy(prep_dir / 'isa.qpy')
        if isa.num_parameters:
            raise IBMStudyError('Prepared circuit has unbound parameters; refusing')
        allowance = None
        if live:
            if remaining_seconds is None or not _ibm_number(remaining_seconds):
                raise IBMStudyError('Give --remaining-seconds: the remaining Open Plan time shown on your IBM Instances page.')
            svc = _ibm_open_service(study)
            be = svc.backend(study['backend'])
            _ibm_check_real_backend(be, study); _ibm_target_supports(be, isa, prep)
            allowance = _ibm_allowance(svc); allowance['user_reported_remaining_seconds'] = float(remaining_seconds)
            avail = [float(remaining_seconds)] + ([allowance['remaining_seconds']] if allowance['available'] else [])
            if min(avail) < cap:
                raise IBMStudyError(f'Allowance: only {min(avail):.0f} s remaining (IBM-reported or your dashboard value), '
                                    f'less than the {cap:.0f} s job reservation. Nothing was submitted.')
            snap = _ibm_backend_snapshot(be)
        else:
            be = IBM_HOOKS['fake_backend'](); snap = None
        attempt_id = f'{slot["slot_id"]}__a{attempt_no}'
        tag = f'sim92-{hashlib.sha256((study["created_utc"] + attempt_id).encode()).hexdigest()[:16]}'
        rec = dict(schema=IBM_ATTEMPT_SCHEMA, attempt_id=attempt_id, slot_id=slot['slot_id'], attempt_no=attempt_no,
                   case=case, method=method, repetition=slot['repetition'], state='submitting', tag=tag, job_id=None,
                   created_utc=_ibm_now(), reservation_seconds=cap, planned_shots=slot['shots'], backend=be.name,
                   instance_crn=study.get('instance_crn'), data_kind=study['data_kind'],
                   accounting=dict(status='reserved', seconds=None, field='reservation (not usage)', history=[]),
                   prep=dict(item=prep['item'], version=prep['version'], isa_sha256=prep['isa_sha256'],
                             prepared_utc=prep['prepared_utc'], age_seconds=round(age, 1), theta=prep['theta'], angle_id=prep['angle_id']),
                   options=dict(max_execution_time=int(cap) if live else None, dynamical_decoupling=False, twirling_gates=False,
                                twirling_measure=False, job_tags=['sim9.2-rcrp', tag] if live else None),
                   budget_before=budget, allowance_before=allowance, analysis_role='primary' if attempt_no == 1 else 'replacement',
                   replaces=None if _replaces is None else _replaces['attempt_id'], replacement_reason=_reason,
                   results=None, identity=None, versions=_ibm_versions(), history=[])
        rec['history'].append(dict(utc=_ibm_now(), from_state=None, to_state='submitting', note='reservation recorded before dispatch'))
        if snap is not None:
            _ibm_write(_ibm_paths(root)['results'] / attempt_id / 'target_before_submission.json', snap)
        _ibm_write_new(_ibm_attempt_path(root, attempt_id), rec)          # reservation is durable BEFORE dispatch
        _ibm_event(root, 'reserved', attempt=attempt_id, seconds=cap)
        if live:
            options = dict(max_execution_time=int(cap), dynamical_decoupling={'enable': False},
                           twirling={'enable_gates': False, 'enable_measure': False},
                           environment={'job_tags': ['sim9.2-rcrp', tag]})
        else:
            options = dict(dynamical_decoupling={'enable': False}, twirling={'enable_gates': False, 'enable_measure': False},
                           simulator={'seed_simulator': _ibm_seed('fake-v2', attempt_id) % (2 ** 31)})
        try:
            sampler = IBM_HOOKS['sampler'](be, options)
            job = sampler.run([isa], shots=int(slot['shots']))
            job_id = job.job_id()
        except BaseException as exc:
            _ibm_transition(root, rec, 'uncertain', f'exception during dispatch ({type(exc).__name__}); the job may exist. '
                            'Run "ibm reconcile"; never resubmit blindly.')
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            raise IBMStudyError(f'Submission outcome uncertain for {attempt_id} ({type(exc).__name__}). '
                                f'Run "ibm reconcile --attempt {attempt_id}". Its {cap:.0f} s reservation is kept.') from None
        side = _ibm_paths(root)['registry'] / f'{attempt_id}.jobid'
        try:
            with open(side, 'w') as f:
                f.write(str(job_id)); f.flush(); os.fsync(f.fileno())
        except OSError:
            pass                                                         # the record write below is the primary copy
        _ibm_transition(root, rec, 'submitted', 'IBM accepted the job', job_id=str(job_id))
        try:
            side.unlink()
        except OSError:
            pass
        if not live:
            _IBM_LOCAL_JOBS[str(job_id)] = job
        say(f'Submitted ONE job for {attempt_id}: {job_id}' + ('' if live else ' (local fake device; simulation)'))
    if not live:
        ibm_collect(root, attempt_id, say=say)
        rec = _ibm_read(_ibm_attempt_path(root, attempt_id))
    return rec


def _ibm_pub_circuit_and_shots(job):
    try:
        pubs = job.inputs.get('pubs')
    except Exception as exc:
        return None, None, f'job.inputs unavailable ({type(exc).__name__})'
    if not isinstance(pubs, (list, tuple)) or len(pubs) != 1:
        return None, None, f'job inputs have {None if pubs is None else len(pubs)} PUBs, expected 1'
    pub = pubs[0]
    if hasattr(pub, 'circuit'):
        return pub.circuit, getattr(pub, 'shots', None), None
    if isinstance(pub, (list, tuple)) and pub:
        shots = pub[2] if len(pub) > 2 else None
        return pub[0], shots, None
    return None, None, f'unrecognised PUB type {type(pub).__name__}'


def _ibm_verify_remote(job, rec, isa, study):
    """Identity of a remote job: backend, unique tag, instance, input circuit (== frozen ISA) and shots."""
    ident = dict(checked_utc=_ibm_now())
    be = job.backend(); name = getattr(be, 'name', be)
    if name != rec['backend']:
        raise IBMStudyError(f'Job {rec["job_id"]} ran on {name!r}, not {rec["backend"]!r}; refusing to use it')
    ident['backend'] = name
    tags = list(getattr(job, 'tags', []) or [])
    if rec['tag'] not in tags:
        raise IBMStudyError(f'Job {rec["job_id"]} does not carry this attempt\'s unique tag; refusing to use it')
    ident['tag'] = rec['tag']
    try:
        inst = job.instance
    except Exception:
        inst = None
    if inst is not None and study.get('instance_crn') and inst != study['instance_crn']:
        raise IBMStudyError(f'Job {rec["job_id"]} belongs to a different instance; refusing to use it')
    ident['instance'] = inst if inst is not None else 'not reported by SDK'
    circ, shots, why = _ibm_pub_circuit_and_shots(job)
    if circ is None:
        ident['input_circuit'] = f'not verifiable: {why}'
    else:
        if circ != isa:
            raise IBMStudyError(f'Job {rec["job_id"]} input circuit differs from the frozen prepared circuit; refusing to use it')
        ident['input_circuit'] = 'equal to frozen ISA circuit'
    if shots is not None and int(shots) != int(rec['planned_shots']):
        raise IBMStudyError(f'Job {rec["job_id"]} requested {shots} shots, not {rec["planned_shots"]}; refusing to use it')
    ident['input_shots'] = shots if shots is not None else 'not reported by SDK'
    return ident


def _ibm_save_results(root, rec, job, problem, table, bay):
    """Save ordered shots once. Repeated collection never duplicates or rescales them."""
    out = _ibm_paths(root)['results'] / rec['attempt_id']; out.mkdir(parents=True, exist_ok=True)
    states_path = out / 'states.npy'
    if rec.get('results'):
        if not states_path.exists() or _ibm_sha(states_path) != rec['results']['states_sha256']:
            raise IBMStudyError(f'Saved results for {rec["attempt_id"]} are missing or changed; stopping')
        return rec['results']
    result = job.result()
    if len(result) != 1:
        raise IBMStudyError(f'Job {rec["job_id"]} returned {len(result)} results, expected 1')
    data = result[0].data
    if not hasattr(data, 'decision'):
        raise IBMStudyError('Result has no "decision" register; it is not this study\'s circuit')
    ba = data.decision
    if ba.num_bits != problem.n:
        raise IBMStudyError(f'Decision register has {ba.num_bits} bits, expected {problem.n}')
    bits = ba.get_bitstrings()
    states = np.asarray([int(b, 2) for b in bits], dtype=np.int64)
    tmp = out / f'.states.{os.getpid()}.npy'
    np.save(tmp, states); os.replace(tmp, states_path); _ibm_fsync_dir(out)
    raw = dict(counts=ba.get_counts(), executed_shots=len(bits), planned_shots=rec['planned_shots'])
    try:
        raw['pub_metadata'] = result[0].metadata; raw['result_metadata'] = getattr(result, 'metadata', None)
    except Exception:
        pass
    _ibm_write(out / 'raw_result.json', raw)
    score = _ibm_score(states, table, problem, bay)
    res = dict(states_file=str(states_path.relative_to(Path(root))), states_sha256=_ibm_sha(states_path),
               executed_shots=int(len(states)), shot_count_matches_plan=len(states) == rec['planned_shots'],
               saved_utc=_ibm_now(), score=score)
    return res


def ibm_collect(root, attempt_id=None, say=print):
    """Fetch results and accounting for submitted attempts. Never submits. Safe to repeat."""
    changed = []
    with _IBMStudyLock(root):
        study = _ibm_load_study(root); live = study['kind'] == 'live'
        recs = _ibm_registry(root, study)
        todo = [r for r in recs.values() if (attempt_id is None or r['attempt_id'] == attempt_id)
                and r.get('job_id') and (r['state'] in ('submitted', 'awaiting', 'failed', 'cancelled') or not _ibm_accounting_final(r))]
        if attempt_id is not None and attempt_id not in recs:
            raise IBMStudyError(f'Unknown attempt {attempt_id}')
        svc = _ibm_open_service(study) if (live and todo) else None
        for rec in todo:
            prep_dir = _ibm_paths(root)['prep'] / rec['prep']['item'] / f'v{rec["prep"]["version"]}'
            isa = _ibm_load_qpy(prep_dir / 'isa.qpy')
            if _ibm_sha(prep_dir / 'isa.qpy') != rec['prep']['isa_sha256']:
                raise IBMStudyError(f'The prepared circuit used by {rec["attempt_id"]} changed on disk; stopping')
            try:
                job = svc.job(rec['job_id']) if live else _IBM_LOCAL_JOBS[rec['job_id']]
            except KeyError:
                say(f'{rec["attempt_id"]}: local fake job is gone (different process); marked failed, no IBM usage.')
                rec['accounting'] = dict(status='final_zero', seconds=0.0, field='local simulator: no IBM QPU usage',
                                         history=rec['accounting'].get('history', []))
                _ibm_transition(root, rec, 'failed', 'local fake job not available in this process'); continue
            except Exception as exc:
                say(f'{rec["attempt_id"]}: could not reach job {rec["job_id"]} ({type(exc).__name__}); reservation kept, try later.')
                continue
            try:
                if not live:
                    job.result()                                         # local simulation: wait for it to finish
                status = _ibm_status_str(job)
            except Exception as exc:
                say(f'{rec["attempt_id"]}: status unavailable ({type(exc).__name__}); try later.'); continue
            if live:
                rec['identity'] = _ibm_verify_remote(job, rec, isa, study)
            else:
                rec['identity'] = dict(local=True, input_circuit='local primitive job of this process', checked_utc=_ibm_now())
            terminal = status in IBM_TERMINAL_JOB
            new_state = rec['state']
            if status == 'DONE':
                bay, problem, theta, angle_id = ibm_build(rec['case'], rec['method'])
                if [float(t) for t in theta] != [float(t) for t in rec['prep']['theta']]:
                    raise IBMStudyError('Frozen angles differ from the prepared angles; stopping')
                try:
                    rec['results'] = _ibm_save_results(root, rec, job, problem, evaluation_table(problem), bay)
                except IBMStudyError:
                    raise
                except Exception as exc:
                    say(f'{rec["attempt_id"]}: result retrieval failed ({type(exc).__name__}); job ID and reservation kept. Run collect again.')
                    _ibm_event(root, 'result_retrieval_failed', attempt=rec['attempt_id'], error=type(exc).__name__)
                    continue
                new_state = 'awaiting'
            elif status == 'ERROR':
                new_state = 'failed'
                try:
                    rec['error_message'] = str(job.error_message())[:500]
                except Exception:
                    pass
            elif status == 'CANCELLED':
                new_state = 'cancelled'
            if terminal:
                if live:
                    acc = ibm_read_usage(job, terminal=True)
                else:
                    acc = dict(observed_utc=_ibm_now(), status='final_zero', seconds=0.0, field='local simulator: no IBM QPU usage')
                hist = rec['accounting'].get('history', []) + [acc]
                if rec['accounting']['status'] in ('final', 'final_zero'):
                    acc = dict(rec['accounting'])                       # never downgrade a final value
                rec['accounting'] = dict(status=acc['status'], seconds=acc.get('seconds'), field=acc.get('field'),
                                         raw_usage=acc.get('raw_usage'), sdk_job_usage=acc.get('sdk_job_usage'),
                                         error=acc.get('error'), observed_utc=acc['observed_utc'], history=hist)
                if new_state == 'awaiting' and rec['accounting']['status'] in ('final', 'final_zero'):
                    new_state = 'completed'
            note = f'collect: IBM status {status}; accounting {rec["accounting"]["status"]}'
            _ibm_transition(root, rec, new_state, note)
            changed.append(rec['attempt_id'])
            r = rec.get('results') or {}
            sc = r.get('score') or {}
            say(f'{rec["attempt_id"]}: {status}, state {new_state}, accounting {rec["accounting"]["status"]}'
                + (f', {rec["accounting"]["seconds"]} s' if rec['accounting'].get('seconds') is not None else '')
                + (f', legal {sc["accepted_rate"]:.4f}, optimal {sc["replay_optimal_rate"]:.4f}' if sc else ''))
        ibm_summarize(root, say=lambda s: None, _locked=True)
    return changed


def ibm_reconcile(root, attempt_id, confirm_no_job=False, say=print):
    """Resolve an 'uncertain' attempt using IBM's job-tag search (each attempt has a unique tag).
    Exactly one match is verified and attached. Zero matches never release the reservation unless the user
    confirms after two searches at least 10 minutes apart. More than one match stops for manual review."""
    import datetime as _dt
    with _IBMStudyLock(root):
        study = _ibm_load_study(root); recs = _ibm_registry(root, study)
        rec = recs.get(attempt_id)
        if rec is None:
            raise IBMStudyError(f'Unknown attempt {attempt_id}')
        if rec['state'] != 'uncertain':
            raise IBMStudyError(f'{attempt_id} is {IBM_STATE_TEXT[rec["state"]]}, not uncertain; use "ibm collect"')
        if study['kind'] != 'live':
            rec['accounting'] = dict(status='final_zero', seconds=0.0, field='local simulator: no IBM QPU usage', history=rec['accounting']['history'])
            _ibm_transition(root, rec, 'reconciled_no_job', 'fake study: local jobs are never charged'); return rec
        svc = _ibm_open_service(study)
        created = _dt.datetime.fromisoformat(rec['created_utc']) - _dt.timedelta(minutes=5)
        try:
            jobs = list(svc.jobs(job_tags=[rec['tag']], backend_name=rec['backend'], instance=study['instance_crn'],
                                 limit=10, created_after=created))
        except Exception as exc:
            raise IBMStudyError(f'IBM job search failed ({type(exc).__name__}); nothing changed. Try again later.') from None
        searches = rec.setdefault('reconcile_searches', [])
        searches.append(dict(utc=_ibm_now(), matches=[j.job_id() for j in jobs]))
        if len(jobs) == 1:
            job = jobs[0]; rec['job_id'] = job.job_id()
            prep_dir = _ibm_paths(root)['prep'] / rec['prep']['item'] / f'v{rec["prep"]["version"]}'
            rec['identity'] = _ibm_verify_remote(job, rec, _ibm_load_qpy(prep_dir / 'isa.qpy'), study)
            _ibm_transition(root, rec, 'submitted', 'reconciled: exactly one IBM job carries this attempt\'s unique tag')
            say(f'{attempt_id}: found job {rec["job_id"]}. Run "ibm collect" next.'); return rec
        if len(jobs) > 1:
            _ibm_write(_ibm_attempt_path(root, attempt_id), rec)
            raise IBMStudyError(f'{len(jobs)} IBM jobs carry the tag of {attempt_id}: {searches[-1]["matches"]}. '
                                'This should not happen; check Workloads and contact IBM. Nothing changed.')
        zero = [s for s in searches if not s['matches']]
        gap = ((_dt.datetime.fromisoformat(zero[-1]['utc']) - _dt.datetime.fromisoformat(zero[0]['utc'])).total_seconds()
               if len(zero) >= 2 else 0.0)
        if confirm_no_job and len(zero) >= 2 and gap >= _IBM_RECONCILE_MIN_GAP_SECONDS:
            rec['accounting'] = dict(status='final_zero', seconds=0.0, history=rec['accounting']['history'],
                                     field=f'no job: {len(zero)} tag searches over {gap / 60:.0f} min found none; confirmed by the user',
                                     observed_utc=_ibm_now())
            _ibm_transition(root, rec, 'reconciled_no_job', 'user confirmed no job after repeated tag searches')
            say(f'{attempt_id}: reconciled as no job; its reservation is released.'); return rec
        _ibm_write(_ibm_attempt_path(root, attempt_id), rec)
        say(f'{attempt_id}: no IBM job with its tag yet ({len(zero)} empty search(es) so far). The reservation is kept. '
            'Check IBM Workloads, wait at least 10 minutes, search again, and only then use --confirm-no-job.')
        return rec


def ibm_replace(root, slot_id, reason, remaining_seconds=None, say=print):
    """Replace exactly one failed/cancelled slot with ONE new job (at most one replacement per slot)."""
    if not reason or not str(reason).strip():
        raise IBMStudyError('Give --reason (why the original attempt failed); it is kept in the record')
    with _IBMStudyLock(root):
        study = _ibm_load_study(root); recs = _ibm_registry(root, study)
        mine = sorted((r for r in recs.values() if r['slot_id'] == slot_id), key=lambda r: r['attempt_no'])
        if not mine:
            raise IBMStudyError(f'Slot {slot_id} has no attempt to replace (use "ibm submit")')
        if any(r.get('results') for r in mine):
            raise IBMStudyError(f'Slot {slot_id} already has results; replacing it would mean choosing between result sets. Refused.')
        if len(mine) >= 2:
            raise IBMStudyError(f'Slot {slot_id} has already been replaced once; no further replacement is allowed')
        last = mine[-1]
        if last['state'] not in ('failed', 'cancelled', 'reconciled_no_job'):
            raise IBMStudyError(f'{last["attempt_id"]} is {IBM_STATE_TEXT[last["state"]]}; only a failed/cancelled (or reconciled '
                                'no-job) attempt can be replaced')
        if not _ibm_accounting_final(last):
            raise IBMStudyError(f'{last["attempt_id"]} accounting is {last["accounting"]["status"]}; wait for final accounting '
                                '("ibm collect") before replacing')
    say(f'Replacing {last["attempt_id"]} with ONE new job. Reason: {reason}')
    return ibm_submit(root, remaining_seconds=remaining_seconds, say=say, _replaces=last, _reason=str(reason))


# ----------------------------------------------------------------------------
# Status and summary (work for empty and partial studies)
# ----------------------------------------------------------------------------
def ibm_status(root, say=print):
    study = _ibm_load_study(root); recs = _ibm_registry(root, study, recover=False)
    b = ibm_budget(study, recs); un = _ibm_unresolved(recs)
    attempted = {r['slot_id'] for r in recs.values()}
    say(f"Study {Path(root).name}: {study['kind']} on {study['backend']}; {len(attempted)}/{len(study['slots'])} slots attempted.")
    say(f"QPU seconds: final {b['final_confirmed_seconds']:.1f}, still reserved {b['unresolved_reserved_seconds']:.1f}, "
        f"study cap {b['study_cap_seconds']:.0f}. (IBM's own remaining allowance is separate; check the Instances page.)")
    for r in sorted(recs.values(), key=lambda r: r['attempt_id']):
        a = r['accounting']
        say(f"  {r['attempt_id']:<46} {IBM_STATE_TEXT[r['state']]:<44} accounting {a['status']}"
            + (f" {a['seconds']} s" if a.get('seconds') is not None else ''))
    stale = [r for r in recs.values() if r['state'] == 'submitting']
    if stale:
        say('  Note: a submission is in progress or was interrupted; the next command will mark it uncertain if its process is gone.')
    if un:
        say('Unresolved: ' + ', '.join(r['attempt_id'] for r in un) + ' -> run "ibm collect" (or "ibm reconcile" if uncertain).')
    nxt = next((s['slot_id'] for s in study['slots'] if s['slot_id'] not in attempted), None)
    say(f'Next unstarted slot: {nxt}' if nxt else 'All slots have been attempted.')
    return dict(budget=b, unresolved=[r['attempt_id'] for r in un], next_slot=nxt, attempts=len(recs))


def ibm_summarize(root, say=print, _locked=False):
    import csv
    study = _ibm_load_study(root); recs = _ibm_registry(root, study, recover=False)
    rows = []; items = {}
    for s in study['slots']:
        mine = sorted((r for r in recs.values() if r['slot_id'] == s['slot_id']), key=lambda r: r['attempt_no'])
        analysed = next((r for r in mine if r.get('results')), None)
        items.setdefault((s['case'], s['method']), []).append((s, mine, analysed))
    for (case, method), entries in items.items():
        used = [a for _, _, a in entries if a is not None]
        row = dict(case=case, method=method, backend=study['backend'], data_kind=study['data_kind'],
                   planned_jobs=len(entries), attempted_slots=sum(1 for _, m, _ in entries if m),
                   analysed_jobs=len(used), failed_or_cancelled_attempts=sum(1 for _, m, _ in entries for r in m if r['state'] in ('failed', 'cancelled')),
                   replacement_attempts=sum(1 for _, m, _ in entries for r in m if r['attempt_no'] > 1))
        if used:
            bay, problem, theta, angle_id = ibm_build(case, method); table = evaluation_table(problem)
            pooled = np.concatenate([np.load(Path(root) / a['results']['states_file']) for a in used])
            sc = _ibm_score(pooled, table, problem, bay)
            per = [a['results']['score'] for a in used]
            rng = np.random.default_rng(_ibm_seed('uniform-matched-v2', case, method, len(pooled)))
            uni = _ibm_score(rng.integers(0, 1 << problem.n, len(pooled)), table, problem, bay)
            row.update(shots=sc['shots'], accepted_rate=sc['accepted_rate'], accepted_ci95=sc['accepted_rate_ci95'],
                       replay_optimal_rate=sc['replay_optimal_rate'], replay_optimal_ci95=sc['replay_optimal_rate_ci95'],
                       accepted_sd_between_jobs=float(np.std([p['accepted_rate'] for p in per], ddof=1)) if len(per) > 1 else None,
                       optimal_sd_between_jobs=float(np.std([p['replay_optimal_rate'] for p in per], ddof=1)) if len(per) > 1 else None,
                       best_relocations=sc['best_accepted_relocations'], median_relocations=sc['median_accepted_relocations'],
                       matched_uniform_accepted=uni['accepted_rate'], matched_uniform_optimal=uni['replay_optimal_rate'])
        else:
            row.update(shots=0, accepted_rate=None, accepted_ci95=None, replay_optimal_rate=None, replay_optimal_ci95=None,
                       accepted_sd_between_jobs=None, optimal_sd_between_jobs=None, best_relocations=None,
                       median_relocations=None, matched_uniform_accepted=None, matched_uniform_optimal=None)
        rows.append(row)
    b = ibm_budget(study, recs)
    summary = dict(schema='sim9.2-ibm-summary/1', created_utc=_ibm_now(), data_kind=study['data_kind'], backend=study['backend'],
                   analysis_rule=IBM_ANALYSIS_RULE, budget=b, attempts=len(recs), rows=rows,
                   complete=all(r['analysed_jobs'] == r['planned_jobs'] for r in rows))
    _ibm_write(Path(root) / 'summary.json', summary)
    fields = list(rows[0]) if rows else ['case']
    tmp = Path(root) / f'.summary.{os.getpid()}.csv'
    with open(tmp, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
    os.replace(tmp, Path(root) / 'summary.csv')
    for r in rows:
        say(f"{r['case']:<18} {r['method']:<9} {r['analysed_jobs']}/{r['planned_jobs']} jobs analysed"
            + (f"  legal {r['accepted_rate']:.4f} (random {r['matched_uniform_accepted']:.4f})  optimal {r['replay_optimal_rate']:.4f}"
               if r['accepted_rate'] is not None else '  no results yet'))
    say(f"Summary written: {Path(root) / 'summary.json'} ({'complete' if summary['complete'] else 'INCOMPLETE study'})")
    return summary


# ----------------------------------------------------------------------------
# Account helper and command line
# ----------------------------------------------------------------------------
def ibm_account(name, overwrite=False, say=print):
    """Save a NAMED account with an explicit Open Plan CRN. The API key is read with a hidden prompt and
    stored only in Qiskit's local account file (~/.qiskit/qiskit-ibm.json), never in the study."""
    import getpass
    from qiskit_ibm_runtime import QiskitRuntimeService
    crn = input('Open Plan instance CRN (from IBM Instances page): ').strip()
    if not crn.startswith('crn:'):
        raise IBMStudyError('That is not an IBM Cloud CRN (it should start with "crn:")')
    key = getpass.getpass('IBM API key (hidden): ').strip()
    if not key:
        raise IBMStudyError('No API key entered')
    try:
        QiskitRuntimeService.save_account(channel='ibm_quantum_platform', token=key, instance=crn, name=name,
                                          overwrite=overwrite, set_as_default=False)
    except Exception as exc:
        raise IBMStudyError(f'Could not save the account ({type(exc).__name__}). If the name exists, use --overwrite only on purpose.') from None
    del key
    say(f'Saved account {name!r} for this CRN (key not shown). Next: python Sim9_2.py ibm backends --account {name} --instance <CRN>')
    return crn


def ibm_backends(name, crn, say=print):
    study = dict(kind='live', account_name=name, instance_crn=crn)
    svc = _ibm_open_service(study)
    say('Instance verified as Open Plan. Real devices you can use (no job is sent):')
    for b in svc.backends(simulator=False, operational=True):
        try:
            q = b.status().pending_jobs
        except Exception:
            q = '?'
        say(f'  {b.name:<16} qubits {b.num_qubits:<5} queued jobs {q}')
    a = _ibm_allowance(svc)
    say(f"IBM-reported remaining usage: {a['remaining_seconds']} s" if a['available'] else
        'IBM did not report remaining usage; read it on the Instances page.')


def ibm_main(argv):
    ap = argparse.ArgumentParser(prog='Sim9_2.py ibm', description='IBM hardware study (Sim9.2): one explicit job per submit, '
                                 'persistent registry, budget reservations, reconcile, single-slot replacement.')
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('plan', help='print the declared protocol and settings')
    s = sub.add_parser('check', help='fake-device circuit check for one bay/method (no account)')
    s.add_argument('--case', required=True); s.add_argument('--method', choices=list(IBM_LADDER), required=True)
    s.add_argument('--out', default='ibm_checks')
    s = sub.add_parser('account', help='save a named IBM account with an explicit Open Plan CRN (hidden key)')
    s.add_argument('--account', required=True); s.add_argument('--overwrite', action='store_true')
    s = sub.add_parser('backends', help='verify the Open Plan instance and list devices (no job)')
    s.add_argument('--account', required=True); s.add_argument('--instance', required=True)
    s = sub.add_parser('init', help='create a new study folder')
    s.add_argument('--study', required=True); s.add_argument('--backend', required=True, help="'fake' or an exact device name")
    s.add_argument('--account'); s.add_argument('--instance'); s.add_argument('--approval')
    s = sub.add_parser('prepare', help='compile and check the circuits for the study backend (no job)')
    s.add_argument('--study', required=True); s.add_argument('--item', action='append', help='CASE:METHOD (default: all 8)')
    s = sub.add_parser('submit', help='submit exactly ONE job (next unstarted slot, or --slot)')
    s.add_argument('--study', required=True); s.add_argument('--slot'); s.add_argument('--remaining-seconds', type=float)
    s = sub.add_parser('collect', help='fetch results and accounting (never submits)')
    s.add_argument('--study', required=True); s.add_argument('--attempt')
    s = sub.add_parser('reconcile', help='resolve an uncertain submission by its unique IBM job tag')
    s.add_argument('--study', required=True); s.add_argument('--attempt', required=True); s.add_argument('--confirm-no-job', action='store_true')
    s = sub.add_parser('replace', help='replace ONE failed/cancelled slot with one new job')
    s.add_argument('--study', required=True); s.add_argument('--slot', required=True); s.add_argument('--reason', required=True)
    s.add_argument('--remaining-seconds', type=float)
    s = sub.add_parser('status', help='show every attempt, accounting and the next slot')
    s.add_argument('--study', required=True)
    s = sub.add_parser('summarize', help='write summary.json/csv (works for partial studies)')
    s.add_argument('--study', required=True)
    for old in ('run', 'retrieve'):
        sub.add_parser(old, help='removed in Sim9.2')
    a = ap.parse_args(argv)
    try:
        if a.cmd == 'plan':
            jobs = len(ibm_slots())
            print(json.dumps(dict(settings=IBM_SETTINGS, order=IBM_ORDER, jobs=jobs,
                                  total_shots=sum(s['shots'] for s in ibm_slots()), analysis_rule=IBM_ANALYSIS_RULE,
                                  replacement_rule=IBM_REPLACEMENT_RULE,
                                  estimated_qpu_seconds=round(qpu_seconds_estimate(jobs, IBM_SETTINGS['shots_per_batch']), 1)), indent=2))
        elif a.cmd == 'check':
            rec = ibm_check(a.case, a.method, 'fake', Path(a.out) / f'{a.case}__{a.method}__fake')[0]
            return 0 if rec['passed'] else 1
        elif a.cmd == 'account':
            ibm_account(a.account, a.overwrite)
        elif a.cmd == 'backends':
            ibm_backends(a.account, a.instance)
        elif a.cmd == 'init':
            ibm_init(a.study, a.backend, a.account, a.instance, a.approval)
        elif a.cmd == 'prepare':
            items = None if not a.item else [tuple(x.split(':', 1)) for x in a.item]
            ibm_prepare(a.study, items)
        elif a.cmd == 'submit':
            ibm_submit(a.study, a.slot, a.remaining_seconds)
        elif a.cmd == 'collect':
            ibm_collect(a.study, a.attempt)
        elif a.cmd == 'reconcile':
            ibm_reconcile(a.study, a.attempt, a.confirm_no_job)
        elif a.cmd == 'replace':
            ibm_replace(a.study, a.slot, a.reason, a.remaining_seconds)
        elif a.cmd == 'status':
            ibm_status(a.study)
        elif a.cmd == 'summarize':
            ibm_summarize(a.study)
        else:
            print('"ibm run" and "ibm retrieve" were replaced in Sim9.2 by: init, prepare, submit, collect, reconcile, replace, status, summarize.')
            return 2
        return 0
    except IBMStudyError as exc:
        print(f'STOP: {exc}', file=sys.stderr); return 2
    except KeyboardInterrupt:
        print('Interrupted. Run "ibm status": an interrupted submission is kept as uncertain, never resubmitted.', file=sys.stderr); return 130
    except Exception as exc:          # network/SDK errors can carry request details: print the type only
        print(f'STOP: unexpected {type(exc).__name__}. Nothing further was submitted. Run "ibm status".', file=sys.stderr); return 2

def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == 'hardware':
        return hardware_main(argv[1:])
    if argv and argv[0] == 'ibm':                 # FIX (Sim9) 18
        return ibm_main(argv[1:])
    ap = argparse.ArgumentParser(prog='rcrp_qaoa_suite.py', description='rCRP QAOA suite: GUI, runs, self-test, IBM workflow.',
                                 epilog='Subcommand "hardware" takes the original hardware_solver.py options; see "hardware -h". '
                                        'Subcommand "ibm" runs the declared IBM study protocol; see "ibm -h".')
    sub = ap.add_subparsers(dest='cmd')
    sub.add_parser('gui', help='open the window (default)')
    s = sub.add_parser('selftest', help='built-in correctness checks'); s.add_argument('--quick', action='store_true')
    sub.add_parser('fixes', help='list the bugs fixed in this merged version')
    s = sub.add_parser('list', help='list embedded benchmark bays'); s.add_argument('--family')
    s = sub.add_parser('run', help='one QAOA experiment, JSON to stdout or --out')
    _bay_args(s)
    s.add_argument('--method', choices=list(METHODS), default='predicate')
    s.add_argument('--presolve', choices=['standard', 'strong'], default='standard',
                   help='standard: the validated release model (default); strong: exact for the best plan, separate model')
    s.add_argument('--synthesis', choices=['pauli', 'mcp'], default='pauli')
    s.add_argument('--angles', choices=list(ANGLE_MODES), default='transfer')
    s.add_argument('--backend', choices=list(BACKENDS), default='ideal')
    s.add_argument('--depth', type=int, default=2); s.add_argument('--shots', type=int, default=1024)
    s.add_argument('--jobs', type=int, default=40); s.add_argument('--seed', type=int, default=0)
    s.add_argument('--p2', type=float, default=3e-3); s.add_argument('--readout', type=float, default=0.01)
    s.add_argument('--histories', type=int, default=200); s.add_argument('--max-qubits', type=int, default=20)
    s.add_argument('--no-baselines', action='store_true'); s.add_argument('--milp', action='store_true')
    s.add_argument('--out', help='write the full result JSON here'); s.add_argument('--quiet', action='store_true')
    s = sub.add_parser('resources', help='compare encodings for a bay (no simulation)')
    _bay_args(s); s.add_argument('--depth', type=int, default=1)
    s = sub.add_parser('export', help='write an encoding (and circuit) to a folder')
    _bay_args(s); s.add_argument('--method', choices=['predicate', 'hybrid', 'galle', 'coherent'], default='galle')
    s.add_argument('--presolve', choices=['standard', 'strong'], default='standard')
    s.add_argument('--out', required=True); s.add_argument('--depth', type=int, default=1)
    a = ap.parse_args(argv)

    if a.cmd in (None, 'gui'):
        return launch_gui()
    if a.cmd == 'fixes':
        print(FIXES); return 0
    if a.cmd == 'selftest':
        p, f = selftest(quick=a.quick); return 1 if f else 0
    if a.cmd == 'list':
        for r in catalog():
            if a.family and r['family'] != a.family:
                continue
            ref = r['reference']
            print(f"{r['id']:<16} C={r['containers']:<4} S={r['stacks']:<3} T={r['capacity']:<3} "
                  + (f"published {ref['best_known']}{'' if ref['proven_optimal'] else ' (best known)'}" if ref else ''))
        return 0
    cfg = _bay_from_args(a)
    if a.cmd in ('resources', 'export'):
        name, bay, height, _ = resolve_bay(cfg)
        if a.cmd == 'resources':
            print(f'{name}: {len(bay)} stacks, capacity {height}, {sum(map(len, bay))} containers, depth p={a.depth}')
            for r in resource_report(bay, height, a.depth):
                f = lambda k: '-' if r.get(k) is None else f'{r[k]:,}'
                print(f"  {r['method']:<40} qubits {f('qubits'):>7}  measured {f('measured'):>6}  "
                      f"logical CX {f('cx'):>9}   {r.get('note', '')}")
            return 0
        files = export_model(bay, height, a.method, a.out, a.depth, presolve=a.presolve)
        print(f'wrote {len(files)} files to {a.out}: ' + ', '.join(files)); return 0
    cfg.method, cfg.synthesis, cfg.angles, cfg.backend, cfg.presolve = a.method, a.synthesis, a.angles, a.backend, a.presolve
    cfg.depth, cfg.shots, cfg.jobs, cfg.seed = a.depth, a.shots, a.jobs, a.seed
    cfg.p2, cfg.readout, cfg.histories, cfg.max_qubits = a.p2, a.readout, a.histories, a.max_qubits
    cfg.baselines, cfg.milp = not a.no_baselines, a.milp
    r = run(cfg, log=(lambda s: None) if a.quiet else (lambda s: print(s, file=sys.stderr, flush=True)))
    text = json.dumps(r, indent=2, default=_json_default)
    if a.out:
        Path(a.out).write_text(text + '\n'); print(summary_text(r))
    else:
        print(summary_text(r) if not a.quiet else text)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except BrokenPipeError:          # e.g. piped into head
        sys.stderr.close(); raise SystemExit(0)
