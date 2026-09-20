# FRP Master Connection — Stage 3.2-R8 Profile Wall Bolt-Path Geometry — Authority Ledger RC1

## New authority

R8 authorizes derived finite opposing broad-face geometry for:
- Channel web and flange walls;
- existing W/I wall/flange regression where needed;
- rectangular hollow-section single-wall paths from an exterior wall face to the corresponding inner cavity face.

## RHS constructability qualification

A rectangular hollow-section single-wall path requires access to the inner side for the accepted fastener assembly.

R8 therefore authorizes the trace/qualification identity:

`INTERNAL_FASTENER_ACCESS_REQUIRED`

R8 does not assert that such access exists automatically.

## Inherited authority

Unchanged:
- R7 Angle leg paths;
- Flat Plate path;
- Stage 3.2 Tee topology;
- Stage 2 demand/resistance mechanics;
- Stage 3.1 material authority;
- R6 last-valid-preview behavior.

## Not authorized

R8 does not authorize:
- through-bolting across both RHS walls;
- tube spacers/crush sleeves;
- blind fasteners or inserts;
- new Channel/W/I/RHS resistance equations;
- epsilon/tolerance surface matching;
- internal overlap planes as exposed broad faces;
- changing layout semantics;
- curved/round-section direct Tee contact.

## Fail-closed rule

A path without exactly one finite exposed opposing broad face at the exact intended wall thickness remains invalid.

## Fingerprint rule

No accepted fingerprint transition is authorized.

**END OF AUTHORITY LEDGER RC1**
