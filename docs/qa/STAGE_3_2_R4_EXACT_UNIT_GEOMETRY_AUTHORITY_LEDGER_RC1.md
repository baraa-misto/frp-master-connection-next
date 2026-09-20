# FRP Master Connection — Stage 3.2-R4 Exact Unit Geometry + Valid Tee Benchmark — Authority Ledger RC1

## New correction authority

R4 authorizes only:

1. restoring exact Decimal coordinate arithmetic before geometry validation and engineering fingerprinting;
2. replacing the invalid Tee UI benchmark Angle fixture with the controlled physically valid flat-plate benchmark in the companion R4 golden;
3. updating the one known affected SI execution fingerprint from
   `7c6d7bb9b3d04246c789ad9ed9b291d5b7349a46435594d9bebb181c8488bf57`
   to
   `40ba8cb419f56f5b5c59e2b102c9842850bc925a600088b62185d96cc0314a69`;
4. updating additional SI-only fingerprints only if they are proven to change solely because the same binary-float coordinate-recovery defect is removed, with exact before/after reporting and no physical-geometry change.

## Not authorized

R4 does not authorize:

- tolerance or epsilon geometry;
- new demand/resistance equations;
- Tee-body resistance;
- new member-body checks;
- new profile applicability;
- benchmark-only validation bypass;
- changing U.S./canonical physical geometry to match an erroneous SI result;
- changing any non-SI engineering fingerprint;
- dependency/workflow changes.

## Exactness hierarchy

Authoritative:

`Decimal input -> exact unit conversion -> Decimal geometry arithmetic -> validation -> fingerprint`

Presentation only:

`authoritative geometry -> float rendering`

A render float must never become the source of recovered engineering geometry when exact source coordinates are available.

## Benchmark authority

The R4 U.S. and SI Tee benchmark loaders represent the same physical connection.

The benchmark connected member is a `FLAT_PLATE` brace, preserving the original Stage 3.2 RC1 simple plate-interface intent while R2's Angle/Channel/W-I/RHS profiles remain available for user selection and visual acceptance.

## Fingerprint reproducibility

The deprecated fingerprint remains documented for historical reproducibility but shall not be emitted by the corrected case.

Any additional fingerprint transition outside the narrowly defined SI exact-coordinate class requires STOP.

**END OF AUTHORITY LEDGER RC1**
