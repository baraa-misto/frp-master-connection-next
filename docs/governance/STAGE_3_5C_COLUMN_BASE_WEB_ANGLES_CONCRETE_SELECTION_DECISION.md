# FRP Master Connection — Stage 3.5C Column Base Using Single/Double Web Angles to Concrete — Selection Decision

## Decision

The next controlled concrete-support shear-connection stage is:

**Stage 3.5C — FRP W/I Column Base Using Single or Symmetric Double FRP Web Angles to Concrete**

Normal product label:

**Column connection — Single/double web base angles to concrete**

This remains under **Shear Connections**.

Stage 3.5C permits:

- one vertical FRP W/I column;
- one single FRP base angle on one column-web face, or one symmetric mirrored pair of FRP base angles on both column-web faces;
- one column-web-to-angle bolt group;
- one external concrete-anchor group per base angle;
- axial compression plus two horizontal shear components;
- zero user-applied moment.

Concrete, anchor-system capacity, and concrete bearing capacity remain externally designed.

## Serial component-design demand philosophy

The owner-directed Stage 3.5C philosophy is:

1. **Column web local transfer check:** the column web is checked for **100% of the column axial compression demand** at the web-to-angle connection.
2. **Base-angle system check:** the base-angle system is independently assigned **100% of the same axial compression demand**.
3. These are component design demands in series / conservative envelope checks. They do **not** represent two physical foundation reactions and shall not be added together in equilibrium.
4. The combined concrete-base handoff contains the physical column action **once**.

For a single base angle:

`P_angle = P_u`.

For a symmetric double-angle pair:

`P_pair = P_u`

and, after exact pair symmetry is proven:

`P_positive = P_negative = P_u / 2`.

The double-angle connection system still transfers 100% of `P_u`; the two branches share that system demand.

## Material-direction requirement

This is a controlling owner requirement.

### Column web

The column is pultruded along its vertical member axis.

For axial compression:

`P_u` is parallel to the column-web `LW` material direction.

The column-web local connection layer is therefore checked using the accepted **longitudinal** FRP directional properties where the existing method is applicable.

### Base-angle vertical leg

Each base angle is pultruded along its horizontal angle length.

The vertical leg carries the axial transfer down toward the concrete base in the angle **CW** material direction.

For pure axial compression:

- column web bearing/load direction relative to material = `LW`;
- base-angle vertical-leg bearing/load direction relative to material = `CW`.

Existing directional bolt-hole checks shall use those actual region bases.

No property substitution based only on component name is permitted.

## Base-angle body boundary

The existing bolted-connection methods may evaluate supported local web/vertical-leg bolt-hole limit states.

Stage 3.5C does **not** invent a complete capacity for:

- crosswise compression transfer through the FRP angle body;
- heel/corner force transfer;
- vertical-to-horizontal-leg load spreading;
- horizontal-leg flexure/prying;
- concrete bearing.

Required:

`BASE_ANGLE_CW_BODY_AND_HEEL_COMPRESSION_TRANSFER = NOT_EVALUATED`.

Concrete bearing is external.

## Column-end contact / duplicate component demand

No artificial column-bottom clearance is introduced.

If the column end and base angles are both physically in contact with the base, Stage 3.5C does not calculate stiffness-based compression sharing between:

- direct column-end bearing;
- base-angle bearing.

The internal component-design envelope still checks:

- column web at 100% `P_u`;
- base-angle system at 100% `P_u`.

The physical partition is:

`COLUMN_END_VS_BASE_ANGLE_BEARING_PARTITION = EXTERNAL_DESIGN_REQUIRED`.

The foundation reaction is never doubled.

## Base frame

Define a right-handed column-base frame:

- `S_C`: horizontal direction in the column-web plane;
- `T_C`: horizontal direction normal to the column web;
- `L_C`: column longitudinal direction, positive upward.

Require:

`S_C × T_C = L_C`.

The concrete top surface is:

`L_C = 0`.

The column extends into positive `L_C`.

## Force contract

No user-applied moments.

Inputs:

- **Axial compression** `P_u >= 0`, acting in `-L_C`;
- **Web-plane shear** `V_S`, signed along `S_C`;
- **Web-normal shear** `V_T`, signed along `T_C`.

Engineering force vector in `(S_C,T_C,L_C)`:

`F = (V_S, V_T, -P_u)`.

Axial tension/uplift is not accepted in RC1.

## Double-angle symmetry

For the symmetric double-angle option, exact branch half-sharing is authorized only when:

- both base angles are exact mirrors;
- web-bolt geometry is mirrored/locked;
- base-anchor groups are mirrored/locked;
- material/source identity is symmetric;
- the column is centered;
- `V_T = 0`.

Then the pair-system action in the mirror plane may be split exactly 50/50.

When `V_T != 0`, the existing symmetry proof does not authorize complete branch allocation.

Required:

`WEB_NORMAL_SHEAR_DOUBLE_ANGLE_BRANCH_ALLOCATION = NOT_EVALUATED`.

The complete base reaction and full anchor layout remain available for external design.

## Common web-bolt group

Single-angle option:

`Angle Vertical Leg -> Column Web`

Double-angle option:

`Positive Angle Vertical Leg -> Column Web -> Negative Angle Vertical Leg`

For the symmetric pair, reuse the accepted common-group layer provenance:

- positive angle layer = branch share;
- column web layer = full system share;
- negative angle layer = branch share.

For pure compression in a double pair:

- column web layer total demand = `P_u`;
- each angle vertical-leg layer total demand = `P_u/2`.

## Concrete / anchor boundary

FRP Master Connection shall not calculate:

- concrete bearing capacity;
- anchor steel capacity;
- concrete breakout;
- pullout;
- pryout;
- side-face blowout;
- concrete edge/spacing strength;
- seismic anchor qualification;
- grout/base support capacity.

The external handoff shall retain:

- combined base reaction wrench;
- angle-system/branch wrenches where authorized;
- anchor coordinates;
- angle bearing footprints;
- column/base contact footprint;
- geometric edge distances;
- exact limitations.

## Planned family sequence

Stage 3.5C does not begin the beam web-splice family.

After Stage 3.5C acceptance, the concrete-support shear family may be considered for freeze before beginning the web-splice family.

**END OF STAGE 3.5C COLUMN BASE WEB-ANGLE TO CONCRETE SELECTION DECISION**
