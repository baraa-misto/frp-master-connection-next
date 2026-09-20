# FRP Master Connection — Stage 3.2-R14B Region-Specific FRP Material-Basis Engineering Correction — Authority Ledger RC1

## New authority

R14B authorizes region-specific material-basis correction for exactly these audited defective region classes:

- W/I WEB
- Tee STEM
- Angle LEG_2
- Channel WEB
- RHS SIDE_WALL_1 / SIDE_WALL_2

The corrected exact bases are controlled by the R14B specification and golden.

## Audited-correct regions

The following audited regions must remain unchanged:

- Tee flange
- W/I flanges
- Angle Leg 1
- Channel flanges
- RHS top/bottom walls
- Flat Plate

If any requires a basis mutation, stop for new authority.

## No material-property authority

R14B changes only coordinate orientation.

It does not authorize any change/equality/substitution of CW, TT, interlaminar, pull-through, bearing, tensile, compressive, shear, or stiffness properties.

## Numerical engineering boundary

Current numerical engineering is expected to remain unchanged because the corrected region LW axes remain unchanged and the audited current numerical consumer uses LW.

If any accepted numerical demand/resistance result or applicability status changes, stop before commit.

## Geometry boundary

No physical geometry is authorized to change.

## Fingerprints

R14B authorizes exact fingerprint transitions only when canonical payload comparison proves the change is caused solely by the controlled material-basis corrections or immediate parent identities derived from them.

Every transition must have exact before/after hashes and automated assertions.

Earlier controlled artifacts remain byte-exact and historical fingerprints remain historical evidence.

## Frontend

The frontend must render backend-authoritative material axes faithfully.

A frontend-only label/vector swap is prohibited.

Region labeling/focus is presentation-only.

**END OF AUTHORITY LEDGER RC1**
