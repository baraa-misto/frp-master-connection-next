# FRP Master Connection — Stage 3.2-R2 Unified Workspace + Member/Profile Architecture — Authority Ledger RC1

## Purpose

This ledger defines the exact new authority created by Stage 3.2-R2 and the authorities that remain inherited or explicitly absent.

## New Stage 3.2-R2 authority

Stage 3.2-R2 newly controls only:

1. One reusable desktop connection-workspace shell for current/future simple/shear templates.
2. A scalable grouped connection-type dropdown replacing horizontal template buttons.
3. User-facing Tee naming that hides internal `two interfaces` terminology.
4. Persistent canonical-view behavior while engineering controls scroll independently.
5. A reusable structural member/profile identity separating:
   - member role;
   - section/profile family;
   - exact dimensions;
   - material identity;
   - orientation;
   - physical connection surface.
6. Exact geometric definitions and stable surface IDs for:
   - Angle;
   - Channel;
   - Wide-flange/I;
   - Rectangular hollow section;
   - Flat plate.
7. Round-hollow-section identity with direct flat Tee-stem connection prohibited in this stage.
8. Reuse of one W/I cross-section geometry for column-role and beam-role supporting members through different global transforms.
9. Construction of `Brace ↔ Tee Stem` from the selected real connected-member surface instead of a generic plate placeholder.
10. Physical-interface naming and interface-linked viewer emphasis.
11. Engineering stale-state rules for member/profile changes and non-stale rules for display-only changes.
12. Deterministic member/profile/surface identity for the Stage 3.2 Tee workflow.

## Inherited engineering authorities

Stage 3.2-R2 inherits without modification:

- Stage 2.4A prescribed row distributions.
- Stage 2.4B multi-row resistance engine.
- Stage 2.5A eccentric in-plane per-bolt demand engine.
- Stage 2.5B supported resistance handoff.
- Stage 2.6A eccentric bolt-line shear-out compatibility.
- Stage 2.6B automatic design integration.
- Stage 3.1 connector/fastener material architecture and fail-closed authority gating.
- Stage 3.2 Tee topology, two physical interfaces, local action transformation, interface-normal fail-closed handling, and Tee-body `NOT_EVALUATED` limitation.
- Stage 3.2-R1 test-only Windows timing correction.

## Explicitly not authorized

No Stage 3.2-R2 artifact authorizes:

- a manufacturer profile catalog;
- manufacturer section properties;
- profile strength inferred from shape or dimensions;
- angle-leg bending resistance;
- channel flange/web local strength beyond already accepted interface checks;
- tube wall flexure/local yielding/local buckling;
- W/I member local strength beyond already accepted interface checks;
- round-tube direct Tee connection without a separately defined physical adapter/interface;
- general member-body strength design;
- Tee-body strength;
- metallic Tee strength;
- custom FRP bolt strength;
- new bolt-group distribution equations;
- automatic bolt-axis tension distribution;
- prying;
- friction/slip design;
- concrete anchorage;
- moment/semi-rigid connection mechanics.

## Connection naming authority

Normal product UI shall use clear physical connection names.

For the current Tee brace connection:

`Brace connection — Tee connector`

The terms `two interfaces`, `Interface A`, and `Interface B` are internal architecture/debug identities and shall not be required user-facing template terminology.

Normal physical interface labels are:

- `Brace ↔ Tee Stem`
- `Tee Flange ↔ Support`

## Member/profile distinction

A member role is not a shape.

Examples:

- `BRACE + ANGLE`
- `BRACE + CHANNEL`
- `BRACE + RECTANGULAR_HOLLOW_SECTION`
- `COLUMN + WIDE_FLANGE_I`
- `BEAM + WIDE_FLANGE_I`

Material identity is separate from both role and profile family.

## Surface applicability rule

A connection template may consume only a physical surface explicitly exposed by the selected profile and authorized by the template applicability resolver.

No silent generic face is allowed.

No `anything with dimensions` fallback is allowed.

Round hollow sections expose no direct flat Tee-stem contact surface in Stage 3.2-R2.

## Supporting W-shape reuse rule

Column-role and beam-role W supports use the same local W/I cross-section geometry and local surface definitions.

Their difference is the global member/support transform and connection placement.

Equivalent local connection geometry/action shall therefore remain locally invariant when only the support role/global transform changes.

## Governing fail-closed rule

Existing aggregation remains controlling:

- any supported failure => `FAIL`;
- otherwise any required unsupported/not-evaluated path => `NOT_EVALUATED`;
- ordinary whole-connection `PASS` remains prohibited while general Tee-body resistance is unsupported.

Changing the connected profile does not create new resistance authority.

## UI authority boundary

The persistent viewer, dropdown selector, sidebar organization, highlighting, and dynamic title are product-presentation authorities only.

They shall not alter authoritative engineering values unless the user changes an engineering input such as member profile, dimension, surface, orientation, support role, Tee geometry, bolt layout, material/fastener authority, load, or reference point.

## Future-library compatibility

The R2 member/profile architecture is intended for later reuse in:

- brace connections;
- beam shear connections;
- truss/gusset connections;
- member splices;
- bases/anchorage;
- handrail/access-system connections;
- later moment connections.

This intent does not make those future connection families implemented or automatically authorized.

**END OF AUTHORITY LEDGER RC1**
