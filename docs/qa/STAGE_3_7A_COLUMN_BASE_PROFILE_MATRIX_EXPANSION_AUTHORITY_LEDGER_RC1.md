# FRP Master Connection — Stage 3.7A Column-Base Profile Matrix Expansion — Authority Ledger RC1

## Authority added

Stage 3.7A expands the existing shear-category column-base connection from W/I only to:

- W/I;
- RHS;
- SRS;
- Angle column;

with:

- Single base angle;
- Double base angles.

No new material-strength or resistance equation is introduced.

## Frozen predecessor

Stage 3.5 remains frozen and immutable.

Historical Stage 3.5C W/I behavior remains controlling for historical contracts.

Stage 3.7A is an additive successor.

## Shared rectangular full-through authority

RHS/SRS use the existing shared full-through physical bolt architecture.

RHS:

- near wall material;
- cavity free-shank only;
- far wall material;
- no internal hardware.

SRS:

- continuous solid material;
- no cavity.

Stage 3.7A does not create a new rectangular-section bolt model.

## Angle-column geometry authority

Stage 3.7A reuses the existing Angle profile geometry and selected-leg physical-surface authority.

The actual backend member centroid/reference shall remain controlling.

No connection-layer or frontend centroid approximation is authorized.

If no trustworthy backend Angle centroid/reference exists, implementation stops.

## Angle-column shear topology

Single:

- one base angle on one broad face of one selected column leg.

Double:

- one base angle on each broad face of that same selected column leg.

The two-different-column-leg connector arrangement is not Stage 3.7A and is reserved for a future moment connection.

## Action authority

Stage 3.7A uses:

- signed axial force;
- signed connection-plane shear;
- signed connection-normal shear;
- zero user-applied moment.

Exact generated moments from member-reference/connection-reference eccentricity are retained.

These generated moments do not create user-applied moment authority.

## Component-demand authority

Owner-controlled serial adequacy philosophy remains:

### Column
100% of signed axial action; design magnitude `|P_L|`; material axis LW.

### Base-angle system
100% of the same signed axial action; vertical-leg material axis CW.

These demands are not added to create a doubled foundation reaction.

## Double branch authority

W/I preserves Stage 3.5C.

RHS/SRS opposite-face Double may split complete supported in-plane system action 50/50 only after exact geometry/action symmetry.

Angle-column Double does not obtain complete 50/50 branch-wrench allocation merely from connector geometry because the member centroid is generally offset from the selected-leg plane.

For Angle Double:

- supported common-group in-plane layer provenance may be `0.5 / 1.0 / 0.5` after local symmetry;
- complete anchor/base-angle branch-wrench allocation remains `NOT_EVALUATED` unless actual action symmetry is separately proven.

## External design boundary

Concrete and anchors remain externally designed.

No concrete or anchor capacity equation is added.

Compression bearing partition remains external where applicable.

Uplift direct column-end bearing is not required.

## Connection-normal boundary

Connection-normal shear remains bolt-axis action.

No automatic bolt tension/prying resistance or complete Double branch allocation.

## Material-direction authority

- column axial direction = LW;
- base-angle vertical-leg axial transfer = CW;
- actual selected wall/leg region bases are backend authoritative;
- RHS cavity has no material axes;
- concrete has no FRP material axes.

## Local resistance authority

Reuse existing:

- Stage 2.5A actual per-bolt demand;
- Stage 2.5B local resistance handoff;
- accepted bearing/net/shear-out/block-shear logic;
- existing fastener resistance only where already applicable.

No new local resistance method is authorized.

## Historical/frozen boundary

Stage 3.5 and Stage 3.6 freeze tags remain immutable.

All earlier frozen-family behavior/fingerprints remain exact.

**END OF STAGE 3.7A COLUMN-BASE PROFILE MATRIX EXPANSION AUTHORITY LEDGER RC1**
