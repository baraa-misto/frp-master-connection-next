# FRP Master Connection — Stage 3.5C Column Base Using Single/Double Web Angles to Concrete — Authority Ledger RC1

## New product authority

Stage 3.5C authorizes one new Shear Connections product:

`FRP W/I Column -> Single or Symmetric Double FRP Web Base Angles -> Concrete`

The product accepts:

- axial compression;
- web-plane shear;
- web-normal shear;
- zero user-applied moment.

Axial tension/uplift is not authorized in RC1.

## Component-design demand authority

This is owner-controlled.

The physical column action is counted once in foundation equilibrium.

For connection-component design:

### Column web

The local web-to-angle transfer check receives:

`100% of P_u`.

The column web is pultruded vertically, so pure axial compression is in the web **LW** direction.

### Base-angle system

The base-angle system independently receives:

`100% of P_u`.

This is a system-level demand.

For a single angle:

`P_angle = P_u`.

For a symmetric double-angle pair after exact symmetry proof:

`P_positive = P_negative = P_u/2`.

The two angle branches sum to the full system demand.

These duplicate component design demands are not added to the physical foundation reaction.

## Material-direction authority

The base angle is pultruded along its horizontal angle length.

The vertical leg therefore carries column axial compression in its **CW** direction.

For pure axial compression:

- column web directional FRP checks use LW/longitudinal classification where applicable;
- angle vertical-leg directional FRP checks use CW/transverse classification where applicable.

For pure web-plane shear, the relationship reverses:

- column web action is transverse to web LW;
- angle vertical-leg action is parallel to angle LW.

The actual region-specific material bases govern.

## Web-bolt topology authority

### Single angle

`Angle Vertical Leg -> Column Web`

with two FRP layers.

### Double angle

`Positive Angle Vertical Leg -> Column Web -> Negative Angle Vertical Leg`

with one physical common through-bolt group.

For double angles, accepted layer-demand provenance is:

`0.5 / 1.0 / 0.5`

for positive angle / web / negative angle under exact symmetry.

For single angle:

`1.0 / 1.0`.

## Double-angle symmetry authority

Exact half sharing is permitted only for exact mirrored geometry/material/source and an action lying in the web/mirror plane.

In RC1:

`V_T = 0`

is required for complete symmetric branch allocation.

When `V_T != 0`:

`WEB_NORMAL_SHEAR_DOUBLE_ANGLE_BRANCH_ALLOCATION = NOT_EVALUATED`.

No tolerance-based allocation.

## Web-normal action boundary

Web-normal shear acts along the common web-bolt axes.

Required when nonzero:

`COMMON_WEB_GROUP_BOLT_AXIS_RESPONSE = NOT_EVALUATED`.

No bolt tension/prying method is introduced.

## Base-angle body limitation

Existing local bolted checks do not establish a complete crosswise compression load path through:

- vertical angle leg;
- angle heel/corner;
- horizontal angle leg.

Always:

`BASE_ANGLE_CW_BODY_AND_HEEL_COMPRESSION_TRANSFER = NOT_EVALUATED`.

Where applicable:

`BASE_ANGLE_HORIZONTAL_LEG_BENDING_AND_PRYING = NOT_EVALUATED`.

No transverse shape-compression capacity is fabricated from plate properties.

## Concrete / bearing / anchor boundary

No capacity is calculated for:

- angle-to-concrete bearing;
- direct column-end bearing;
- grout;
- anchor steel;
- concrete breakout/pullout/pryout;
- concrete edge/spacing;
- anchor qualification.

Required:

- `BASE_ANGLE_TO_CONCRETE_BEARING_RESISTANCE = EXTERNAL_DESIGN_REQUIRED`;
- `COLUMN_END_VS_BASE_ANGLE_BEARING_PARTITION = EXTERNAL_DESIGN_REQUIRED`;
- `CONCRETE_SUBSTRATE_RESISTANCE = EXTERNAL_DESIGN_REQUIRED`;
- `ANCHOR_SYSTEM_RESISTANCE = EXTERNAL_DESIGN_REQUIRED`;
- `ANCHOR_STEEL_RESISTANCE = EXTERNAL_DESIGN_REQUIRED`;
- `ANCHOR_CONCRETE_LIMIT_STATES = EXTERNAL_DESIGN_REQUIRED`;
- `EXTERNAL_ANCHOR_DEMAND_VERIFICATION = REQUIRED`.

## External handoff authority

The handoff contains the physical column action exactly once.

It also contains component design-demand provenance without summing those conservative component demands into equilibrium.

Where double-angle symmetry is proven, branch anchor-group wrenches may be exported.

Where full branch allocation is unsupported, export the complete base reaction and full physical layout instead.

## Existing calculation authority

No new demand/resistance equation is introduced.

Existing Stage 2.5A / Stage 2.5B / Stage 2.6 methods may be used only under their accepted applicability for local bolted FRP checks.

## Historical/frozen boundary

Stage 3.5A/R1/R2/B/R1 remain exact.

No Direct, Tee, Clip-Angle, or Multi-Member Tee frozen engineering fingerprint may change.

All freeze tags remain immutable.

## Explicit exclusions

Stage 3.5C does not authorize:

- uplift/tension;
- user moments;
- moment base;
- full base-angle CW body/heel capacity;
- anchor/concrete capacity;
- stiffness-based bearing partition;
- flange-mounted base angles;
- non-W/I column;
- unequal double angles;
- welds/adhesives;
- beam web splice.

**END OF AUTHORITY LEDGER RC1**
