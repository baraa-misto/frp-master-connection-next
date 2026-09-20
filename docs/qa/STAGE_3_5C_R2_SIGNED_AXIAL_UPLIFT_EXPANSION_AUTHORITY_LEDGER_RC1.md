# FRP Master Connection — Stage 3.5C-R2 Signed Axial Compression/Uplift Expansion — Authority Ledger RC1

## Successor authority

Stage 3.5C-R2 authorizes a signed axial-force successor contract for the existing FRP W/I column base with single or symmetric double web angles to concrete.

Accepted user actions in the successor are:

- signed axial force along `L_C`;
- signed web-plane shear along `S_C`;
- signed web-normal shear along `T_C`;
- zero user-applied moment.

Positive axial force is uplift/tension; negative axial force is compression.

## Historical contract boundary

Historical contract:

`3.5C-RC1`

remains exact with nonnegative `Axial compression` magnitude semantics.

Stage 3.5C-R1 is presentation-only.

New successor contract:

`3.5C-R2-RC1`.

No historical payload or fingerprint is silently changed.

## Component design-demand authority

The owner-controlled Stage 3.5C component-demand philosophy remains exact for either axial sign.

### Column web

Signed local axial action:

`P_web = P_L`.

Design magnitude:

`|P_L|`.

Demand fraction:

`1.0`.

Material axis:

`LW`.

Compression is `-LW`; uplift is `+LW`.

### Base-angle system

Signed system axial action:

`P_angle_system = P_L`.

Design magnitude:

`|P_L|`.

Demand fraction:

`1.0`.

Vertical-leg material axis:

`CW`.

Compression is `-CW`; uplift is `+CW`.

### Single angle

`P_angle = P_L`.

### Symmetric double angles

After exact symmetry proof and only when `V_T=0`:

`P_positive = P_negative = P_L/2`.

The pair-system demand remains the full signed axial action.

These component design demands are not summed into foundation equilibrium.

## Signed material-direction authority

Changing axial sign reverses the force direction along the same material axis.

It does not change:

- web axial classification from LW to CW;
- angle vertical-leg axial classification from CW to LW.

Existing direction-aware local bolted checks may execute only when their current signed-force and loaded-edge applicability supports the actual reverse action.

No reverse-load net/shear-out/block-shear method is invented.

## Uplift load-path authority

For `P_L>0`, the controlled physical intent is:

`Column -> Web -> Web Bolts -> Angle Vertical Leg(s) -> Angle Body/Heel -> Horizontal Leg(s) -> Anchors -> Concrete`.

Direct column-end bearing does not resist the uplift component.

Required:

`COLUMN_END_BEARING_FOR_UPLIFT = NOT_REQUIRED`.

## Uplift unsupported/external boundary

When uplift is present, require:

- `BASE_ANGLE_CW_BODY_AND_HEEL_UPLIFT_TRANSFER = NOT_EVALUATED`;
- `BASE_ANGLE_HORIZONTAL_LEG_UPLIFT_PRYING = NOT_EVALUATED`;
- `ANCHOR_TENSION_RESISTANCE = EXTERNAL_DESIGN_REQUIRED`;
- `CONCRETE_UPLIFT_ANCHORAGE_LIMIT_STATES = EXTERNAL_DESIGN_REQUIRED`.

No capacity is fabricated.

## Compression boundary

When `P_L<0`, retain:

- `COLUMN_END_VS_BASE_ANGLE_BEARING_PARTITION = EXTERNAL_DESIGN_REQUIRED`;
- `BASE_ANGLE_TO_CONCRETE_BEARING_RESISTANCE = EXTERNAL_DESIGN_REQUIRED`.

The angle system still receives 100% compression design demand under the owner-controlled component envelope.

## Web-normal shear boundary

No change.

When `V_T != 0`:

- `COMMON_WEB_GROUP_BOLT_AXIS_RESPONSE = NOT_EVALUATED`;
- for double angles, `WEB_NORMAL_SHEAR_DOUBLE_ANGLE_BRANCH_ALLOCATION = NOT_EVALUATED`.

No bolt-axis tension/prying method is introduced.

## Existing calculation authority

No new demand or resistance equation is introduced.

Existing Stage 2.5A / Stage 2.5B / Stage 2.6 methods may be reused only under their accepted applicability for local FRP/bolt checks.

The signed in-plane force direction is preserved into all local layers.

## Foundation equilibrium authority

The physical base reaction uses the signed column action exactly once:

`F_B = F_column`.

Component-design demand duplication does not create a doubled foundation reaction in compression or uplift.

## External handoff authority

The R2 handoff contains:

- signed axial force;
- axial mode `COMPRESSION`, `UPLIFT`, or `ZERO`;
- signed component design actions and magnitudes;
- branch wrenches where symmetry authorizes allocation;
- combined base wrench;
- anchor groups and bearing footprints;
- contact applicability;
- uplift/compression limitations;
- exact fingerprints/method versions.

No concrete or anchor capacity is issued.

## Historical/frozen boundary

Stage 3.5A/R1/R2/B/R1/C-RC1 remain exact.

No Direct, Tee, Clip-Angle, or Multi-Member Tee frozen engineering fingerprint may change.

All freeze tags remain immutable.

## Explicit exclusions

Stage 3.5C-R2 does not authorize:

- user-applied moments;
- moment-resisting base design;
- full angle-body/heel uplift or compression capacity;
- horizontal-leg uplift prying capacity;
- anchor tension capacity;
- concrete uplift capacity;
- stiffness-based compression bearing partition;
- web-normal bolt tension/prying capacity;
- unequal double-angle pair;
- non-W/I column;
- beam web splice.

**END OF AUTHORITY LEDGER RC1**
