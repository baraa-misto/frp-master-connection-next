# Direct Owner Round 2 F1 candidate

This bounded candidate follows `df541bf2a0f2055f3e93c4c24d82a73f99392417` on
`codex/shear01-direct-f1`. It remains subject to owner review; Direct is not frozen.

## Current product and starter

Brace/beam connection — Direct exposes only Direct angle-to-W connection:
ANGLE LEG_1 to WIDE_FLANGE TOP_FLANGE EXTERIOR, SINGLE_LAP, two actual FRP layers.
The packaged `direct_owner_starter.json` defines the shared U.S./SI physical
starter. Angle is 4 × 4 × 0.5 in; W is 8 × 8 × 0.5 × 0.5 in. Two rows, one bolt
per row; bolt 0.5 in, physical hole 0.563 in under US_CUSTOMARY_PRINTED, washer
OD 1 in and thickness 0.051 in. e1 and loaded boundary 3 in, pitch and retained
gauge 2 in, sides 1 in each, orientation 135 degrees. SI is exactly ×25.4.
Required production temperatures and load classification remain incomplete.
The example axial force is the same physical 0.7 kip / 3.11375513068235 kN
member-local action; it is an explicit example, not a project load derivation.

The geometry helper first searches placements within the selected member sizes.
Any resizing proposal is separately identified and requires explicit acceptance.

## Execution and completeness

Missing basic inputs, invalid/stale geometry and unsupported independent moment
or bolt-axis action block execution. Unresolved environment factors, Tg, F593 Fnt,
ICE qualification, Section 2.3.2 and unsupported check methods permit unaffected
numerical diagnostics and prevent GREEN. Unresolved adjusted resistance is labeled
diagnostic only. Numerical FAIL remains RED. The final integration, including its
authorized rational inter-row shear-out, supplies compact UI/report results.
Exhaustive native records remain in the Full Technical Audit.

## Governed Direct representation correction

An exactly member-local axial load can acquire a Decimal cancellation residue
when binary geometry axes are transformed independently. At the Direct adapter
boundary only, a one-line, equilibrated, force-only member-local action is rebuilt
in the existing exact semantic template axes. Axis agreement and projected zero
components must satisfy the existing DEMAND_FRAME_TOLERANCE (1E-12); direction
quantization remains the existing tolerance squared (1E-24). Entered Y/Z or moments
are excluded even below that bound. Above-boundary representation differences,
non-equilibrated/empty demand scenarios and multiple bolt lines are excluded.

The raw force, projected components, per-bolt vectors, line transverse residue and
fingerprints are retained in an explicit canonicalization trace. The frozen demand
and group-mode engines and their exact-zero contracts remain byte-identical.
U.S./SI normal-action parity and below/at/above boundary tests are required.

## Capability and future shapes

Authenticated `GET /api/v1/workspaces/direct-shapes` publishes the packaged
DIRECT-SHAPE-CAPABILITIES-OR2-F1 contract. Only ANGLE → WIDE_FLANGE is enabled.
WIDE_FLANGE and I_SECTION remain distinct identities. Future multi-shape planar
Direct adapters require reviewed pair/surface, stack, axes, demand, checks, source,
qualification, geometry, UI and PDF tests before exposure. Audit B combinations
are potential adapter candidates only; C/D/E remain unavailable.

## Publication gates

Full backend: 7833 tests, configured 100% statement/branch coverage, Ruff, strict
mypy, dependency consistency and source/wheel builds. Full frontend: 1196 tests,
100% statement/branch/function/line coverage, lint, strict TypeScript, build and
full/runtime audits. Exact-SHA CI runs four Windows/Ubuntu jobs and generates
signed OR2 PDFs on each backend runner. Gates must actually pass; this record
does not claim a result before external evidence is collected. Final SHA, logs,
rendered PDF review, parity and protected-ref evidence are recorded outside the
repository in the owner review package. No main merge, tag or qualification change.
