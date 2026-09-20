# FRP Master Connection — Stage 3.2 Tee Connector Authority Ledger RC1

## Purpose

This ledger defines exactly what engineering authority Stage 3.2 inherits and what it does not create.

## New Stage 3.2 authority

Stage 3.2 newly controls only:

1. Tee connector canonical topology and geometry identity.
2. Two-interface assembly identity:
   - brace to Tee stem;
   - Tee flange to supporting-member flange.
3. Column-flange vs beam-flange support-template transformation.
4. Transformation of the existing canonical transmitted force/reference point into each interface local frame.
5. Exact decomposition into interface in-plane and interface-normal components.
6. Orchestration of the already accepted Stage 2.5A in-plane bolt-group engine once per physical interface.
7. Fail-closed aggregation for required but unsupported interface-normal action and Tee-body resistance.
8. Unified application/API/frontend presentation of that controlled assembly.

## Inherited calculation authorities

Stage 3.2 does not alter:

- Stage 2.4A prescribed row distributions.
- Stage 2.4B multi-row numerical resistance engine.
- Stage 2.5A eccentric in-plane per-bolt demand engine.
- Stage 2.5B supported resistance handoff.
- Stage 2.6A eccentric bolt-line shear-out compatibility.
- Stage 2.6B automatic design integration.
- Stage 3.1 connector/fastener material and authority architecture.

## Explicitly not authorized

No Stage 3.2 artifact authorizes:

- general Tee connector body strength;
- FRP Tee bending, rupture, delamination, local buckling, or prying equations;
- metallic Tee strength;
- custom FRP bolt strength;
- automatic interface-normal bolt-axis tension distribution;
- prying;
- moment connection behavior;
- new first-row eccentric net-tension mechanics;
- new block-shear paths;
- concrete anchorage;
- friction/slip design.

## Governing fail-closed rule

If any supported check fails, assembly status is `FAIL`.

Otherwise, if any required check/action remains unsupported or not evaluated, assembly status is `NOT_EVALUATED`.

An ordinary whole-connection `PASS` is prohibited while general Tee-body resistance is unsupported.

## Material identity

The Stage 3.2 production vertical slice uses:

- FRP Tee connector identity;
- 316SS fastener identity;
- explicit existing accepted bolt strength/property data only.

Material names do not create strength values.

## Column vs beam reuse criterion

The same Tee connector topology/geometry code shall be used for column-flange and beam-flange templates.

Equivalent local geometry and local action must produce equivalent local interface demand.

Differences caused only by the global support transform are presentation/template differences, not different bolt-group equations.

**END OF AUTHORITY LEDGER RC1**
