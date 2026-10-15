# Sequential Robust Transport Observation Design

This extension asks an incremental design question:

> given observations already committed, where should the next measurement be taken?

Starting from a fixed seed design, each candidate space-time observation from a finite pool is added temporarily and scored with the existing finite-scenario robust Fisher-information layer.

At each step, the accepted observation maximises worst-case D-optimality across the declared diffusion/decay scenarios. Deterministic secondary criteria use mean D-optimality, worst-case conditioning, then the space-time index.

The algorithm returns the complete step-by-step history, not only the final design.

The regression contract requires:
- no duplicate observations;
- fixed declared candidate pool;
- deterministic choices independent of pool ordering;
- non-decreasing worst-case D-optimality across accepted additions;
- explicit failure when the pool is too small.

This is greedy finite-pool augmentation. It is not a proof of globally optimal fixed-budget design, continuous design optimisation, or a real field sampling recommendation.
