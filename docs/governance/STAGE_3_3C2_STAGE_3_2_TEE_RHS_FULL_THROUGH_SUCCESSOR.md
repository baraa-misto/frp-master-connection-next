# Stage 3.3C2 Stage 3.2 Tee RHS Full-Through Successor

Status: controlled successor record
Date: 2026-08-26
Scope: affected Tee connected-member RHS request classes only

## Historical frozen behavior

The frozen Stage 3.2 RHS benchmark engineering fingerprint was:

`77fe6b02d379e189ed7b2279360c3610d1bc74d52fe3a91e0d1a81114348f196`

Its physical calculation path crossed one RHS wall and reported
`INTERNAL_FASTENER_ACCESS_REQUIRED`. That identity remains historical provenance; the
Stage 3.2 freeze tag and manifest are not moved or rewritten.

## Stage 3.3C2 successors

The accepted legacy R2 request fixture now resolves to:

`cbb32000a9d4401d42116623a4d6ff43089fed59d3ff3b899ccc15c49c67131a`

The controlled R8 profile-wall fixture now resolves to:

`9269fc2ec373686d2a946970e0c1633a2c6188f8d0c4ca650e30088771a7c0d5`

The canonical delta is limited to the required physical successor: each displayed
bolt owns one continuous path through `TEE_STEM`, `RHS_NEAR_WALL`, `RHS_CAVITY`, and
`RHS_FAR_WALL`; the cavity is `FREE_SHANK_SPAN`; the near/far walls are material; both
exterior hole disks are independently contained; and head/washer plus nut/washer are
external with zero internal hardware.

`INTERNAL_FASTENER_ACCESS_REQUIRED` is removed because the successor no longer
requires internal hardware. Required but unauthorized local mechanics are recorded as
`RHS_LOCAL_WALL_RESPONSE` and `RHS_SLEEVE_OR_CRUSH_TUBE_REQUIREMENT`. They prevent
ordinary PASS and set design readiness false without making valid geometry invalid.

## Invariance boundary

Exact non-RHS frozen Tee engineering fingerprints remain:

- Flat Plate: `e93e83c5e231d533be29f36f19086c09b0e5b89a3b0388ef3f3ab5e842b8174b`
- Angle: `70e2a2f8f02dddbee5648295da21097edce9a41842a6d6419578d8e30a39f2f6`
- Channel: `ca4489f859f4bba24acce0dc880e6cf102156681d1b0e996baa6a8669df81106`
- W/I: `0863a69cdae2143a694b3c06c774938e0ece232e2d8a984ba113df8284ced971`

No equation, numerical resistance result, material property, demand method, freeze
tag, dependency, or workflow changes under this successor.
