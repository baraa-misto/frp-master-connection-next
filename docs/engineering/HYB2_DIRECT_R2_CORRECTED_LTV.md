# HYB2-D1 R2: inactive corrected LTV and hole-area evidence

Owner clarification SHA256:
5818f42056ae28965f5f9704cfde4914332bc5328b2bfe933a647814194ba475.
Preserved predecessor: 8d15d67c0c884f0ac261e80a7e389fe574e40755.

## Separate execution streams

The original Direct workbook is unchanged. HISTORICAL_REPLICATION retains
Input!L64=L51*SIN(N45), L65=L64 and every historical summary. The earlier
CORRECTED_REFERENCE stream also remains available unchanged. The opt-in
Direct-only CORRECTED_SOURCE_CANDIDATE freshly uses L51*COS(N45) for L64/L65.
It changes only the two global V capacities and their dependent global
utilizations, Calcs!D121/D239. Local, P-branch and bolt equations do not change.

At 30.9 degrees, d_span=2 in:

| Quantity | in |
|---|---:|
| Historical SIN LTV | 1.027082504116340 |
| Owner COS LTV | 1.716129811447289 |
| Physical vertical pair spacing | 2.330826009383650 |
| Actual pair perpendicular to V | 1.196975307188628 |

The COS-only brace global utilization is 0.016384394079624 versus historical
0.018108108446212. Receiving-column global utilization is 0.039229559073420
versus 0.040397678801026. These are ASD source reference comparisons, not
adopted Direct resistances. Column V retains the original second Ts factor.

## Physical interpretation

The same bolt centers remain (0,+/-s_v/2); x right, y up;
P axis=(cos(phi),-sin(phi)), V axis=(sin(phi),cos(phi)). The 2-in d_span
witness is the actual pair's projection on V. Its projection endpoints are
recorded explicitly, separately from the vertical physical connector and the
owner COS fracture-length proposal. Both member V branches retain these axes.

R2 confirms Xb as the identifiable brace edge-to-column-centerline distance;
saved Xb=.4375 in. Its historical thickness recipe is not a changed-geometry
rule. Positive local shear paths remain physical edge-to-bolt-centerline
lengths, without automatic half-hole deductions. Reversal is still withheld.

Actual 2D cut rays are explicit geometric witnesses, not a newly established
stress-transfer law. In particular, brace V rays reaching a common free edge
have lengths 1 and 3 in, while the source uses 2 x 1 in. The vertical connector
also differs from the source effective LTV. No bolt, boundary, force axis or
source input is moved to reconcile this.

## Actual holes and conditional source-area sensitivity

The finite-segment/circle intersection routine uses the explicitly supplied
.563-in review hole diameter (not an original workbook operand). It records
entry/exit coordinates, full/half/partial fractions and actual cut gross,
removed and net areas, with interval unions preventing duplicate removal on
one surface. Coincident holes in separate members remain separate surfaces.
Additional allowance is zero: no unapproved ASCE allowance is inserted.

Four comparisons isolate changes: HISTORICAL_GROSS, LTV_ONLY,
HOLES_ONLY_CONDITIONAL and COMBINED_CONDITIONAL. The latter two subtract actual
cut removed areas from the source effective areas. Because the physical and
effective surfaces are unreconciled, they are explicitly conditional numerical
sensitivities, not verified net structural resistances. Actual geometric net
areas are also retained separately. Nonpositive source residual area withholds
only its affected comparison; independent valid checks continue. Listed stress
x area sums before SF4/temperature are not LRFD nominal resistances.

## Single R2 physical adoption decision

For each global V branch, which two physical endpoints define d_span=2 in,
and what is the V direction relative to that segment, so d_span*cos(phi)
is its force-perpendicular fracture length with the unchanged bolt centers?

Until reconciled, physical applicability remains NOT_RECONCILED and no actual
coverage is credited. Reference PASS/FAIL, actual numerical outcomes, analytical
coverage, method notes and qualification remain separate. No blanket YELLOW,
missing-check PASS/N/A, LRFD-to-ASD conversion or public activation is introduced.
Material limits, all required unevaluated mechanisms, C13 and Section 2.3.2
qualification remain visible. No change to native ASCE/F8/F9 or signed authority.

## Verification

Independent floating-point source-operand oracles check every scenario/member/
branch, areas, listed sums, allowable capacities and ratios. Tests cover acute
and near-singular angles, invalid limits, representation precision, hole
intersections/tangency/union/labels, U.S./SI parity, overload, nonpositive residuals,
stream isolation and immutable rendered reports. The original source/historical
fixtures and 53 engineering / 173 historical controls remain authoritative.
The existing inert PDF harness adds two R2 reports per Windows/Ubuntu platform.
No owner service or public route imports the new modules. PR1 stays draft.
