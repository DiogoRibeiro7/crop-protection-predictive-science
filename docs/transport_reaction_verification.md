# Verified Transport-Reaction Forward Model

This note documents a stand-alone synthetic scientific-computing demonstration.
It does **not** use the empirical hop or Bipolaris datasets, does not reopen the
Bipolaris model-selection programme, and does not make a pesticide-use claim.

## Governing equation

The forward problem is

\[
\frac{\partial c}{\partial t}
=
D\frac{\partial^2 c}{\partial x^2}
-
k c,
\]

for \(x\in[0,L]\), with constant diffusion coefficient \(D\ge 0\),
first-order decay rate \(k\ge 0\), and homogeneous no-flux boundaries

\[
\frac{\partial c}{\partial x}(0,t)
=
\frac{\partial c}{\partial x}(L,t)
=
0.
\]

The implementation accepts a non-negative finite initial concentration on a
cell-centred finite-volume grid.

## Numerical scheme

Space is discretised with conservative finite volumes. The boundary cells use
the no-flux face condition directly; there are no ghost-cell source terms.
Time integration uses implicit Euler,

\[
\left(I-\Delta t\,D L_h+\Delta t\,kI\right)c^{n+1}=c^n,
\]

which produces a tridiagonal linear system solved with SciPy's banded solver.

The method is deliberately simple and auditable. The purpose is verification of
the scientific-computing workflow, not algorithmic novelty.

## Verification hierarchy

### 1. Uniform analytic limit

For spatially uniform initial concentration \(c(x,0)=c_0\), diffusion vanishes
and the continuous solution is

\[
c(t)=c_0 e^{-kt}.
\]

The test suite checks convergence of the implicit-Euler result to that analytic
limit at a sufficiently small time step.

### 2. Admissible state

For non-negative initial conditions, computed states are required to remain:

- finite;
- non-negative up to a small numerical tolerance.

A materially negative or non-finite state is treated as a solver failure rather
than silently accepted.

### 3. Discrete mass balance

Because the finite-volume diffusion fluxes telescope under no-flux boundaries,

\[
M^{n+1}(1+k\Delta t)-M^n=0,
\]

where

\[
M^n=\Delta x\sum_i c_i^n.
\]

The solver records that residual at every step. With \(k=0\), total mass should
therefore be conserved to floating-point precision.

### 4. Cosine-mode analytic solution

The no-flux eigenfunctions are cosine modes. For

\[
c(x,0)=\bar c + A\cos\left(\frac{m\pi x}{L}\right),
\]

the continuous solution is

\[
c(x,t)
=
\bar c\,e^{-kt}
+
A\exp\left[-\left(k+D\left(\frac{m\pi}{L}\right)^2\right)t\right]
\cos\left(\frac{m\pi x}{L}\right).
\]

The test suite refines space and time together and requires the relative error
against this analytic solution to decrease monotonically.

## Scope boundary

This forward model is synthetic methods evidence. It demonstrates:

- conservation-aware discretisation;
- verification against known solutions;
- numerical diagnostics;
- typed scientific software.

It does not establish transport parameters for any real crop-protection system,
does not use Piedade field data, and does not alter any empirical conclusion in
this repository.

Inverse parameter recovery, observation-noise calibration and identifiability
analysis remain separate work under issue #45.
