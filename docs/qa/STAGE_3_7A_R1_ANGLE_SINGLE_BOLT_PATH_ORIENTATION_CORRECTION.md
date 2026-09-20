# Stage 3.7A-R1 Angle Single Bolt-Path Orientation Correction

## Control and baseline

The controlling order was read in full before repository action. Its SHA-256 is
`A57E3BECB55FD8A560BA26745D3147DFD5A6448038113BDF85DE40074EC8BAC3`, and its final
sentinel is present. The correction began from clean, synchronized `main` at
`e906ba6faad2e4a85f08cf954c8c95a49a0c6c9f`, commit count 94. GitHub Actions run
#89 is accepted Stage 3.7A evidence: Backend Ubuntu, Backend Windows, Frontend Ubuntu,
and Frontend Windows all passed in approximately 5m49s. The owner-observed negative-face
Single visual defect was open at the start of this correction.

All four Stage 3.7A controlled artifacts retained their prescribed hashes. The six
existing annotated family-freeze tags retained their exact tag objects and peeled
targets. No tag operation is part of this correction.

## Exact reproduction and first-loss boundary

The prescribed 6×6×0.5 in Angle, Leg Y, Single, negative `-T_C` face case was reproduced
with the 5 in connector, 2×1 web-bolt group, 1.5 in pitch, 2 in gauge, 2 in group height,
0.5 in bolt, 0.563 in hole, -20 kip axial force, +4 kip connection-plane shear, and zero
connection-normal shear.

Before correction, the backend returned:

- layer path `POSITIVE_BASE_ANGLE_VERTICAL_LEG -> SELECTED_ANGLE_COLUMN_LEG`;
- stack endpoints `T_C=+0.5 -> -0.5 in` and axis `-T_C`;
- master bolt center `T_C=-0.25 in`;
- Leg Y connection-frame origin `(0,3,0)` and `T_C=(0,0,-1)` in profile coordinates;
- negative connector vertical-leg bounds `T_C=-1.0 -> -0.5 in`.

The endpoint-driven frontend therefore rendered a 1 in shank centered at `T_C=0`, in
the `-T_C` direction. Its schematic head occupied `T_C=+0.8125 -> +0.5 in` and its nut
occupied `T_C=-0.5 -> -0.9375 in`. The shank crossed the selected Angle leg but did not
cross the negative connector vertical leg. Hardware ownership was consequently shown on
the wrong physical ends.

The first loss was backend function `_open_profile_paths`: it hard-coded the positive
connector layer identity, `selected + connector thickness` start, `opposite` end, and
`-T_C` axis for every Angle Single request. Connector-body placement, the selected-leg
surface/frame, action reference, demand, and frontend endpoint consumption were already
correct.

## Narrow correction

The corrected symbols are `negative_angle_single`, `prefix`, `start`, `end`, and
`bolt_axis` in the backend open-profile path constructor. A negative-face Angle Single
now starts at the connector exterior `opposite - connector thickness`, ends at the
selected-leg opposite exterior `selected`, travels in `+T_C`, and identifies the
negative base-angle vertical leg. Positive Single, Double, and W/I logic retain their
existing symbols and values. No frontend production change was required because the
scene already derives shank and schematic hardware from backend endpoints.

## Six-case orientation matrix

| Case | Ordered physical layers | Start/end in `T_C` (in) | Axis | Result |
|---|---|---:|---:|---|
| Leg Y / Positive / Single | Positive connector, selected leg | `+0.5 -> -0.5` | `-T_C` | exact, unchanged |
| Leg Y / Negative / Single | Negative connector, selected leg | `-1.0 -> 0` | `+T_C` | corrected |
| Leg Z / Positive / Single | Positive connector, selected leg | `+0.5 -> -0.5` | `-T_C` | exact, unchanged |
| Leg Z / Negative / Single | Negative connector, selected leg | `-1.0 -> 0` | `+T_C` | corrected |
| Leg Y / Double | Positive connector, selected leg, negative connector | `+0.5 -> -1.0` | `-T_C` | exact, unchanged |
| Leg Z / Double | Positive connector, selected leg, negative connector | `+0.5 -> -1.0` | `-T_C` | exact, unchanged |

For corrected negative Single cases, the endpoint-driven frontend shank is centered at
`T_C=-0.5 in`, has length 1 in, and travels in `+T_C`. The schematic head occupies
`T_C=-1.3125 -> -1.0 in`, while the nut occupies `T_C=0 -> +0.4375 in`. The backend
washer ownership remains `EXTERIOR_NEAR_SIDE` and `EXTERIOR_FAR_SIDE`; there is no
internal or floating hardware. Both physical Angle legs remain in the scene, only the
selected leg is a bolt-path layer, and heel/perpendicular-leg interference continues to
fail closed.

## Fingerprint transition and engineering invariance

Exactly two current Stage 3.7A orientation cases transition. These are physical-geometry
conformance changes under the existing authority, not authority changes:

| Case | Fingerprint | Before | After |
|---|---|---|---|
| Leg Y negative Single | row-1 path | `56121df73a3f4f8de48fb30446b0752bd7b9df33c24bec36e25143b268bd81f8` | `a6ab52edfa37171fa59440201d8b90e18e944236c2286c3c41886291b249affc` |
| Leg Y negative Single | row-2 path | `d3b9227d7586e27ad0571a0259a0e67c52729680ab47da083e8d062c619c8710` | `f7cade8f592a3128d5fe67b42552479df71661deb3ead7938a370606ab9458c0` |
| Leg Y negative Single | handoff | `27fda421bb5a754eeeeae88bd655a0d13c51e0721e5becf1a31f74726046dad9` | `c8d8fcae776497fbc0aaa508e6a8e8d0d7b6582307418b62f66a7f8ce3c3c6c7` |
| Leg Y negative Single | application | `82b202d9d809e6852fb2e5bf2573f569257047d0c46d7accee238e98661d7773` | `a429d97bbd670dc00f9fbadee5f5eef8c3bd84538f07daefb7e7d8dc2bf14365` |
| Leg Y negative Single | engineering | `eeba88c0314c95076eec18678f2996e532681a9c2a63f5d3939d7b5e4c542e8f` | `e3595b4ad56e37c57d1281b99c4154140e423cf4f6a6f8b944a600b0b2dd7999` |
| Leg Z negative Single | row-1 path | `56121df73a3f4f8de48fb30446b0752bd7b9df33c24bec36e25143b268bd81f8` | `a6ab52edfa37171fa59440201d8b90e18e944236c2286c3c41886291b249affc` |
| Leg Z negative Single | row-2 path | `d3b9227d7586e27ad0571a0259a0e67c52729680ab47da083e8d062c619c8710` | `f7cade8f592a3128d5fe67b42552479df71661deb3ead7938a370606ab9458c0` |
| Leg Z negative Single | handoff | `a6d53389cd1ce1fe40e58d3ac97efee89939611722c1499d31ed20c599529761` | `956829aa847ddf038cc9cdb1ab04010b7e4b3291ac0395578096655d8cca9a6d` |
| Leg Z negative Single | application | `5623a1908a02369e3ab78167147d5c627bf89b330a3f7af016933166d210f82b` | `4961953d300431754dbf25f536dd7fd946a0ca33fe32eba6ac5b4f375d55f036` |
| Leg Z negative Single | engineering | `efd4405d6d40a764e752c5403f6a8c3a4c8034877d1c04f82f44041d2e30624b` | `e1c9aab26cdd7108d564c99c78d64d66cd50eabdb3061dc046243b8c73b633e9` |

Positive Single and both Double fingerprints are exact. The exact Leg Y member action
reference remains `(1.315217391304347826086956522,
-1.684782608695652173913043478, 0) in`, and its foundation moment remains
`(33.69565217391304347826086956, 26.30434782608695652173913044,
6.739130434782608695652173912) kip-in`. The exact Leg Z values retain the corresponding
negative `S_C` action reference and negative `T_C` foundation-moment component. Web-group
demand, layer material directions, component transfer, resistance availability, anchors,
and all other action/handoff values remain exact.

Historical Stage 3.5C and all six frozen-family fingerprints remain exact. W/I, RHS,
SRS, Angle Double/uplift, material axes, and G1-G60 remain exact. Demand-equation,
resistance-equation, dependency, workflow, and tag change counts are zero.

## Verification status

- Narrow backend matrix: 54 passed.
- Narrow frontend endpoint/hardware matrix: 5 passed.
- Complete local QA: 2,721 backend tests at configured 100-percent coverage over 21,542
  statements and 5,986 branches; 571 frontend tests across 39 files at configured
  100-percent coverage over 4,178 statements, 3,531 branches, 1,465 functions, and 3,129
  lines. Ruff, strict mypy, ESLint, strict TypeScript, production build, dependency tree,
  JSON, whitespace, runtime/import smoke, and both zero-vulnerability audits passed.
- Fresh depth-one, no-tags, no-alternates object-isolated QA: accepted at
  `0403bc8a4ace0df95b45a84a55832c17b18d6008`.
- Hosted CI for Stage 3.7A-R1: GitHub Actions run #90 passed Backend Ubuntu, Backend
  Windows, Frontend Ubuntu, and Frontend Windows in approximately 5m56s.
- Owner six-case visual acceptance: accepted on 2026-08-31, including centroid/moment,
  Double/uplift, W/I/RHS/SRS, material-axis, and fail-closed interference invariance.

The future different-leg Angle-column moment topology was not begun.
