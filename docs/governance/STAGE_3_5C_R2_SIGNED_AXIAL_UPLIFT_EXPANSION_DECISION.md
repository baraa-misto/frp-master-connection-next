# FRP Master Connection — Stage 3.5C-R2 Signed Axial Compression/Uplift Expansion — Decision

## Decision

Stage 3.5C remains open and is expanded before the Stage 3.5 concrete-support family is frozen.

Stage 3.5C-R2 adds a **signed axial-force successor contract** to the FRP W/I column base using single or symmetric double FRP web angles to concrete.

The current product shall allow:

- axial compression;
- axial uplift/tension;
- web-plane shear;
- web-normal shear;
- zero user-applied moment.

The product remains under **Shear Connections** and is not a moment-resisting base connection.

## Signed axial convention

The Stage 3.5C-R2 normal input is:

**Axial force**

in the column-base `L_C` direction.

- `P_L > 0` = uplift/tension along `+L_C`;
- `P_L < 0` = compression along `-L_C`;
- `P_L = 0` = no axial action.

The complete user force in `(S_C,T_C,L_C)` is:

`F = (V_S, V_T, P_L)`.

The current successor default is:

- Axial force = `-20 kip`;
- Web-plane shear = `+4 kip`;
- Web-normal shear = `0 kip`.

User-applied moment remains exactly zero.

## Historical compatibility

Historical engineering contract:

`3.5C-RC1`

remains accepted and reproducible with its nonnegative `Axial compression` magnitude semantics.

Stage 3.5C-R1 was presentation-only and does not alter the historical engineering request contract.

Stage 3.5C-R2 introduces:

`3.5C-R2-RC1`.

The successor uses signed `Axial force`.

Historical payloads are never silently reinterpreted.

## Component-design demand philosophy — unchanged

The owner-controlled philosophy remains:

### Column web local transfer

The column web is checked for **100% of the signed axial action** at the web-to-angle connection.

Demand magnitude:

`|P_L|`.

Signed material direction:

- uplift: `+LW`;
- compression: `-LW`.

The material axis classification remains `LW` in either sign.

### Base-angle system

The base-angle system is independently assigned **100% of the same signed axial action**.

Demand magnitude:

`|P_L|`.

Vertical-leg signed material direction:

- uplift: `+CW`;
- compression: `-CW`.

The material axis classification remains `CW` in either sign.

For a single angle:

`P_angle = P_L`.

For a symmetric double-angle pair after exact symmetry proof:

`P_positive = P_negative = P_L / 2`.

The two branches sum to the signed pair-system action.

These are component adequacy demands and shall not be added to create a doubled foundation reaction.

## Uplift physical load path

For uplift, the controlled physical transfer intent is:

`Column -> Column Web -> Web Bolts -> Base-Angle Vertical Leg(s) -> Angle Body/Heel -> Horizontal Leg(s) -> External Anchors -> Concrete`.

Direct column-end bearing does not resist uplift.

The following remain unsupported/external:

- complete base-angle body/heel uplift transfer;
- horizontal-leg bending/prying;
- anchor tension capacity;
- concrete breakout/pullout/pryout and other uplift anchorage limit states.

## Compression physical boundary

For compression, Stage 3.5C retains the unresolved physical partition between:

- direct column-end bearing;
- base-angle bearing/contact.

Required in compression:

`COLUMN_END_VS_BASE_ANGLE_BEARING_PARTITION = EXTERNAL_DESIGN_REQUIRED`.

The internal component-design envelope still checks the base-angle system for 100% of the compression demand.

## Directional local-check boundary

Reversing compression to uplift reverses the signed direction along the same material axis; it does not change LW versus CW classification.

Existing local bolted FRP checks may execute only where their current signed-force, loaded-edge, bypass-path, and geometry applicability maps the actual action correctly.

If a reverse-load net-section, shear-out, or block-shear path is not authorized by the existing method, return `NOT_EVALUATED` rather than inventing a new failure path.

## Double-angle symmetry

The existing exact symmetry proof remains controlling.

Complete branch half-sharing is authorized only when:

- double-angle geometry is an exact mirror;
- common web group is centered;
- base anchor groups are exact mirrors;
- material/source identities match;
- column is centered;
- `V_T = 0`.

Signed axial force may be compression or uplift.

Then the symmetry-eligible action is split exactly 50/50.

When `V_T != 0`:

`WEB_NORMAL_SHEAR_DOUBLE_ANGLE_BRANCH_ALLOCATION = NOT_EVALUATED`.

## Uplift limitations

When `P_L > 0`, require:

- `BASE_ANGLE_CW_BODY_AND_HEEL_UPLIFT_TRANSFER = NOT_EVALUATED`;
- `BASE_ANGLE_HORIZONTAL_LEG_UPLIFT_PRYING = NOT_EVALUATED`;
- `ANCHOR_TENSION_RESISTANCE = EXTERNAL_DESIGN_REQUIRED`;
- `CONCRETE_UPLIFT_ANCHORAGE_LIMIT_STATES = EXTERNAL_DESIGN_REQUIRED`.

The exact anchor/base wrenches remain exported.

## Foundation equilibrium

The physical foundation action is counted once:

`F_B = F_column`.

No matter whether axial is compression or uplift, the conservative web-design and angle-system-design demands are never added into foundation equilibrium.

## No new calculation method

Stage 3.5C-R2 introduces no new:

- bolt-group demand equation;
- FRP resistance equation;
- base-angle body/heel capacity;
- prying capacity;
- anchor capacity;
- concrete capacity;
- moment-connection method.

**END OF STAGE 3.5C-R2 SIGNED AXIAL UPLIFT EXPANSION DECISION**
