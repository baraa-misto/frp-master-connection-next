# HYB2-D1-R3: owner-confirmed physical pair

Inactive candidate, based on `ccb74ef9234d0275248f01dfb404ada639d56e2b`.
Order SHA-256: `b081f0e95676043a22e2fbba4a05bbde6aaf8589f40e7875fcd7c5339356f102`.
Owner PNG SHA-256: `bbc9e20cf2eebbac69cb3d2916120ab75429cfe7fde586155f1fa77bff76564c`.
The unchanged PNG is in `figures/HYB2_R3_OWNER_CONFIRMED_GEOMETRY.png`.

## Geometry decision closed

`OWNER_CONFIRMED_GEOMETRY_R3` has its own typed `vertical_bolt_pitch`.
B1=(0,+1), B2=(0,-1) in at the declared midpoint, with optional explicit
rigid frame transformation. Actual pitch is 2 in; no division by cosine.
Both members, all actual holes, paths, projections and rotated comparisons
use this one array. Historical `DirectGeometry.d_span`, R1 and R2 are unchanged.

P=(cos(phi),-sin(phi)); n=(sin(phi),cos(phi)); sketch V=-n.
Changing to the old +n basis changes the signed V component, not the physical
force. At phi=30.9 degrees, transverse LTV=2*cos(phi)=1.716129811447289 in;
longitudinal stagger/perpendicular-to-V projection=2*sin(phi)=1.027082504116340 in.
The foot F on the P-parallel line is constructed, not an additional hole.
The old 2.330826-in pair and its 1.196975-in perpendicular-to-V projection
remain labelled predecessor evidence. The spacing/axis question is CLOSED.

## Placement, boundaries and signs

Xb=.4375 in is the independent horizontal edge-to-column datum, not a thickness
recipe. Local x=-Xb is the brace end. Column face boundaries are x=Xc=1 and
x=Xc-column_flange=-3 in. These datums and the midpoint stay fixed in the
brace-aligned comparison. The brace transverse +n boundary is explicitly
anchored by the inherited near-B1 edge-to-centerline distance=1 in:
n.x=n.B1+1. Its opposite is 4 in away. This is a declared inherited source
anchor, not an owner measurement of every edge and not a fixed-global-edge
comparison with R2. No dimensions are measured from unscaled sketch pixels.

For this reference path construction, release rays oppose the respective
member action. Brace actions are P*p-V*n; the receiving column reaction is
their opposite. Consequently:

| Member / branch | Directed ray | Identified free edge | Centerline lengths, in |
|---|---|---|---|
| Brace P | -p | x=-.4375 | .509868190 / .509868190 |
| Brace V | +n | n.x=n.B1+1 | 1 / 2.716129811 |
| Column P | +p | x=1 | 1.165413005 / 1.165413005 |
| Column V | -n | x=-3 | 5.841789706 / 5.841789706 |

The column V path cannot silently keep the old +1-in edge when the force
direction reverses. Generic ray/edge validation retains negative/zero signed
distances, parallel rays, wrong members and finite-edge misses as unavailable.
Column longitudinal end cuts and the brace distal end are unspecified;
containment is nominal face containment, not complete manufactured fit.

## Same-surface net material and arithmetic scope

Every global block has two separately intersected shear segments and the actual
straight B1-B2 connector. Gross area is actual segment length times actual
member thickness. The existing finite circle/segment kernel unions intersections
on that same surface. Coincident holes in different members are separate surfaces.
The .563-in circular hole is an explicit review input, not an owner sketch
measurement; no additional ASCE hole allowance is inserted.

The 2-in connector loses .563 in across two endpoint half holes: residual length
1.437 in. Brace net connector area=.7185 in2; column=.538875 in2. Projected gross,
removed and residual contributions use the same geometric projection. Neither
the old effective gross area nor a projected width minus an unprojected diameter
is used as the actual net area. Local tear-out keeps centerline lengths without
half-hole subtraction, and retains the source's uniform component/n assumption.

Both gross and net variants freshly execute bearing, shared bolts, every per-bolt
local comparison, local component interactions and global P/V stress-area sums.
The latter are **arithmetic witnesses**, not established resistance: the actual
connector is oblique to the load/material axes. Reusing source Fs/Ft and scalar
P/V interaction does not establish an orthotropic mixed-mode law. No standalone
first-row or independent column side-path resistance is inferred.

Source polyester temperature points, listed properties/SF4, thread basis and
repeated Ts in D31/D221 remain exact. There is no storm relief or LRFD-to-ASD
conversion. Independent paired action cases and currentness remain governed.
The isolated 12 lbf-in couple uses the actual 2-in lever arm (6 lbf per horizontal
couple component); it does not adopt an eccentric FRP demand law.

## Residual decision delta

- CLOSED: what the 2-in spacing means, corrected shared centers, axes and projection foot.
- RECONCILED for declared anchors: nominal directed edges, unequal lengths and actual hole/net geometry.
- Still separate: orthotropic oblique-surface/source-property applicability, general eccentric
  transfer, standalone Angle/W first-row, independent W releases, web/junction/contact and C13.
- Missing fabrication data: column longitudinal end cuts and brace distal end; these affect
  complete physical fit, not the answered bolt spacing.
- Section 2.3.2 qualification and owner acceptance remain pending.

The inactive adapter has no adoption flag and contributes only reference rows.
Native ASCE/F8/F9, public routes, signed snapshots, catalogs and qualifications
are unchanged. No complete connection PASS is claimed. Numerical reference PASS,
FAIL (including red overload), coverage, notes and qualification stay separate.

## Verification and report binding

Acceptance nodes are in `test_hyb2_direct_r3.py` and `test_hyb2_direct_r3_review.py`,
alongside unchanged R1/R2 safeguards. Independent trigonometric/path/area/strength
oracles, unit/frame/permutation witnesses, unsupported-action guards, actual PDF
rendering and input/currentness tests cover the R3 contract. Rendering only prints
immutable backend records. Geometry, action and temperature inputs bind the report;
camera state is not a mechanics input. Exact records retain all old streams and
the dependency ledger. Three additive hosted PDFs preserve the fifteen predecessor
records and same-platform historical report text. Successor count/hash changes
retain exact reconstruction of every prior workflow, including R2.
