# FRP Master Connection — Stage 3.4B Multi-Member Tee Profile and Support Expansion — Authority Ledger RC1

## New authority

Stage 3.4B authorizes expansion of the accepted Multi-Member Tee Node to the existing shared connected-profile and supporting-member matrices.

It does not authorize a new connection topology or new engineering equation.

## Connected-profile authority

Every semantic slot may select exactly:

- Flat Plate;
- Angle;
- Channel;
- Wide-Flange / I;
- Rectangular Hollow Section;
- Solid Rectangular Section.

This includes the Middle Member slot.

Middle Flat Plate and Middle Angle are explicitly authorized at horizontal inclination `0°`.

The slot controls inclination semantics, not the profile family.

## Slot orientation authority

- Upper Brace: `0°` through `+90°`;
- Middle Member: exactly `0°`;
- Lower Brace: `-90°` through `0°`.

Profile roll remains separate.

The existing stable `MIDDLE_BEAM` engineering identity may remain for backward compatibility.

## Supporting-member authority

The Multi-Member Tee may select exactly:

- W Column Flange;
- W Beam Flange;
- W Column Web;
- Channel Column Web;
- Angle Column Leg;
- Rectangular Hollow Column Wall;
- Solid Rectangular Column Face.

No W Beam Web target is authorized.

The shared support-target registry/editor is controlling.

## Physical path authority

Open profiles use the existing accepted finite physical-region resolvers.

RHS connected-member path:

`Tee stem -> near RHS wall -> cavity FREE_SHANK_SPAN -> far RHS wall`

RHS support path:

`Tee flange -> near RHS wall -> cavity FREE_SHANK_SPAN -> far RHS wall`

SRS connected/support paths cross the complete solid depth.

One physical bolt per axis and external-only RHS hardware remain mandatory.

## Same-face and group authority

All active connected members remain on the same Tee-stem face.

The four independent physical groups remain:

- Upper member ↔ Tee stem;
- Middle member ↔ Tee stem;
- Lower member ↔ Tee stem;
- Tee flange ↔ Support.

Profile or support changes do not automatically move any group.

## Trim authority

Every active slot may use the accepted full-profile trim architecture for all six profiles.

Trim remains slot-specific and does not move groups.

RHS remains hollow and SRS remains solid.

## Wrench/demand authority

Stage 3.4A exact member-wrench and support-wrench assembly remains controlling:

`F_S = Σ F_i`

`M_S = Σ [M_i + (r_i - r_S) × F_i]`

Stage 3.4B adds no load-sharing, redistribution, demand, or resistance equation.

Per-slot Stage 2.5A calls and one assembled support Stage 2.5A call remain unchanged.

## Limitation authority

Always required:

- `TEE_CONNECTOR_BODY_RESISTANCE = NOT_EVALUATED`;
- `MULTI_MEMBER_TEE_INTERGROUP_LOAD_PATH_AND_STABILITY = NOT_EVALUATED`.

Where rectangular profiles/supports apply:

- `RHS_LOCAL_WALL_RESPONSE = NOT_EVALUATED`;
- `RHS_SLEEVE_OR_CRUSH_TUBE_REQUIREMENT = NOT_EVALUATED`;
- `SOLID_RECTANGULAR_FULL_DEPTH_RESISTANCE_APPLICABILITY = NOT_EVALUATED`.

These are design limitations, not geometry-invalid reasons.

Ordinary whole-connection PASS remains prohibited.

## Backward compatibility

Historical `3.4A-RC1` requests remain accepted with exact geometry, results, and fingerprints.

Expanded requests use `3.4B-RC1`.

The Stage 3.4A all-three default remains Angle / W-I / Angle with W Column Flange.

## Frozen-family boundary

No Direct, frozen Stage 3.2 Tee, or frozen Stage 3.3 Clip-Angle fingerprint may change.

No freeze tag may move.

## Explicit exclusions

Stage 3.4B does not authorize:

- more than three slots;
- opposite Tee-stem faces;
- W Beam Web;
- new profile families beyond the six;
- new support targets beyond the seven;
- common bolts shared between member groups;
- automatic load redistribution;
- Tee-body/intergroup resistance methods;
- moment connection;
- adhesives/epoxy;
- welds.

**END OF AUTHORITY LEDGER RC1**
