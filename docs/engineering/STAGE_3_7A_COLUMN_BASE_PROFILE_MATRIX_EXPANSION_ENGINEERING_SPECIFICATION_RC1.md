# FRP Master Connection — Stage 3.7A Column-Base Profile Matrix Expansion — Engineering Specification RC1

## 1. Status

**Controlled owner engineering specification — RC1**

Stage 3.7A is an additive successor to the frozen Stage 3.5 column-base shear connection.

It expands the current column profile matrix while preserving the accepted W/I behavior.

## 2. Accepted starting baseline

Expected repository state:

- branch: `main`;
- `HEAD == origin/main == remote main`:
  `031e8367b25765652447fb358e54dd5facd1238b`;
- subject:
  `chore: freeze Stage 3.6 W/I web-splice family baseline`;
- commit count:
  `93`;
- clean worktree/index.

Stage 3.6 freeze hosted CI:

- GitHub Actions run #88;
- Backend Ubuntu PASS;
- Backend Windows PASS;
- Frontend Ubuntu PASS;
- Frontend Windows PASS;
- duration approximately `5m 38s`.

Expected frozen tags include Stage 3.6:

`stage-3.6-wi-web-splice-family-freeze`

tag object:

`748d684ae08d86d6335fc26c9bff1e6c0389aa25`

peeled target:

`031e8367b25765652447fb358e54dd5facd1238b`.

All earlier freeze tags remain immutable.

## 3. Frozen Stage 3.5 successor policy

Stage 3.5 frozen product behavior remains historical authority.

Stage 3.7A is a separately versioned successor.

Do not move:

`stage-3.5-concrete-support-shear-family-freeze`.

Historical Stage 3.5C / R1 / R2 request/result/fingerprint behavior must remain exact.

## 4. Product identity

Existing historical product:

`Column connection — Single/double web base angles to concrete`

remains reproducible under historical contracts.

Current successor presentation may use the more general label:

`Column connection — Single/double base angles to concrete`.

Selector remains under:

`Shear Connections`.

## 5. Successor contract

Add:

`3.7A-RC1`.

Historical Stage 3.5C contracts remain accepted unchanged.

Unknown future versions fail closed.

## 6. Supported column profile matrix

Current normal successor supports exactly:

- `WIDE_FLANGE_I`;
- `RECTANGULAR_HOLLOW_SECTION`;
- `SOLID_RECTANGULAR_SECTION`;
- `ANGLE`.

No Channel-column base is added in Stage 3.7A.

No other profile family is accepted.

## 7. Assembly matrix

For every supported profile, allow exactly:

- `SINGLE_BASE_ANGLE`;
- `DOUBLE_BASE_ANGLES`.

Meaning is profile-specific as defined below.

## 8. Column-base frame

Use backend-authoritative right-handed frame:

- `L_C` = column longitudinal, positive upward;
- `T_C` = selected connection surface/selected Angle-leg plane normal;
- `S_C` = in-plane horizontal direction satisfying:
  `S_C × T_C = L_C`.

Do not derive engineering frame in frontend.

## 9. Loads

Current successor inputs:

- signed axial force `P_L`;
- signed connection-plane shear `V_S`;
- signed connection-normal shear `V_T`;
- zero user-applied moment.

Sign convention:

- `P_L > 0` uplift/tension;
- `P_L < 0` compression;
- `V_S` signed in selected connection plane;
- `V_T` signed normal to selected connection plane.

## 10. Member action reference

Use the backend-authored physical column member-end reference.

### W/I, RHS, SRS
Reference lies on the centroidal longitudinal axis.

### Angle
Reference shall be the actual backend Angle-section centroid/member axis.

Stage 3.7A must retain any offset from the selected leg plane.

If the existing backend cannot provide the Angle centroid/reference, STOP before mutation.

## 11. Exact action translation

For every profile/assembly:

- retain the canonical member-end force;
- translate the complete wrench exactly to connector/bolt/anchor/foundation references;
- preserve all generated moments from geometry;
- no tolerance zeroing;
- no frontend wrench calculation.

Generated moments do not make this a user-moment connection.

## 12. W/I historical regression

W/I Single and Double must remain byte-/fingerprint-exact to accepted Stage 3.5C-R2 behavior under historical contracts.

Under the successor contract, physical behavior must be equivalent except for additive profile-generalized metadata/labels.

## 13. RHS default geometry

Controlled test default:

- outside dimension in local `S_C`: `10 in`;
- outside dimension through selected/opposite faces in local `T_C`: `8 in`;
- wall thickness: `0.5 in`;
- display height: `24 in`.

Default hollow cavity across selected face pair:

`7 in`.

## 14. SRS default geometry

Controlled test default:

- outside dimension `S_C`: `10 in`;
- through-depth `T_C`: `8 in`;
- display height: `24 in`.

No wall-thickness field is used.

## 15. Angle-column default geometry

Controlled test default:

- Leg Y width: `6 in`;
- Leg Z width: `6 in`;
- thickness: `0.5 in`;
- display height: `24 in`.

Use the existing sharp-corner/simplified Angle geometry authority exactly.

Do not invent a new Angle profile model.

## 16. Rectangular face selection

For RHS/SRS, expose all existing finite broad exterior faces supported by the shared rectangular profile.

Single assembly:

- user selects one physical face.

Double:

- user selects one face;
- backend derives its exact opposite face;
- pair identity is selected/opposite.

Do not let frontend create opposite-face transforms.

## 17. RHS Single bolt path

For each physical column/base-angle bolt:

`BASE_ANGLE_VERTICAL_LEG -> RHS_NEAR_WALL -> FREE_SHANK_CAVITY -> RHS_FAR_WALL`.

Default segment lengths for the test fixture:

- base-angle vertical leg: existing connector thickness;
- near wall: `0.5 in`;
- cavity: `7.0 in`;
- far wall: `0.5 in`.

Head/washer exterior to base angle.

Nut/washer exterior to far RHS wall.

Internal hardware count:

`0`.

## 18. RHS Double bolt path

For each physical common bolt:

`POSITIVE_BASE_ANGLE_VERTICAL_LEG -> RHS_NEAR_WALL -> FREE_SHANK_CAVITY -> RHS_FAR_WALL -> NEGATIVE_BASE_ANGLE_VERTICAL_LEG`.

No duplicate shank.

No internal hardware.

The cavity has no material identity, no bearing layer, and no material axes.

## 19. SRS Single bolt path

For each bolt:

`BASE_ANGLE_VERTICAL_LEG -> SOLID_RECTANGULAR_COLUMN`.

One continuous solid material segment through full selected/opposite-face depth.

Head/washer exterior to connector.

Nut/washer exterior to opposite SRS face.

## 20. SRS Double bolt path

For each common bolt:

`POSITIVE_BASE_ANGLE_VERTICAL_LEG -> SOLID_RECTANGULAR_COLUMN -> NEGATIVE_BASE_ANGLE_VERTICAL_LEG`.

No fictitious cavity.

## 21. Angle selected-leg identity

Allow exactly the existing two physical column-leg identities.

The user selects one leg.

The other leg remains physical geometry and must participate in:

- interference;
- heel clearance;
- visible scene;
- material-axis presentation.

## 22. Angle Single side

User selects one broad face of the chosen leg.

Physical bolt path:

`BASE_ANGLE_VERTICAL_LEG -> SELECTED_ANGLE_COLUMN_LEG`.

External head/washer at connector side.

External nut/washer at opposite broad face of selected column leg.

No connector exists on the opposite broad face.

## 23. Angle Double topology

Exactly:

`POSITIVE_BASE_ANGLE_VERTICAL_LEG -> SELECTED_ANGLE_COLUMN_LEG -> NEGATIVE_BASE_ANGLE_VERTICAL_LEG`.

The two connectors lie on opposite broad faces of the **same selected column leg**.

Do not connect different Angle-column legs in Stage 3.7A.

## 24. Future moment topology exclusion

Reject any request representing:

- one base angle on Leg Y; plus
- one base angle on Leg Z.

Return a controlled scope rejection equivalent to:

`ANGLE_COLUMN_TWO_DIFFERENT_LEGS_MOMENT_BASE_NOT_IN_STAGE_3_7A_SCOPE`.

Do not silently reinterpret it as Double.

## 25. Angle interference

Fail closed for:

- connector heel collision with the other column leg;
- connector vertical leg overlap inconsistent with face contact;
- horizontal-leg positive-volume collision with column geometry;
- anchor/column interference;
- impossible bolt path.

No automatic angle flip/move/resize.

## 26. Column axial component demand

For every profile:

- column local/member transfer axial signed action = `P_L`;
- design magnitude = `|P_L|`;
- demand fraction = `1.0`;
- material axis classification = `LW`.

Profile-specific local layer handoff remains governed by existing accepted physical-path architecture.

Do not create new RHS near/far-wall force-sharing equations.

## 27. Base-angle-system axial component demand

For every profile:

- base-angle-system signed axial action = `P_L`;
- design magnitude = `|P_L|`;
- system demand fraction = `1.0`;
- base-angle vertical-leg material axis = `CW`.

Column and connector system demands are serial adequacy checks and are never summed into the foundation reaction.

## 28. Single branch demand

Single connector receives full connector-system action.

Any geometric eccentricity between member action line and connector/anchor reference is retained as exact moment in the handoff.

## 29. W/I Double sharing

Preserve Stage 3.5C exact symmetry proof and branch-allocation behavior.

No historical transition.

## 30. RHS/SRS Double sharing

Authorize complete 50/50 branch sharing only if all are exact:

- selected/opposite faces are geometric mirrors about member centroid;
- identical base-angle geometry/materials;
- mirrored anchor groups;
- common member reference on the mid-plane;
- `V_T = 0`;
- zero user moment.

Then supported in-plane branch forces are exact halves.

If proof fails:

branch allocation `NOT_EVALUATED`.

## 31. Angle Double common-group layer allocation

For the supported in-plane physical common-bolt demand, after exact connector/selected-leg local symmetry:

- positive base-angle layer = `0.5 Q_i`;
- selected Angle-column leg layer = `1.0 Q_i`;
- negative base-angle layer = `0.5 Q_i`.

This is local in-plane layer provenance only.

## 32. Angle Double complete branch-wrench allocation

Because the Angle-column member centroid is generally offset normal to the selected-leg plane, connector geometric symmetry does not by itself prove complete action symmetry.

Retain exact combined system/foundation wrench.

Unless the backend proves the complete action/reference state is branch-symmetric:

`ANGLE_COLUMN_BASE_ANGLE_BRANCH_WRENCH_ALLOCATION = NOT_EVALUATED`.

Do not fabricate 50/50 anchor-group wrenches.

## 33. Angle centroid eccentricity

For Angle profiles, retain the exact vector from member-end reference to selected leg/common bolt/anchor references.

Axial force may therefore generate a real moment.

Connection-plane shear may also generate additional moment depending reference offset.

These generated moments are part of the exact external base/anchor handoff.

Do not suppress them because user moment input is zero.

## 34. Connection-normal action

`V_T` is normal/bolt-axis action.

Preserve existing limitation:

- no automatic bolt-axis tension resistance;
- no prying closure;
- no unsupported complete Double branch allocation.

The complete foundation wrench is retained.

## 35. Compression contact

For `P_L < 0` preserve external unresolved partition where applicable:

`COLUMN_END_VS_BASE_ANGLE_BEARING_PARTITION = EXTERNAL_DESIGN_REQUIRED`.

No new contact stiffness model.

## 36. Uplift contact

For `P_L > 0`:

direct column-end bearing is not a tensile path.

Return not-required state for column-end bearing.

Retain:

- base-angle body/heel uplift limitation;
- horizontal-leg prying limitation;
- anchor tension external;
- concrete uplift anchorage external.

## 37. Foundation reaction

The physical foundation force/wrench is assembled once from the canonical member action and exact translation.

Never add column-design demand and base-angle-system design demand.

## 38. Anchors/concrete

Preserve external design boundary.

No anchor or concrete capacity equation.

Export exact:

- anchor coordinates;
- branch wrenches when authorized;
- combined foundation wrench;
- geometry;
- sign convention;
- provenance;
- limitations.

## 39. Local FRP checks

Reuse accepted local checks where applicability exists:

- actual per-bolt demand;
- pin bearing;
- net tension;
- shear-out;
- block shear;
- existing bolt/local handoff.

Use actual layer material basis and actual force direction.

If a new profile/path cannot map an existing failure mode legitimately:

return `NOT_EVALUATED`.

Do not invent a resistance equation.

## 40. Full-through material layers

RHS cavity:

- no material properties;
- no bearing;
- no resistance check;
- no LW/CW/TT axes.

SRS:

- continuous material.

Angle:

- selected physical leg only in the column/base-angle bolt path.

## 41. Material axes

With axes enabled, show backend-authored axes for:

- all active W/I regions;
- all active RHS walls;
- SRS region(s);
- both Angle-column legs;
- base-angle vertical/horizontal legs.

Concrete has no FRP axes.

## 42. Preview

Preview performs:

- validation;
- geometry;
- action/reference translation;
- Stage 2.5A demand where already accepted;
- symmetry/applicability proof;
- external handoff;
- visualization;
- statuses.

Preview resistance calls:

`0`.

## 43. Explicit design

Run Design Check:

- current accepted preview;
- existing authorized local FRP/bolt checks only;
- no new concrete/anchor/body/prying equation;
- limitations retained.

## 44. Whole-result precedence

1. invalid input/geometry -> invalid;
2. supported numerical failure -> `FAIL`;
3. otherwise required external/not-evaluated state -> `NOT_EVALUATED`;
4. do not issue ordinary whole-connection PASS across required unsupported/external states.

## 45. Frontend workspace

Reuse the existing column-base workspace.

Current successor profile selector exposes exactly:

- W/I;
- Rectangular Hollow Section;
- Solid Rectangular Section;
- Angle.

Assembly selector exposes:

- Single;
- Double.

Use dynamic profile-specific controls.

Historical W/I loaders/contracts remain reproducible.

## 46. RHS UI

Expose:

- outside dimensions;
- wall thickness;
- display height;
- selected contact face;
- Single/Double.

Double automatically identifies opposite face.

Do not expose an internal hardware option.

## 47. SRS UI

Expose:

- outside dimensions;
- display height;
- selected contact face;
- Single/Double.

No wall-thickness field.

## 48. Angle UI

Expose:

- Leg Y width;
- Leg Z width;
- thickness;
- display height;
- selected leg;
- selected broad face for Single;
- Single/Double.

For Double, side selector becomes locked/opposite broad faces of selected leg.

Do not expose different-leg Double.

## 49. Visualization

Render actual:

- profile geometry;
- concrete base;
- Single/Double base angles;
- physical through-bolts;
- anchors;
- RHS cavity / SRS solid;
- other Angle-column leg;
- exact action arrows;
- material axes;
- selected surface/leg;
- no ghost/internal hardware.

## 50. Default successor fixture

Normal successor default may remain W/I historical default for regression stability.

Profile-specific controlled fixtures:

### RHS
- `10 x 8 in`;
- wall `0.5 in`;
- display height `24 in`;
- selected face normal depth `8 in`;
- cavity `7 in`.

### SRS
- `10 x 8 in`;
- display height `24 in`.

### Angle
- `6 x 6 x 0.5 in`;
- display height `24 in`.

Base-angle/fastener/anchor defaults reuse historical Stage 3.5C values unless geometry invalidity requires an explicit controlled profile fixture.

## 51. Required golden cases

At minimum:

G1. Historical Stage 3.5C-R2 W/I Single exact.
G2. Historical Stage 3.5C-R2 W/I Double exact.
G3. Successor W/I physical equivalence.
G4. Profile selector exactly W/I/RHS/SRS/Angle.
G5. Assembly selector exactly Single/Double.
G6. RHS Single selected-face geometry.
G7. RHS Single full-through path.
G8. RHS Single cavity free-shank only.
G9. RHS Single external-only hardware.
G10. RHS Double opposite-face geometry.
G11. RHS Double common through-bolt path.
G12. RHS Double no duplicate physical bolt.
G13. RHS Double exact 50/50 in-plane branch proof when eligible.
G14. RHS Double `V_T != 0` branch allocation not evaluated.
G15. SRS Single full solid-depth path.
G16. SRS Double Plate/Solid/Plate path.
G17. SRS no fictitious cavity.
G18. SRS Double exact 50/50 in-plane branch proof when eligible.
G19. Rectangular face-pair orientation changes authoritative frame.
G20. Rectangular opposite face derived backend-side.
G21. Angle selected Leg Y geometry.
G22. Angle selected Leg Z geometry.
G23. Angle Single one connector / one selected broad face.
G24. Angle Single bolt through connector + selected leg only.
G25. Angle Double connectors on both broad faces of same selected leg.
G26. Angle Double common Plate/Leg/Plate bolt identity.
G27. Angle other leg retained in geometry.
G28. Angle heel/perpendicular-leg collision invalid.
G29. Different-leg double topology rejected as future moment scope.
G30. Angle backend member centroid/reference used.
G31. Angle centroid-to-selected-leg eccentricity retained.
G32. Angle axial generated moment retained.
G33. Angle common-group 0.5/1.0/0.5 in-plane layer provenance after local symmetry.
G34. Angle complete branch-wrench allocation not inferred without action symmetry.
G35. Column axial demand = 100% / LW for W/I.
G36. Column axial demand = 100% / LW for RHS.
G37. Column axial demand = 100% / LW for SRS.
G38. Column axial demand = 100% / LW for Angle selected leg/member transfer.
G39. Base-angle system axial demand = 100% / vertical-leg CW.
G40. Single connector receives full connector-system action.
G41. Foundation axial action counted once.
G42. Compression bearing partition external.
G43. Uplift column-end bearing not required.
G44. Anchor/concrete capacity external.
G45. Connection-normal bolt-axis response limitation.
G46. RHS cavity has no material axes.
G47. SRS solid material axes.
G48. Angle both-leg material axes visible.
G49. Base-angle material axes visible.
G50. Preview zero resistance.
G51. Supported numerical failure precedence.
G52. U.S./SI W/I equivalence.
G53. U.S./SI RHS equivalence.
G54. U.S./SI SRS equivalence.
G55. U.S./SI Angle equivalence.
G56. Deterministic successor fingerprints.
G57. Stage 3.5 freeze regression exact.
G58. Stage 3.6 freeze regression exact.
G59. Stage 3.2/3.3/3.4 frozen regressions exact.
G60. Direct/Tee/Clip-Angle/Multi-Member-Tee/Web-Splice regressions exact.

## 52. U.S./SI

Equivalent physical profile/assembly inputs shall preserve:

- geometry;
- action references;
- generated moments;
- physical bolt paths;
- material layers;
- Stage 2.5A demand;
- branch applicability;
- foundation handoff;
- statuses;
- fingerprints.

## 53. Fingerprints

Successor engineering identity includes:

- profile family;
- physical column geometry;
- selected face/leg;
- local frame;
- member action reference;
- assembly type;
- Single/Double topology;
- full-through path identity;
- exact generated moments;
- symmetry/applicability;
- component-demand provenance;
- limitations;
- contract version.

Presentation excluded.

Historical Stage 3.5 fingerprints remain exact.

## 54. Deliberate exclusions

Stage 3.7A does not authorize:

- Angle-column connector on two different column legs;
- explicit user moment;
- moment-resisting Angle-column base;
- Channel column;
- unequal Double connectors;
- new anchor/concrete design;
- new angle-body/heel/prying equation;
- new bolt-axis tension response;
- fabricated Angle complete branch allocation.

## 55. Acceptance boundary

Stage 3.7A is accepted only if:

- W/I behavior stays exact;
- RHS/SRS full-through physics are correct;
- Angle selected-leg physical geometry is correct;
- Double Angle uses both broad faces of the same selected leg only;
- member centroid/reference eccentricity is preserved for Angle;
- RHS/SRS Double sharing is exact only after symmetry;
- Angle complete branch sharing is not fabricated;
- column axial demand remains 100% LW;
- base-angle-system axial demand remains 100% CW;
- foundation reaction counted once;
- concrete/anchors remain external;
- all frozen families remain exact;
- local/object-isolated QA passes;
- hosted CI 4/4 passes;
- owner visual acceptance passes.

**END OF STAGE 3.7A COLUMN-BASE PROFILE MATRIX EXPANSION ENGINEERING SPECIFICATION RC1**
