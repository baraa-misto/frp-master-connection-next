# FRP Master Connection — Stage 3.5B Direct Side-Lap Angle/Channel to Concrete Wall — Selection Decision

## Decision

The next controlled concrete-support shear-connection stage is:

**Stage 3.5B — Direct Side-Lap FRP Angle/Channel to Concrete Wall**

Normal product label:

**Brace/beam connection — Direct side-lap Angle/Channel to concrete wall**

The connected FRP member runs parallel to the concrete-wall face and continues beyond the wall free end.

The wall stops while the FRP member continues.

The user controls the physical distance over which both the wall and connected member coexist:

**Side-lap length**

Examples include `12 in`, `18 in`, and other valid user-entered lengths.

## Controlled physical topology

Define a right-handed side-lap frame:

- `L_LAP`: connected-member longitudinal axis, positive beyond the concrete wall free end;
- `S_LAP`: transverse direction in the concrete-wall face;
- `N_W`: concrete-wall outward normal toward the connected member.

Require:

`L_LAP × S_LAP = N_W`.

The wall free-end plane is:

`L_LAP = 0`.

The concrete wall occupies negative `L_LAP`.

The connected member occupies:

- the overlap interval behind the free end;
- and continues into positive `L_LAP` beyond the wall.

For side-lap length `L_lap`:

`-L_lap <= L_LAP <= 0`

is the physical member/wall overlap zone.

## Initial connected profiles

Exactly:

- FRP Angle;
- FRP Channel.

No Flat Plate, W/I, RHS, SRS, or other profile in RC1.

## Angle topology

One selected Angle leg lies directly against the concrete wall face.

The other Angle leg remains physically present and projects away from the concrete.

The user may select either accepted Angle leg under the existing shared Angle physical-surface authority.

Any orientation that embeds the perpendicular leg/heel into the concrete is invalid.

Anchors pass through the selected Angle leg directly into concrete.

## Channel topology

Only the **Channel web** may lie against the concrete wall.

Channel flange-to-wall connection is not authorized.

Both Channel flanges remain physically present and project away from the concrete wall.

Anchors pass directly through the Channel web into concrete.

A request selecting a Channel flange as the concrete contact surface is rejected.

## Anchor topology

There is one direct wall-anchor group.

Each anchor passes:

`FRP selected region -> concrete wall`

with:

- exterior nut/washer at the FRP member;
- one shank embedded into the concrete;
- no fictitious far-side concrete hardware.

Anchor and concrete capacity remain designed in specialized anchor software.

## Default overlap and anchor layout

Default side-lap length:

`12 in`.

Default connected-member projection beyond the wall free end:

`16 in`.

Default anchor group:

- rows: `2`;
- anchors per row: `1`;
- pitch: `4 in`;
- group centroid: `6 in` behind the wall free end;
- transverse centroid: `0`.

In the side-lap frame:

- group centroid `L_LAP = -6 in`;
- anchor longitudinal coordinates `-8 in` and `-4 in`.

The user may increase rows and anchors per row where physical geometry permits.

Changing side-lap length shall **not** silently move the anchor group.

An explicit **Center anchor group in overlap** action may set the group centroid to the overlap midpoint.

## Overlap validity

Every anchor must lie in the true physical overlap where both:

- the selected FRP physical region exists;
- and the concrete wall exists.

If the user shortens the lap so that an existing anchor lies outside the member/wall overlap, geometry becomes invalid.

No automatic anchor relocation is permitted.

## Force contract

Stage 3.5B remains under Shear Connections.

No user-applied moments.

Use three signed force components in the side-lap frame:

- **Axial force** along `L_LAP`;
- **Major shear** along `S_LAP`;
- **Minor shear** along `N_W`.

Positive Minor shear pulls away from the wall.

Negative Minor shear acts toward the wall.

The complete user force is:

`F = (P_axial, V_major, V_minor)` in `(L_LAP, S_LAP, N_W)`.

## Action reference

The canonical member-end action reference is backend-derived from the actual connected-profile geometry at the concrete wall free-end plane.

It shall represent the connected member's physical section reference consistently with the shared profile/placement architecture.

No frontend action-reference calculation.

All eccentricity-induced transfer moments to the wall-anchor-group centroid are retained exactly.

## In-plane and normal-action boundary

Axial force and Major shear lie in the selected FRP lap surface and may use existing accepted Stage 2.5A / Stage 2.5B in-plane mechanics where applicability holds.

Minor shear acts normal to the selected FRP lap surface and along the external anchor axes.

Stage 3.5B does not calculate:

- FRP pull-through capacity;
- bolt/anchor axial tension capacity;
- local prying;
- wall-normal contact/anchor partition.

Required when Minor shear is nonzero:

- `DIRECT_SIDE_LAP_BOLT_AXIS_RESPONSE = NOT_EVALUATED`;
- `DIRECT_SIDE_LAP_FRP_PULL_THROUGH = NOT_EVALUATED`;
- `WALL_NORMAL_CONTACT_AND_ANCHOR_FORCE_PARTITION = EXTERNAL_DESIGN_REQUIRED`.

## External design boundary

FRP Master Connection does not calculate:

- concrete resistance;
- anchor steel resistance;
- concrete breakout;
- pullout;
- pryout;
- concrete edge/spacing capacity;
- seismic anchor qualification;
- product-specific anchor capacity.

The full wall-anchor-group wrench, anchor layout, overlap geometry, and geometric edge distances are exported to specialized anchor software.

## Qualification boundary

The direct FRP-to-concrete side-lap connection is not assigned an ordinary whole-connection PASS in RC1.

Required:

`DIRECT_SIDE_LAP_CONNECTION_QUALIFICATION = NOT_EVALUATED`.

Supported FRP local failure still governs overall `FAIL`.

## Historical/frozen boundary

Stage 3.5A / R1 / R2 remain unchanged.

Stage 2.3, Stage 3.2, Stage 3.3, and Stage 3.4 freeze tags remain immutable.

No existing engineering fingerprint transition is authorized.

**END OF STAGE 3.5B DIRECT SIDE-LAP ANGLE/CHANNEL TO CONCRETE WALL SELECTION DECISION**
