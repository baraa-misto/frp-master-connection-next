# Direct F7 physical Angle block adapter

Status: candidate implementation; OWNER REVIEW REQUIRED / DO NOT MERGE.
Baseline: `8b11a6affd0f80c268cfac557e6596c1015d2539`.
Controlling order SHA-256: `8E482EB4580F85AD7A62FF3B26A10EECE9F1F264D321BC5D61CD363FB8565E9D`.
Controlling A4 archive SHA-256: `8835F881B7B0AE54BB1846637D834378832455CFD72AC6C71E18412242279A77`.

## Authority and scope

ASCE/SEI 74-23 Sections 8.3.3.3 and 2.10 supply the resistance equation and
net-area rules. Controlled Slice 2 supplies rational physical L-path and
shared-corner accounting; Slice 3 supplies the authenticated connection
resultant and force-line handoff. A4 authorizes this bounded Direct adapter.
The method is a project rational physical path with normative Eq. 8-14a/b.
It is not labeled purely prescriptive. Whole-connection Section 2.3.2
qualification remains mandatory. RC3 remains inactive for production Direct.

## Physical resolver

Only a multi-row single-line group on one authenticated Angle leg is accepted.
The actual unloaded physical end, farthest applicable row, positive local
free side and selected-leg thickness define the strip. View crops and contact
patches cannot close it. The native L_LEFT ID denotes the positive Angle
local free side for this Direct frame, independently of screen orientation.

Owner LEG_1 polygon: (0,0.25), (5,0.25), (5,2), (0,2) in.
The authenticated raw transverse coordinate is retained, including inverse
frame representation residue. Lv is 5 in from real x=0 to Row 1 x=5;
it is derived from centers, never hard-coded as e1+pitch. The actual free-side
distance is approximately 1.75 in. The submitted computational 1-in side
distance is not physical free-edge authority. Finite W ends are independent.

The native physical bolt/hole inventory is retained. Interior shear holes
receive full deductions; the shared corner receives half on each segment.
No physical hole receives more than one combined deduction. A U.S. printed
hole adds the governed 0.063-in net-width allowance exactly once, even in
an SI presentation of the same source geometry. A genuine SI printed source
uses its separate governed 1.6-mm allowance.

## Arithmetic and provenance

Owner independent witnesses: Ans=2.0305 in², Ant=0.7185 in²,
Ags=2.5 in², Agt=0.875 in², raw ratios 0.8122 and approximately 0.821142857.
Actual raw physical coordinates explain sub-representation differences.
Areas are never clamped to 0.75 gross. Nonpositive raw area is invalid;
a positive raw ratio below 0.75 retains numerical resistance with a code
geometry blocker, prohibiting ordinary compliant PASS.

The tension plane requires longitudinal material and longitudinal physical
force. Ft,L and Fsh,LT remain actual MAT1 properties. A mismatched axis or
physical force returns METHOD / SOURCE NOT SUPPORTED; properties are not rotated.

Signed native ev is derived as -M/Fu from the same authenticated demand
scenario, action/reference point, geometry, frame and resultant. Classification
uses the existing fingerprinted eccentricity representation tolerance. The
owner ev≈+0.25 in and Mres≈-0.175 kip-in select Eq. 8-14b. A valid zero-moment
control selects 8-14a. The frozen handoff runs at its governed 80-digit
Decimal precision so multiplying by unity does not first round its operands
to Python's default context. No frozen engine is edited.

For the eccentric case, Rn=0.5[Ans Fsh,LT + 0.5 Ant Ft,L].
Owner witnesses: Rn=13.51075 kip, Rd=3.6479025 kip at phi=0.45,
Clap=0.60, Cdelta=CM=CT=CCH=lambda=1. Demand is authenticated |Fp|≈0.7 kip.
Factors remain individually traced and are applied exactly once. A numerical
FAIL has RED precedence over missing qualification.

## Bounded heel N/A

The L_RIGHT history ID is NOT APPLICABLE only after authenticated geometry
proves integral selected-leg / heel / perpendicular-leg continuity. The
attempted negative-side polygon remains attached; its junction is not a real
free side. Geometry IDs, represented heel bounds and rejected polygon remain
in the native result. No N/A demand, resistance or utilization is assigned.
Missing continuity proof retains the unresolved history entry.

Heel/junction fracture, LEG_2 participation, delamination, local bending,
through-thickness response, prying and other 3D behavior remain in mandatory
whole-connection qualification scope. N/A is not PASS.

## Integration and reporting

A separate Direct physical block handoff leaves all original frozen layer
scenarios and seven previously evaluated owner check records byte-for-byte
equivalent. The application supersedes only authorized Angle block history
IDs. Counts and governing/status are derived from results. Expected owner
schedule: 8 evaluated, 5 unresolved response methods, 1 unresolved whole
qualification, 1 bounded N/A and 2 neutral material entries: 17 history IDs.
First-row Angle/W, W inter-row and W block methods remain unresolved.

The UI and PDFs consume authenticated final block records. Reporting code
only presents them. The Engineer Report shows actual equation, areas,
properties, separate factors, demand/resistance/utilization and heel reason.
Exhaustive path/raw-coordinate/force-line/continuity evidence stays in the
Full Technical Audit. No new qualification, freeze, tag or other family method
is introduced.
