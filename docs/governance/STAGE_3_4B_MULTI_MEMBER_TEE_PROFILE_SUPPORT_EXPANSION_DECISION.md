# FRP Master Connection — Stage 3.4B Multi-Member Tee Profile and Support Expansion Decision

## Decision

The next controlled stage is:

**Stage 3.4B — Multi-Member Tee Connected-Profile and Support Expansion**

Stage 3.4B expands the accepted Stage 3.4A Multi-Member Tee Node while preserving its topology, exact joint-wrench assembly, optional-slot behavior, and Tee-body/intergroup limitations.

No new connection family is introduced.

## Connected-profile matrix

Each of the three semantic slots shall offer the same six connected-profile families:

- Flat Plate
- Angle
- Channel
- Wide-Flange / I
- Rectangular Hollow Section
- Solid Rectangular Section

This applies to:

- Upper Brace;
- Middle Member;
- Lower Brace.

The Middle slot is not restricted to conventional W/I beams. Flat Plate and Angle are explicitly included because they are regular project use cases.

## Slot semantics

The slot—not the selected profile family—controls inclination semantics:

- Upper Brace: `0° <= θ_U <= +90°`;
- Middle Member: `θ_M = 0°`;
- Lower Brace: `-90° <= θ_L <= 0°`.

Profile roll and physical connection-surface selection remain independent.

Stable historical slot identity `MIDDLE_BEAM` may be retained in the engineering contract for backward compatibility, while the normal UI may describe it as **Middle Member (horizontal)**.

## Supporting-member matrix

The Multi-Member Tee shall offer exactly the shared seven supporting-member targets:

- W Column Flange
- W Beam Flange
- W Column Web
- Channel Column Web
- Angle Column Leg
- Rectangular Hollow Column Wall
- Solid Rectangular Column Face

No W Beam Web target is introduced.

## Rectangular-section rule

Whenever a connected or supporting profile is Rectangular Hollow Section:

- one continuous physical bolt crosses the near wall, cavity, and far wall;
- both walls are independently validated;
- the cavity is a free shank span, not a material layer;
- no internal nut or washer is permitted.

For Solid Rectangular Section:

- the bolt crosses the complete solid depth;
- no cavity exists;
- hardware remains external.

## Existing Stage 3.4A behavior

The accepted Stage 3.4A default remains unchanged:

- Upper Angle;
- Middle W/I;
- Lower Angle;
- W Column Flange support;
- exact all-three-member actions;
- exact support-wrench assembly;
- exact engineering fingerprints.

Stage 3.4A request contract `3.4A-RC1` remains accepted.

Stage 3.4B introduces an evolved strict contract, recommended `3.4B-RC1`, for the expanded matrix.

## Engineering boundary

Stage 3.4B introduces no new demand, resistance, load-sharing, connector-body, or intergroup equation.

Required limitations remain:

- `TEE_CONNECTOR_BODY_RESISTANCE = NOT_EVALUATED`;
- `MULTI_MEMBER_TEE_INTERGROUP_LOAD_PATH_AND_STABILITY = NOT_EVALUATED`.

Rectangular profiles/supports also retain the accepted limitations:

- `RHS_LOCAL_WALL_RESPONSE = NOT_EVALUATED`;
- `RHS_SLEEVE_OR_CRUSH_TUBE_REQUIREMENT = NOT_EVALUATED`;
- `SOLID_RECTANGULAR_FULL_DEPTH_RESISTANCE_APPLICABILITY = NOT_EVALUATED`.

Known supported numerical failure retains overall `FAIL` precedence.

Ordinary whole-connection `PASS` remains prohibited.

## Future boundary

After Stage 3.4B hosted CI and visual acceptance, the Multi-Member Tee family should be considered for a dedicated freeze.

No Stage 3.4C engineering-method stage is authorized by this decision.

**END OF STAGE 3.4B MULTI-MEMBER TEE PROFILE AND SUPPORT EXPANSION DECISION**
