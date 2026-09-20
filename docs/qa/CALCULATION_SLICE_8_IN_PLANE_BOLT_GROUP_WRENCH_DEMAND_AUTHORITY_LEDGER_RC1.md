# FRP Master Connection — Calculation Slice 8 — Generalized In-Plane Bolt-Group Wrench Demand — Authority Ledger RC1

## Authority classification

Method:

`RATIONAL_ELASTIC_IN_PLANE_BOLT_GROUP_WRENCH_DEMAND_RC1`.

This is an approved rational mechanics extension, not a new ASCE resistance equation.

It is based on exact rigid-body wrench transport plus the equal-stiffness elastic bolt-group distribution already used for accepted eccentric bolt-group mechanics.

## Why new authority is required

The frozen Stage 2.5A engine transfers:

- direct in-plane force;
- physical force-line eccentricity moment;
- equal-stiffness correction.

It does not transfer a separately applied free group moment.

Moment-connection successors require that additional action.

The free moment shall not be:

- ignored;
- converted into a fabricated eccentric force point;
- replaced by an arbitrary force couple;
- hidden in frontend mechanics.

Slice 8 supplies the missing explicit wrench authority.

## Exact mechanics authority

The controlling equations are independently stated in the companion specification.

The complete wrench is transported to the group centroid.

Direct force uses equal shares.

Centroidal free/eccentric moment uses the elastic tangential correction.

Exact rational equilibrium proves the result.

## Numeric authority

Finite Decimal inputs are converted losslessly to exact rationals.

Exact rational values govern mechanics and equilibrium.

Decimal-80 / `ROUND_HALF_EVEN` values are deterministic interoperability projections for existing Decimal downstream resistance engines.

A Decimal projection residual can never supersede the exact rational equilibrium proof or be redistributed.

## Stage 2.5A boundary

Stage 2.5A remains unchanged.

Where its accepted force/eccentricity-only scope applies, it remains valid.

Slice 8 adds the explicit independent-moment path.

Mandatory compatibility tests ensure no contradiction in the overlap.

## Downstream boundary

Slice 8 is demand-only.

Existing resistance and local-check engines consume the returned actual per-bolt vectors/magnitudes under their own accepted applicability.

No downstream strength method is changed by Slice 8.

## Stage 4.2 boundary

Stage 4.2 is not implemented in this slice.

After Slice 8 acceptance, a separately controlled Stage 4.2 R3 package may replace only the unsupported independent-moment Stage 2.5A calls with Slice 8.

## Frozen boundary

No freeze tag or historical fingerprint changes.

Calculation Slices 5 and 7 remain exact.

**END OF CALCULATION SLICE 8 IN-PLANE BOLT-GROUP WRENCH DEMAND AUTHORITY LEDGER RC1**
