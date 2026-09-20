# FRP Master Connection — Stage 3.2-R10 Tee-Fixed Bolt Layout Frame + Bolt-Group Positioning — Authority Ledger RC1

## 1. New authority

R10 authorizes only:

1. decoupling connected-brace inclination from the `Brace ↔ Tee Stem` bolt-layout frame;
2. keeping Interface A bolt centers and bolt axes fixed in the Tee-stem frame when only brace inclination changes;
3. rotating/repositioning the brace member and selected brace surface about the existing backend brace-placement anchor;
4. adding independent in-plane group-position controls for each Tee interface;
5. adding exact server-authored finite-hole clearances and geometry-placement feedback;
6. separating geometry validity from calculation-method frame compatibility;
7. retaining R9 solid fastener hardware presentation under the corrected geometry.

## 2. Frame authority

### Brace frame

Brace inclination controls the connected member's longitudinal direction and profile placement.

### Interface A layout frame

Interface A grid orientation and bolt axes are fixed to the Tee stem/support template.

The grid does not rotate with brace inclination.

### Interface B layout frame

Interface B remains fixed to the Tee flange/support interface.

No camera/view frame has engineering authority.

## 3. Positioning authority

R10 authorizes two placement modes:

- `EDGE_DISTANCE_CONTROLLED`
- `GROUP_OFFSET_CONTROLLED`

Legacy requests omitted mode and continue as `EDGE_DISTANCE_CONTROLLED`.

In offset mode, only two in-plane offsets are user-controlled:

- vertical;
- horizontal.

No through-thickness user offset is authorized.

## 4. Clearance authority

R10 authorizes exact geometry-containment clearances measured from the complete hole footprint to finite interface boundaries.

These clearances are not automatically code-required edge distances.

R10 specifically controls the existing Angle fixture containment boundary:

- `1.0 in` invalid;
- `1.2814 in` invalid;
- `1.2815 in` exact valid boundary;
- `1.3 in` valid.

No input shall be auto-corrected without explicit user action.

## 5. Calculation applicability

R10 does not authorize a new row-distribution or eccentric-demand equation.

If a fixed-grid force/layout relationship is outside an existing method's proven contract, the design method fails closed with a structured applicability result.

The physical bolt geometry shall not rotate merely to make a calculation method available.

## 6. Inherited authority

R10 inherits unchanged:

- all Stage 2 calculation authorities;
- Stage 3.1 material/fastener authority;
- Stage 3.2 Tee topology;
- Stage 3.2 Tee-body limitation;
- R2 profile architecture;
- R4 exact units;
- R5 deterministic trigonometry/fingerprints;
- R6 preview-state behavior;
- R7 Angle paths;
- R8 Channel/W-I/RHS paths and RHS access qualification;
- R9 independent interface counts;
- R9 solid shank/head/nut/washer presentation.

## 7. Fingerprint authority

### Unchanged

No transition is authorized for:

- zero-inclination legacy geometry;
- R4 controlled U.S./SI execution and preview fingerprints;
- legacy edge-distance placement at zero inclination;
- Interface B under brace-inclination-only edits;
- any Stage 2 controlled fingerprint.

### Narrowly authorized transition

R9 nonzero-inclination Tee preview/design fingerprints may change only because R9 rotated Interface A's grid with the brace while R10 keeps the grid fixed to the Tee stem.

Each such controlled regression fixture must report exact before/after fingerprints and prove:

- same user-entered inclination;
- same Tee/support/Interface B geometry;
- same Interface A layout values;
- changed Interface A physical placement only as required by the corrected fixed-frame authority;
- no demand/resistance equation change.

No other fingerprint transition is authorized.

## 8. Presentation authority

R9 schematic head/nut ratios remain presentation-only:

- head across flats `1.50d`;
- head height `0.625d`;
- nut across flats `1.50d`;
- nut thickness `0.875d`.

R10 adds no hardware dimension authority.

## 9. Explicitly not authorized

R10 does not authorize:

- user movement through thickness;
- automatic bolt relocation to fit an inclined brace;
- automatic member resizing;
- new row distributions;
- new brace-force input semantics;
- new resistance equations;
- friction/slip;
- prying;
- blind fasteners;
- connector-body strength;
- member-body strength;
- dependency or workflow changes.

## 10. Fail-closed rule

A geometry-valid fixed bolt grid may coexist with an unsupported calculation method.

A geometry-invalid inclined brace/layout remains invalid.

The software shall preserve the physical geometry and report the unsupported/invalid condition rather than changing the user's bolt orientation or position.

**END OF AUTHORITY LEDGER RC1**
