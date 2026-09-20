# Multi-Row Bolt-Group Planning Specification

> Stage 2.4C integration note: these accepted Stage 2.4A planners are now invoked by
> framework-independent application preview/design orchestration. Preview uses planning
> status only and executes zero resistance equations. Explicit design constructs the
> complete Stage 2.4B execution bundle and calls the verified engine exactly once. The
> public workflow does not change any planner or equation meaning.

## Purpose and boundary

Stage 2.4A establishes immutable physical-geometry, applicability, demand-scenario,
calculation-plan, block-path, and fingerprint contracts for Calculation Slice 2. It
does not execute a new resistance, capacity, utilization, or ordinary ASCE PASS
calculation. The active calculation engine remains `0.1.0.dev1` and the active rule
set remains `asce74-23-ch8-single-bolt-rc2.dev1`.

The controlling engineering meaning is
`CALCULATION_SLICE_2_ENGINEERING_SPECIFICATION_RC1`, SHA-256
`44431A8921CF1ADF9C7D0F7F022C9615265308A41BE589B1EE5150A7D7886F99`.
ASCE/SEI 74-23 and Erratum 1 are verification sources retained outside the
repository. This document summarizes repository contracts without reproducing
licensed text.

## General physical bolt groups

`GeneralBoltGroup` accepts any positive physical bolt count and does not impose a
three-row ceiling. Every bolt has a stable identity and one exact planar center. Row
and bolt-line identities are resolved from coordinates projected on the signed
force/free-end basis, not from input-array order. Tolerance is an explicit geometric
comparison input; raw coordinates, pitches, gauges, and rectangular-deviation
evidence are preserved.

The resolver reports row and line membership, deterministic order, rectangular or
nonrectangular classification, uniformity evidence, raw adjacent pitches/gauges, and
the source geometry identities. Physical geometry therefore remains useful for
arrangements beyond the current prescriptive calculation scope.

## Demand-distribution plans

Three explicit methods are represented as plans:

- `ASCE_PRESCRIBED` uses exact material-pair-specific row fractions. FRP/FRP uses
  `1/2, 1/2` for two rows and `2/5, 1/5, 2/5` for three rows. FRP/steel uses
  `3/5, 2/5` for two rows and `1/2, 3/10, 1/5` for three rows. The sequence starts
  with Row 1, farthest from the unloaded free end.
- `CONSERVATIVE_FULL_ROW` creates one scenario per physical row and assigns the full
  group demand to that row. It is the conservative envelope for general row counts,
  including arrangements with more than three rows.
- `ENGINEER_DEFINED` records either validated fractions that sum to one or explicit
  row forces, with engineer attribution and basis provenance.

Plans carry input, source, method, scenario, row, and warning evidence. They do not
perform single-bolt allocation within a row and do not execute resistance or
utilization calculations.

## First-row and inter-row calculation plans

First-row plans map physical geometry to raw `e1`, `e3`, `e4`, width, gauge, cap,
thickness, hole, material direction, lap, row-count, and source references. Separate
plans represent the simplified, commentary-based, and rational-analysis branches.
The factors customarily identified as K, A, and B remain planned inputs/derivations;
their numerical resistance use is deferred to Stage 2.4B.

Inter-row plans preserve the two specified shear-out branches and an explicitly
identified rational-analysis branch. Pitch, thickness, hole, material direction,
row-pair identity, demand scenario, applicability, and source provenance are
recorded. No shear-out resistance is calculated in Stage 2.4A.

For transverse loading of a plate, the RC1 source-conflict policy records the
conservative `C_T = 0.50` interpretation together with both concise source locators
and a structured conflict warning. Source conflict is visible and is never silently
resolved.

## Block-shear path and raw-area plans

Candidate paths are constructed only from actual bolt centers and actual bounded
free edges. The resolver supports:

- a U-shaped path with two shear planes and one tension plane;
- a left L-shaped path when a real left free boundary closes the block; and
- a right L-shaped path when a real right free boundary closes the block.

Missing, obstructed, or physically unclosable paths are retained as rejected
candidates with reasons; no convenient path is invented. Corner holes shared by a
shear and tension segment contribute one-half hole to each adjoining plane. Other
intersections use the full plane-specific deduction. U.S. and SI hole additions are
derived from the recorded source basis.

Gross and net path lengths and areas are stored raw. A nonpositive net length is
invalid. A positive net area below 75 percent of gross produces a warning and is not
floored upward. Shear-plane and tension-plane Section 2.10 statuses remain separate.
Block-shear resistance and governing-path selection are deferred.

## Applicability, qualification, and status hierarchy

Applicability, qualification, input validity, source conflict, and numerical
execution are independent statuses. A valid physical arrangement can be outside the
prescriptive ASCE scope. Arrangements with more than three rows retain physical
geometry and conservative full-row/rational plans while carrying an explicit
qualification warning; they do not receive an ordinary ASCE PASS. Unsupported
first-row configurations, including the controlled four-bolt-row branch, fail
closed at the method/applicability layer without invalidating the physical model.

Status precedence prevents an unexecuted numerical placeholder from masking invalid
inputs, source conflict, unsupported applicability, or required qualification. The
planned numerical outcome is always explicitly deferred in Stage 2.4A.

## Determinism and fingerprint scope

The Slice 2 planning fingerprint canonicalizes physical bolts by stable identity and
includes units, exact quantities, row/line resolution, demand method and scenarios,
calculation plans, source snapshots, specification/golden identities, and version
metadata. Input order cannot change the digest. Camera, display, selection,
preview-only extents, timestamps, and other UI state are excluded. Mapping is pure:
no fixture lookup, file/network access, current time, or randomness is permitted.

## Stage 2.3 freeze compatibility

Stage 2.4A adds backend domain/calculation-plan modules, tests, fixtures, and
documentation only. It changes no frozen Stage 2.3 frontend production file, API
route, preview/design behavior, visualization contract, equation, RC2 golden value,
qualification result, or freeze tag. The frozen implementation remains commit
`5bc545ab8251f9bd49dedc776962937ed5e822a2`, tagged
`stage-2.3-interface-geometry-freeze`.

## Stage 2.4A-R1 audit reconciliation

The original Stage 2.4A production table already contained all four approved Decimal
sequences and selected them by explicit `FRP_FRP` or `FRP_STEEL` identity. The
original completion report and an earlier revision of this summary incorrectly
described one generic three-row sequence. Stage 2.4A-R1 corrects that documentation
and directly tests the production selector against the unchanged Slice 2 golden.
There is no production distribution change and no new resistance execution.
