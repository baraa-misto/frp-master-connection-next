# FRP Master Connection — Stage 3.2-R2 Unified Workspace + Member/Profile Architecture — Engineering Specification RC1

## 1. Status

**Controlled owner engineering specification — RC1**

Stage 3.2-R2 corrects the Stage 3.2 product/workspace architecture revealed during V1 visual review.

This specification authorizes:

- one reusable desktop connection-workspace shell;
- connection-template selection through a scalable dropdown;
- persistent connection visualization while engineering inputs scroll independently;
- replacement of the Stage 3.2 generic connected-member plate with a controlled member/profile model;
- profile-to-interface surface selection and geometry mapping;
- support for physically compatible connected-member profile families in the Tee simple-connection workflow;
- clearer user-facing naming for the Tee connection;
- continued reuse of the accepted Stage 2 and Stage 3.2 engineering engines.

It does **not** authorize new resistance equations.

Stage 3.2 remains open until this correction, hosted CI, and renewed V1–V4 visual acceptance are complete.

## 2. Accepted starting baseline

Expected repository baseline after Stage 3.2-R1:

- `HEAD == origin/main`: `1aa2ce6e2b9663e43ff99ae8313c38646de95c7e`
- subject: `test: harden frontend integration timing on Windows`
- commit count: `47`
- tracked files: `305`
- Stage 3.2 production frontend tree: `241dc569cb17aef5bd05eba604962607b730411f`
- immutable Stage 2.3 freeze tag: `stage-2.3-interface-geometry-freeze`
- freeze target: `5bc545ab8251f9bd49dedc776962937ed5e822a2`

Stage 3.2-R1 hosted CI is accepted 4/4 green with 227/227 frontend tests on Ubuntu and Windows.

## 3. User visual-review findings controlling this correction

The Stage 3.2 V1 review identified these product issues:

1. Connection-template buttons do not scale to the future connection library.
2. The Tee template uses a large top form and forces the user to scroll away from the 3D view.
3. The 3D view should remain visible while engineering options/results scroll.
4. The label `FRP Tee · two interfaces` exposes internal architecture rather than a clear connection name.
5. The connected member is rendered as a generic plate rather than as a real structural member/profile.
6. Connected/supported member role, section family, size/dimensions, orientation, and selected connection surface must be distinct engineering concepts.
7. The same workspace shell should be used by all current and future connection templates.

These are requirements, not optional UX suggestions.

## 4. Core product rule — one connection workspace shell

Every shear/simple-connection template shall use the same desktop workspace shell.

A template may supply different engineering panels and scene content, but shall not create a separate page/form/viewer layout.

Desktop target:

```text
+---------------------------------------------------------------+
| Header / category / connection-type dropdown                  |
+----------------------+----------------------------------------+
|                      |                                        |
| Engineering sidebar  | Persistent canonical connection view   |
| independently        |                                        |
| scrollable           | remains visible while sidebar scrolls  |
|                      |                                        |
|                      +----------------------------------------+
|                      | Results / inspectors / trace            |
|                      | independently accessible                |
+----------------------+----------------------------------------+
```

The viewer shall occupy the majority of usable desktop width. Responsive/mobile layouts may stack, but desktop behavior is controlling for Stage 3.2-R2.

## 5. Persistent-view requirement

On desktop:

- the canonical connection viewer remains visible while the user scrolls through engineering controls;
- the engineering sidebar has independent vertical scrolling;
- long result/trace content shall not force the viewer completely off screen;
- viewer camera state survives sidebar scrolling;
- switching collapsible engineering sections does not reset the camera;
- display-only viewer operations do not stale engineering results.

Implementation may use a bounded viewport workspace with independent scroll regions and/or a sticky viewer, provided the observable behavior satisfies this specification.

Do not create nested scrolling that prevents normal wheel/trackpad access to sidebar or results.

## 6. Connection-type selector

Replace the horizontal connection-template button strip with a scalable dropdown.

User-facing label: `Connection type`.

Use existing framework/native grouping capability; no new dependency is authorized.

At minimum, current options shall be named:

### Brace connections

- `Brace connection — Direct`
- `Brace connection — Tee connector`

Internal architecture terms such as `two interfaces` shall not appear in the connection-type label.

Future groups may include Beam shear connections, Truss connections, Member splices, Bases/anchorage, Handrails/guardrails, and Moment connections. Do not expose unimplemented future options as working selections.

## 7. Dynamic connection title

Generate a readable title from actual engineering selections, for example:

- `FRP Angle Brace → FRP Tee → W Column Flange`
- `FRP Channel Brace → FRP Tee → W Beam Flange`
- `FRP Rectangular Tube Brace → FRP Tee → W Column Flange`

This is display text only and does not replace stable engineering IDs.

## 8. Member/profile architecture

A structural member shall no longer be modeled as only a role plus generic width/thickness.

Introduce or generalize an immutable member/profile contract with separate concepts.

### 8.1 Member role

At minimum the architecture supports identities for `BRACE`, `BEAM`, and `COLUMN`, and is extensible to truss chord/diagonal, handrail post, rail, stair stringer, and other roles.

Stage 3.2-R2 production Tee use keeps supporting-member roles `COLUMN` and `BEAM`.

The connected/supported member in the current Tee brace connection remains role `BRACE`.

A future beam-shear Tee template shall reuse this architecture but need not be activated by R2 unless existing action/orchestration can support it without new engineering authority.

### 8.2 Section/profile family

At minimum implement production geometry contracts for:

- `ANGLE`
- `CHANNEL`
- `WIDE_FLANGE_I`
- `RECTANGULAR_HOLLOW_SECTION`
- `FLAT_PLATE`

Also establish an extensible identity for `ROUND_HOLLOW_SECTION`, but do not permit a round/curved surface to connect directly to a flat Tee stem without a separately defined compatible interface/adapter.

### 8.3 Size / dimensions

Support `CUSTOM_DIMENSIONS` for every enabled profile family.

Do not invent a manufacturer/catalog size database.

The architecture shall permit future catalog/profile IDs without breaking custom dimensions.

### 8.4 Material

Member material identity remains separate from profile geometry. The current connected brace remains controlled FRP. Material selection does not infer strength.

### 8.5 Orientation

Member orientation is separate from section family. Changing orientation moves the authoritative profile and selected connection surface.

### 8.6 Connection surface

A profile exposes stable physical surfaces that may be selected by a connection template. Only physically meaningful surfaces shall be selectable.

## 9. Profile local-frame convention

Use a right-handed member local frame:

- `X` — member longitudinal axis;
- `Y` — first cross-section axis;
- `Z` — second cross-section axis.

Authoritative section geometry is defined in the `Y-Z` cross-section and extruded along `X`.

All section dimensions are exact Decimal values. Display meshes may use floating-point rendering transforms, but backend/domain geometry remains authoritative.

## 10. Profile families and minimum dimensions

### 10.1 Angle

Required: `leg_y`, `leg_z`, `thickness`, `member_length`.

Validity: all > 0; `thickness < leg_y`; `thickness < leg_z`.

Minimum selectable exterior flat surfaces:

- `LEG_Y_OUTER`
- `LEG_Z_OUTER`

### 10.2 Channel

Required: `depth`, `flange_width`, `web_thickness`, `flange_thickness`, `member_length`.

Validity: all > 0; `2 * flange_thickness < depth`; `web_thickness < flange_width`.

Minimum selectable flat surfaces:

- `WEB_OUTER`
- `FLANGE_POS_OUTER`
- `FLANGE_NEG_OUTER`

### 10.3 Wide-flange / I section

Required: `depth`, `flange_width`, `web_thickness`, `flange_thickness`, `member_length`.

Validity: all > 0; `2 * flange_thickness < depth`; `web_thickness < flange_width`.

Minimum selectable flat surfaces:

- `WEB_POS_FACE`
- `WEB_NEG_FACE`
- `FLANGE_POS_OUTER`
- `FLANGE_NEG_OUTER`

### 10.4 Rectangular hollow section

Required: `depth`, `width`, `wall_thickness`, `member_length`.

Validity: all > 0; `2 * wall_thickness < depth`; `2 * wall_thickness < width`.

Minimum selectable exterior flat surfaces:

- `Y_POS_FACE`
- `Y_NEG_FACE`
- `Z_POS_FACE`
- `Z_NEG_FACE`

### 10.5 Flat plate

Required: `width`, `thickness`, `member_length`.

Validity: all > 0.

Minimum selectable surfaces:

- `FACE_POS`
- `FACE_NEG`

This profile remains available for legitimate flat-plate members/details but shall no longer masquerade as the default representation of every brace.

### 10.6 Round hollow section

Future geometry identity: `outer_diameter`, `wall_thickness`, `member_length`.

R2 may render it if inexpensive, but it shall not be offered as a valid direct flat Tee-stem contact surface.

## 11. Connected brace profile applicability for the Tee template

For `Brace connection — Tee connector`, permit only profile/surface combinations that provide a real flat contact face for Interface A.

At minimum enable:

- Angle brace: `LEG_Y_OUTER`, `LEG_Z_OUTER`.
- Channel brace: `WEB_OUTER`, and exterior flange surfaces where bolt-group bounds permit.
- W/I brace: web faces, and exterior flange faces where geometry/orientation permits.
- Rectangular hollow-section brace: any exterior flat face.
- Flat-plate brace: either face.
- Round hollow-section brace: not selectable for direct Tee-stem contact in this stage.

The UI filters surfaces based on the chosen profile family. Do not show meaningless surface choices.

## 12. Supporting member model

Migrate or adapt existing W-column/W-beam support geometry through the same member/profile architecture.

R2 production Tee support remains:

- role `COLUMN` with `WIDE_FLANGE_I`; or
- role `BEAM` with `WIDE_FLANGE_I`.

The current physical support-flange selection remains explicit: positive local flange or negative local flange.

Support role changes global orientation/placement. Underlying W/I profile geometry and surface IDs are shared.

Do not duplicate W-column and W-beam cross-section geometry.

Future channel/RHS/other support shapes are roadmap-compatible but not automatically authorized here because bolt access/layer-stack behavior may differ.

## 13. Connected-member size controls

Sidebar controls shall be profile-family-specific.

Examples:

- Angle: Leg Y, Leg Z, Thickness, Member/View length.
- Channel: Depth, Flange width, Web thickness, Flange thickness, Member/View length.
- W/I: Depth, Flange width, Web thickness, Flange thickness, Member/View length.
- Rectangular tube: Depth, Width, Wall thickness, Member/View length.
- Flat plate: Width, Thickness, Member/View length.

Do not present irrelevant dimensions for the selected profile.

## 14. Interface A mapping — Brace ↔ Tee Stem

Construct Interface A from the selected real brace profile surface.

Required:

- selected brace surface plane is authoritative;
- Tee-stem contact plane is coincident with that surface as defined by connection geometry;
- bolt axes are normal to the actual brace/Tee-stem interface;
- bolt-group bounds are checked against the finite brace surface and Tee stem;
- penetrated-layer identity uses the real brace profile component/surface, not a generic plate placeholder;
- material-direction mapping remains explicit.

Changing brace family, dimensions, selected surface, or orientation updates Interface A geometry and stales prior design results.

## 15. Interface B mapping — Tee Flange ↔ Support

Interface B remains independent.

Required:

- use the shared W/I support profile;
- selected physical flange face is authoritative;
- bolt axes are normal to the actual contact plane;
- Interface B layout remains independent of Interface A;
- support role `COLUMN` vs `BEAM` changes placement/orientation, not Tee equations or W/I cross-section math.

## 16. No change to Stage 3.2 engineering mechanics

R2 creates no new demand or resistance method.

Reuse unchanged:

- Stage 2.5A eccentric in-plane bolt-group demand;
- Stage 2.5B resistance handoff;
- Stage 2.6A eccentric line-resultant shear-out compatibility;
- Stage 2.6B automatic integration;
- Stage 3.1 material/authority gating;
- Stage 3.2 two-interface transformation/orchestration;
- Stage 3.2 interface-normal fail-closed behavior;
- Stage 3.2 Tee-body `NOT_EVALUATED` limitation.

Profile geometry determines the real interface plane and bounds; it does not authorize new strength equations.

## 17. Member-body resistance boundary

R2 does not create general local/member-profile strength checks beyond accepted interface resistance paths.

Where existing FRP bearing/net/shear/block checks and prerequisites are satisfied, they may run unchanged.

Do not invent channel flange bending, angle-leg bending, tube wall flexure, local crippling, local buckling, profile-specific prying, or unsupported member-body limit states.

Required but unimplemented behavior remains fail-closed.

## 18. Sidebar information architecture

Reorganize the Tee connection into the same collapsible sidebar pattern as the established direct connection.

Recommended order:

1. General / Case
2. Connection
3. Connected Member
4. Supporting Member
5. Connector
6. Interface — Brace ↔ Tee Stem
7. Interface — Tee Flange ↔ Support
8. Materials
9. Fasteners
10. Loads / Member-End Action
11. Factors / Method
12. Model / Geometry Status
13. Design Results
14. Advanced / Diagnostics

Exact labels may follow existing terminology, but information shall not return to one giant top form.

## 19. Interface naming

Normal UI shall prefer physical names:

- `Brace ↔ Tee Stem`
- `Tee Flange ↔ Support`

Internal stable IDs may remain Interface A / Interface B in API/debug trace.

The user should not need to understand `Interface A` or `two interfaces` to operate the software.

## 20. Viewer interaction improvements

Establish reusable selection/highlight behavior where practical without a new dependency.

Minimum required:

- editing Brace ↔ Tee Stem visually emphasizes that interface/bolt group;
- editing Tee Flange ↔ Support emphasizes that interface/bolt group;
- selected component identity remains visible in the viewer.

Preferred if it fits current scene architecture:

- clicking a member/connector/bolt group focuses or expands its sidebar section.

If viewer-to-sidebar click selection materially broadens scope, implement one-way sidebar-to-viewer highlighting now and record click-to-edit as a near-term requirement.

## 21. Results and geometry linkage

Results remain grouped by physical interface and use physical interface labels.

At minimum result cards clearly identify:

- Brace ↔ Tee Stem;
- Tee Flange ↔ Support;
- Tee connector body.

Preferred: expanding/clicking a result highlights the related geometry.

## 22. Stale-result behavior

Engineering changes stale/clear design results, including:

- connection type;
- connected-member role where enabled;
- connected-member profile family;
- connected-member dimensions;
- connected-member selected surface;
- connected-member orientation;
- supporting role;
- supporting W/I dimensions;
- selected support flange;
- Tee dimensions;
- either interface layout;
- material/fastener authority;
- loads/reference point.

Display-only changes do not stale results:

- camera rotate/pan/zoom;
- Front/Top/Side/Fit/Reset;
- overlay visibility;
- accordion open/closed state;
- interface highlight used only for presentation.

## 23. Connection-template persistence boundary

Switching connection type may preserve common case/member/load values only where engineering meaning is identical.

Do not silently reuse incompatible connector/interface geometry.

Restoring prior session-only form state when returning to a previously edited connection type is preferred if it does not confuse stale-result identity.

No project persistence is introduced.

## 24. API/application contracts

Add or generalize contracts for:

- member role;
- profile family;
- profile dimensions;
- profile orientation;
- selected physical connection surface;
- stable surface IDs;
- profile geometry/fingerprint identity.

Backend/domain validates profile dimensions, supported family/surface combinations, Tee-template applicability, and interface bounds.

Frontend shall not generate authoritative profile surfaces.

Existing direct/Stage 2 requests remain backward compatible.

## 25. Deterministic engineering identity

Engineering fingerprints include where applicable:

- member role;
- profile family;
- exact profile dimensions;
- profile material;
- profile orientation;
- selected connection surface;
- supporting role/profile/surface;
- Tee geometry;
- both bolt layouts;
- canonical action/reference;
- fastener/material authority.

Exclude UI open/closed state, viewer highlight, camera, dropdown display label, colors, and responsive-layout state.

No existing Stage 2 fingerprint may change.

## 26. Controlled geometry benchmarks

The companion R2 golden file controls profile/surface geometry and invariance. It creates no new resistance equation.

At minimum it covers:

- angle brace surface mapping;
- channel brace web surface mapping;
- W/I brace web surface mapping;
- rectangular tube face mapping;
- flat-plate compatibility;
- W support role column/beam local geometry invariance;
- surface filtering;
- Interface A/B independence;
- stale versus display-only state behavior.

## 27. Visual acceptance after R2

### V1-R2 — Brace → Column flange → FRP Tee

Verify dropdown connection selection, persistent viewer, independent sidebar scrolling, real brace profile, real Tee, W-column support, correct two bolt groups, physical interface names, and Tee-body limitation.

Run at least two connected brace profiles: Angle and either Channel or Rectangular Tube.

### V2-R2 — Brace → Beam flange → same Tee

Verify same workspace shell, W support becomes beam, shared Tee implementation, physical selected flange, and equivalent local demand for equivalent local inputs.

### V3-R2 — Independent layouts

Change Brace ↔ Tee Stem layout without moving Tee Flange ↔ Support, then reverse.

### V4-R2 — Normal action fail-closed

Apply nonzero interface-normal action. Verify it is retained, no bolt-axis tension is fabricated, and ordinary PASS is prohibited.

### V5-R2 — Persistent viewer / member-profile UX

Scroll top-to-bottom through the engineering sidebar while the viewer remains visible. Change member profile family, profile dimensions, and selected profile surface and verify authoritative geometry updates live.

## 28. Acceptance boundary

Stage 3.2-R2 is acceptable only when:

- workspace layout is unified;
- connection selector is scalable;
- Tee naming is user-facing and clear;
- connected brace is a real profile;
- member/profile/surface architecture is backend-authoritative;
- support W/I geometry is shared for beam/column roles;
- no new resistance equation is introduced;
- all existing controlled hashes remain exact;
- full Windows/Ubuntu CI is green;
- renewed V1-R2 through V5-R2 visual acceptance passes.

Only then may Stage 3.2 be closed.

**END OF CONTROLLED ENGINEERING SPECIFICATION — RC1**
