# FRP Master Connection — Stage 3.5B Direct Side-Lap Angle/Channel to Concrete Wall — Authority Ledger RC1

## New product authority

Stage 3.5B authorizes one new Shear Connections product:

`Brace/beam connection — Direct side-lap Angle/Channel to concrete wall`

Exactly two connected profile families are authorized:

- Angle;
- Channel.

Channel contact is **web-to-wall only**.

Channel flange-to-wall is explicitly not authorized.

## Side-lap geometry authority

The concrete wall has a real free end.

The connected member runs parallel to the wall and continues beyond the wall free end.

The user controls:

`side_lap_length`.

For wall free end `L_LAP=0`, the member/wall overlap is:

`-side_lap_length <= L_LAP <= 0`.

The anchor group does not automatically move when side-lap length changes.

An explicit Center action may move it to the overlap midpoint.

Anchors outside the physical overlap are invalid even if they remain inside the concrete wall.

## Connected-member placement authority

### Channel

Only the web broad face may contact concrete.

Both flanges remain outside concrete and physically present.

### Angle

One selected Angle leg outer face contacts concrete.

The other leg and heel remain outside concrete.

No embedded free leg/heel is permitted.

## Anchor topology authority

One direct external-anchor group passes through:

`selected FRP region -> concrete embedment`.

No clip angle, Tee, adhesive, weld, or through-wall bolt is present.

External anchor geometry is represented for coordination and handoff only.

No far-side concrete hardware.

## Force authority

The connection uses three signed force components in the side-lap frame:

- Axial force along `L_LAP`;
- Major shear along `S_LAP`;
- Minor shear along `N_W`.

User-applied moment remains zero.

The backend derives the member-end action reference from current profile geometry at the wall free-end plane.

All eccentricity-induced moments at the anchor-group centroid are retained exactly.

## Demand authority

Axial and Major shear are in the selected FRP lap surface and may use accepted Stage 2.5A in-plane group mechanics where current applicability holds.

Minor shear is wall-normal / anchor-axis action.

No new distribution equation is introduced.

## FRP resistance authority

Existing accepted FRP local checks may execute only under their current applicability contracts.

Stage 3.5B does not authorize:

- FRP pull-through resistance;
- anchor axial resistance;
- member-wall prying;
- out-of-plane member response method.

## Required limitations

Always:

`DIRECT_SIDE_LAP_CONNECTION_QUALIFICATION = NOT_EVALUATED`.

When wall-normal/unsupported response applies:

- `DIRECT_SIDE_LAP_BOLT_AXIS_RESPONSE = NOT_EVALUATED`;
- `DIRECT_SIDE_LAP_FRP_PULL_THROUGH = NOT_EVALUATED`;
- `DIRECT_SIDE_LAP_OUT_OF_PLANE_RESPONSE = NOT_EVALUATED`;
- `WALL_NORMAL_CONTACT_AND_ANCHOR_FORCE_PARTITION = EXTERNAL_DESIGN_REQUIRED`.

Concrete/anchor limitations remain:

- `CONCRETE_SUBSTRATE_RESISTANCE = EXTERNAL_DESIGN_REQUIRED`;
- `ANCHOR_SYSTEM_RESISTANCE = EXTERNAL_DESIGN_REQUIRED`;
- `ANCHOR_STEEL_RESISTANCE = EXTERNAL_DESIGN_REQUIRED`;
- `ANCHOR_CONCRETE_LIMIT_STATES = EXTERNAL_DESIGN_REQUIRED`;
- `EXTERNAL_ANCHOR_DEMAND_VERIFICATION = REQUIRED`.

No ordinary whole-connection PASS.

Supported local FRP failure retains FAIL precedence.

## External handoff authority

The handoff contains:

- side-lap frame;
- wall free end;
- wall dimensions;
- side-lap length;
- connected profile/surface;
- backend member-end action reference;
- full translated anchor-group wrench;
- anchor coordinates;
- geometric wall/FRP/overlap edge distances;
- nominal diameter/hole/embedment;
- exact limitations/fingerprints.

No concrete/anchor capacity.

## Historical/frozen boundary

Stage 3.5A, Stage 3.5A-R1, and Stage 3.5A-R2 remain exact.

No Direct, Tee, Clip-Angle, or Multi-Member Tee frozen engineering fingerprint may change.

All existing freeze tags remain immutable.

## Explicit exclusions

Stage 3.5B does not authorize:

- Channel flange-to-wall;
- profiles other than Angle/Channel;
- clip angles or Tee connector;
- adhesive/epoxy;
- welds;
- through-wall bolts;
- concrete/anchor capacity;
- pull-through/prying methods;
- user-applied moments;
- automatic anchor repositioning;
- column base.

**END OF AUTHORITY LEDGER RC1**
