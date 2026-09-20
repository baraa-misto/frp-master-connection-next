# FRP Master Connection — Stage 3.2-R13 Tee Length Anchoring + Longitudinal Body Position — Authority Ledger RC1

## New authority

R13 authorizes:

1. Tee connector length anchor modes:
   - CENTER
   - POSITIVE_L_END
   - NEGATIVE_L_END
2. exact selected-anchor longitudinal coordinate relative to a stable Tee datum;
3. one-sided connector-length growth while the selected end remains fixed;
4. exact anchor-mode conversion without physical geometry change;
5. Tee-body translation along the connector longitudinal axis independent from bolt-group positioning.

## Physical separation

R13 treats these as separate:

- Tee body finite boundaries;
- Interface A bolt-group placement;
- Interface B bolt-group placement.

Changing Tee length/anchor/body position does not automatically move the independently positioned bolt groups.

## Terminology

Current vertical Tee UI may use:

- Centered
- Keep upper end fixed
- Keep lower end fixed
- Tee vertical position

Engineering trace retains:

- +L_T
- -L_T
- Tee longitudinal datum

Camera orientation never defines sign.

## Inherited authority

Unchanged:

- Stage 2 calculations;
- Stage 3.1 material/fastener authority;
- Stage 3.2 Tee topology;
- R2 member/profile geometry;
- R4 exact units;
- R5 deterministic geometry/fingerprints;
- R6 preview-state behavior;
- R7/R8 wall/leg paths;
- R9 hardware;
- R10 fixed-grid/offset geometry;
- R11 simplified placement UX;
- R12 end trim/interference geometry.

## Fingerprint rule

Legacy omitted anchor/position preserves current controlled fingerprints exactly.

Different anchor representations of the same exact Tee body geometry should share the same physical body geometry fingerprint.

New body extents/positions create new deterministic geometry identities.

No legacy fingerprint transition is authorized.

## Not authorized

R13 does not authorize:

- automatic bolt movement when connector length changes;
- automatic member movement;
- one-sided flange-width growth;
- new edge-distance equations;
- new resistance methods;
- connector-body strength;
- frontend-only authoritative geometry;
- camera-based top/bottom sign semantics.

**END OF AUTHORITY LEDGER RC1**
