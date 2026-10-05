# Direct Owner Round 2 F3 geometry candidate

This bounded successor to `987922fdb43b5204faf50162414e37d146d8e8e8` implements
the F3 physical-edge contract on `codex/shear01-direct-f1`. Owner review is required.
No main merge, tag, Direct freeze or qualification activation is authorized.

## Explicit owner reconciliation

The owner directed that submitted e1 = 3 in govern the 135-degree starter. Native
loaded boundary x = 8 in and Row 1 x = 5 in are retained. The former physical
Angle extent x = 6 in was inconsistent with that engineering boundary. Direct's
physical Angle extent is now rebuilt from the existing native boundary rule:
2 × unloaded end distance + (rows − 1) × pitch. Its resolved start, axes, section,
datum, bolt anchor and load frames are retained exactly. W physical extents remain
unchanged. View extensions remain presentation objects.

The approved 4 × 4 × 0.5 in Angle, 8 × 8 × 0.5 × 0.5 in W, 2 × 1 layout,
d = 0.5 in, hole = 0.563 in, pitch = 2 in, e1 = 3 in, side inputs = 1/1 in,
selected LEG_1/exterior TOP_FLANGE/single lap and submitted load are preserved.
The physical Row 1 to loaded Angle end distance equals 3 in / 76.2 mm.

## Engineering boundaries and hardware

Direct's additive resolver reads exact canonical section solids and penetration
planes. Physical loaded/unloaded ends, actual free side edges, internal section
junctions and other represented obstructions have separate provenance. Camera,
crop, view extension and computational patch rectangle edges supply no Chapter 8
limits. `geometry/surfaces.py` and existing patch identities are unchanged.

Ordinary e2,min remains 1.5d = 0.75 in for d = 0.5 in. Physical end distance,
free-edge distance, hole footprint, washer seating and unintended penetration of
other exact solids are separate checks. Declared penetrated holes are intended
penetrations, including their shared interface. Deferred heel/fillet shapes and
missing nut/head envelopes are not invented. Full Technical Audit retains the
exhaustive native/computational evidence and these limitations.

Controlled source review: ASCE/SEI 74-23 8.2.4/8.2.5, Figure 8-1, Table 8-1 and
C8.2.2–C8.2.5 / Figures C8-1/C8-2; registered Erratum 1 effective January 13, 2026
does not amend Chapter 8. No perpendicular-wall exception is newly assumed.
The normal report reads these checks from its authenticated calculation snapshot;
it executes no engineering validation or resistance calculation.

## Independent cases

The exact A/B inputs differ only in directed angle. At 45 degrees W Row 1 is
approximately 0.0857864 in from the real loaded physical end, with a 1-in ordinary
two-row end minimum; its physical free-edge distances pass. Hole and washer end
containment also fail. At 135 degrees the physical geometry checks pass; this is
not complete qualified GREEN. Small sweeps around both angles remain continuous.

The deliberate physical free-edge case remains approximately 0.0860473 in and
fails e2. A 105-degree, 2 × 2 patch-only proximity case with a 10-in W flange and
equal 3-in end inputs passes physical checks despite the historical rectangle
warning. A separate subdivision-only witness at exactly 0.086 in preserves all
physical checks. Loaded distance 4 in produces
real W-web washer interference with e2 passing. The oversized 3.6-in washer case
demonstrates angle perpendicular-leg interference and footprint failures while
ordinary e2 passes. These are explicit QA cases, not changes to the owner starter.

## QA and publication requirements

Current collection: 7,897 backend tests and 1,212 frontend tests. Require every
configured statement/branch/function/line coverage threshold at 100%, strict
types/static checks, package/build/dependency gates, actual Windows/Ubuntu PDFs,
rendered page inspection, exact numerical parity for unchanged valid designs,
frozen calculation blob identities, and four exact-SHA hosted CI jobs.

The external F3 review package records actual completion, source identities,
screenshots, rendered pages and exact-SHA CI. Counts here specify gates and do not
substitute for execution. PR #1 remains draft with OWNER REVIEW REQUIRED / DO NOT MERGE.

F593 Fnt, ICE characteristic-property qualification, Tg evidence, Section 2.3.2,
first-row eccentric demand, block shear and other engineering/source limits remain
unchanged. Other connection families retain their existing geometry behavior.
