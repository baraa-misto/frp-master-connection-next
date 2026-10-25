# HYB2-D3-P3 — same physical Direct connection

Predecessor: `2367eaebd98a228658313d8fae6c9d73e3fdc4a7` (accepted P2).
This candidate executes scoped ASCE components with the existing RHM reference
comparisons. It installs no new structural-method approval or qualification.

## Actual geometry and independent actions

The same `R3Geometry` supplies B1=(0,1), B2=(0,-1) in to both methods and the
accepted viewer. Actual vertical pitch is 2 in, never a projected d_span. The
L4x4x.5 / I8x4x.375 source detail, phi=30.9 degrees, Xb=.4375 and Xc=1 retain
their confirmed 1.716129811447289-in transverse and 1.027082504116340-in
longitudinal projections. No Clip Tee or reinforcement is added. No bolt/end
is moved to satisfy a check. I depth/web display context does not become a
resistance operand or a fabricated member end.

Independent supplied LRFD and ASD combinations retain all six components and
their source frames/references. No LRFD-to-ASD conversion exists. Source P and
sketch V=-n form a left-handed 2D pair relative to source x/y: Fx=P cos(phi)-V
sin(phi), Fy=-P sin(phi)-V cos(phi), and source Mz is minus entered local Mz.
Reference positions are transformed with the same signs. The frozen engine
receives the same physical reference for P/sketch-V and the existing
zero-free-moment P/+n alias: the new LRFD seam also reverses the second reference
coordinate when that alias reverses V. Original declared inputs remain in the
signed record. Legacy requests outside this seam are unchanged; a nonzero
free-moment P/+n case remains explicitly unsupported rather than inferred.
The unchanged Slice 8
exact rational wrench engine transports the entered in-plane free moment and
distributes forces at these actual centers. Its four exact equilibrium proofs,
raw action vector, projected values and fingerprint are retained. Equal in-plane
bolt stiffness and engaged contacts are declared model assumptions; equilibrium
does not establish contact, prying or first-row FRP stress capacity. Nonzero or
unknown out-of-plane actions/reference, or an unsupported frame, withhold the
affected LRFD calculation; the independent RHM set remains available.

## Applicable existing ASCE primitives

Primary authority is the supplied ASCE/SEI 74-23 owner copy, printed pp.31-36:
Figure 8-1; 8.2.2-8.2.5/Table 8-1; 8.3.1; 8.3.2.1, .3 and 8.3.3. The retained
Erratum 1 (effective 2026-01-13) changes Chapter 5, not these equations. Publisher
reference: https://ascelibrary.com/doi/book/10.1061/9780784415771 . Licensed pages
are not copied into the candidate or public review package.

* Two bolt shear comparisons reuse Eq.8-2, phi=.75, lambda=1 and the existing
  selected F593/session source resolver. An absent Fnt or unknown shear-thread
  state withholds those two checks; RHM's ASD allowance is never made an LRFD Fnv.
* Four pin-bearing comparisons reuse Eqs.8-5/8-6 on each actual bolt vector and
  each member's LW axis. Angle LW is the R3 P axis; receiving flange LW is source
  vertical, consistent with the accepted material-axis scene. The frozen 5-degree
  direction rule selects the existing longitudinal/transverse characteristic
  property; no new angular interpolation or strength is invented.
* Figure 8-1 defines rows normal to the connection-force direction. For this
  two-center staggered pair, row pitch is the absolute center separation projected
  along the connection resultant; transverse stagger is retained. The existing
  `constant_pitch_factor` applies C_delta=min(1,s/(4d)). Exact zero projection is a
  single two-bolt row (C_delta=1). A zero group resultant has no declared row
  direction and withholds bearing, including a pure-couple case; bolt shear can
  still execute. No new tolerance snaps a real component or changes a frozen gate.
* Single-lap=.6, included/unknown bearing-thread factor=.6, bearing phi=.6 and
  the explicitly selected MAT1 time category are retained. All LRFD cases use that
  declared load classification; names do not infer another classification. The
  coefficient is a component calculation within the existing specification basis,
  not a claim that the furnished product or full detail has been qualified.
* The existing MC1/MAT1 material resolver, catalog and property ledger adjust
  strengths once. A material record/owner override can describe only member-a or
  member-b; one shared MC1 conditions set is required. Shape-family binding is to
  the actual Angle/I element, not to a borrowed native request or result. Missing
  bearing properties/factors and out-of-domain hole/thickness data withhold the
  affected bearing checks while independent bolts/RHM comparisons proceed.

No inter-row, first-row or block capacity is borrowed from the unrelated native
BRACE layout. Native F8/F9 authority, original signed requests and its eight
reference comparisons remain unchanged. Source BRACE rotation retains its own
geometry-only domain; it receives no SUPPORT calculation or inherited heel N/A.

## Existing RHM comparisons and physical mechanisms

The seven unchanged R3 comparisons retain local unequal paths, shared real edges,
actual hole intersections and same-surface net areas. Source polyester 100 F,
listed properties/SF4, repeated Ts in D31/D221 and included-thread 12.75-ksi
allowance remain reference-specific; they are not blended with selected ASCE
properties, factors or hardware. Different project conditions do not turn the
saved reference into a project-qualified ASD calculation. No extraction or
source equation is rewritten.

| Physical mechanism | Executed evidence | Remaining exact requirement |
|---|---|---|
| Shared in-plane bolt shear | Fresh ASCE per-bolt Eq.8-2 and RHM shared-bolt interaction | Actual 3D/bolt-axis transfer and physical hardware conformance |
| Both members' hole bearing | Fresh ASCE vector-specific Eq.8-5/8-6; separate RHM bearing | Applicable product characteristic/source evidence, contact and installation |
| Angle local end/side tear-out | RHM D59:D87, unequal real-edge paths | Validated directional/bearing-bypass applicability of this local envelope |
| Receiving local tear-out | RHM D183:D205 | Inter-hole release proof; long path crosses an integral web and is not automatically flange-only fracture |
| Angle coupled block release | RHM D93:D121; R3 actual net surfaces | Oblique orthotropic law and proof that its combined envelope bounds first-row failure, or an independent valid law |
| Receiving coupled block release | RHM D211:D239; R3 net surfaces | Actual detachable occupied-outstand and web-attached 3D volumes, true ends and remote N/V/M |
| First-row net failure | Not established by another passing row | Actual effective cut/width and bearing/bypass stress law; one substantiated combined proof can cover multiple mechanisms without duplicating resistance |
| Heel and flange/web transfer | Integral geometry retained | Actual roots/fillets and validated 3D transfer or a geometry-specific physical absence proof |
| Bolt-axis force, pull-through/prying | No absence inferred from zero entered actions | Contact/standoff, stiffness and actual six-action transfer; no fake zero prying/N/A |

These are physical requirements rather than an artificial count of ASCE check
names. No unavailable mechanism is assigned PASS or N/A. No generic flange-only
law is installed where the web/junction prevents the proposed release.

## Detailing, coverage and reports

The existing footprint screen retains declared versus unknown faces and actual
washer overhang. A confirmed short washer OD remains a separate ASCE8.2.4
requirement failure. The actual R3 oblique end is intersected opposite each
current LRFD resultant. A distance below even Table8-1's least 2d end-distance
requirement is an explicit failure; meeting this lower-bound screen is not full
detailing approval. The nominal target's declared .4375-in horizontal datum gives
about .559 in along the .15/.02-kip review resultant, below 1 in. The geometry is
preserved, and independent component arithmetic stays available. A 1-in washer
on a confirmed .4375-in free edge overhangs .0625 in and remains NOT_FIT.

Numerical PASS/FAIL, physical fit/detailing, analytical completeness, method notes,
action-envelope completeness and Section2.3.2 remain separate. The backend seals
the new full material/action/demand/equation traces with the same current input
record; no client results, approvals or second physical model are accepted. The
largest scoped utilization is selected in the backend from exact ratios, never
by adding utilizations or mixing resistances across bases. Edits, late responses,
account mismatch, expiry and post-render currentness remain guarded.

Normal reports show actual cases, factors, dimensions, calculated rows, warnings,
scoped maxima and physical requirements. Full exact operands, original records
and machine/native detail remain in the Technical Audit and current JSON. Report
rendering does not calculate another design. Successful installed field use is
attributed to the owner and is not described as laboratory evidence.

The accepted P2 common inputs, preset confirmation/undo, one viewer, accessible
alignment selector and five region-specific LW/CW/TT axes are retained. Existing
MAT1 controls now also supply the source geometry's LRFD property context; they
do not create another material system or change source ASD values.

Stable configured full QA, all four exact-SHA platform jobs, current browser
interactions and actual numerically/visually inspected PDFs are required before
delivery. This document records scope and derivation, not future QA success.
PR1 remains draft/unmerged; no qualification, merge, tag, freeze or deployment.
