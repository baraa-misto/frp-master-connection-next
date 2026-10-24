# HYB2-D3-P2: common Direct connection workflow

Successor to accepted P1 `6dbac59869f7dc9042fdfe642ef1026acecad9b1`.
This stage changes input ownership, presentation and material-axis display. It
does not adopt structural methods or grant whole-connection qualification.

## One current physical connection

The public two-bolt Direct entry always opens the same workspace, with or without
the historical `?workspace=direct-hybrid` launch alias. There is no public switch
between a native ASCE application and a Hybrid application. The retained native
layout component continues to serve the other supported bolt counts. Its existing
independent compatibility suite remains separate from public-entry integration
tests and actual common-workspace browser verification.

`DirectHybridWorkspace` owns one current input object, one workspace identifier,
one monotonic revision and one viewer. `DirectConnectionInputs` presents its shared
member, hole, bolt and boundary controls. Native and source inputs describe
different physical end definitions; these remain explicit. They are not calculation
basis selectors. The backend `HybridInputs` validation remains unchanged: it accepts
one physical representation and rejects simultaneous native/R3 inputs or results.
There is no presumed conversion from the source oblique-cut geometry to an approved
native ASCE calculation contract.

Both presets replace inputs in these same controls only after confirmation. A full
previous-input snapshot supports Restore previous inputs; restoring advances the
revision and never restores a result or report handle. The RHM preset is explicitly
identified as a sample. Its actual vertical bolt spacing remains 2 inches, with
the accepted R3 projections and one bolt pair for both connected members. Source
properties and source conditions remain distinct from native MAT1/F593 selections.
The native example preserves the session's actual selected materials/conditions;
it does not choose project-specific environmental conditions on the user's behalf.

Changing calculation basis invalidates results without changing geometry. Opening
supplemental controls is presentation only. All six entered action components,
frames, reference points and independent LRFD/ASD case lists remain explicit.
No LRFD-to-ASD force conversion is introduced. Every executed check is fresh and
is subject to the existing geometry, source, material and method applicability
guards. The source sample cannot borrow eight results from the different native
layout. Unavailable or unrequested methods retain their backend reasons.

Native material preview ownership is registered through the existing MAT1 state.
An external-store observer reconciles current material, condition and hardware
changes with the current native request and invalidates its result immediately.
The hidden parent layout preview is suspended while the common workspace owns the
connection. Incomplete native project conditions do not fall back silently to
legacy properties in this new UI. Historical backend signed-request behavior is
unchanged. Independent source ASD calculations do not acquire native MAT1 factors.
Native hole edits coordinate the same declared hole in the geometry template,
two-bolt request and material-envelope legacy request before fresh validation.

## Region-specific material axes

The source scene now owns exactly five planar material-axis regions: both Angle
legs and the receiving I's two flanges and web. LW follows the established R3 brace
P direction and the I member's longitudinal direction. R3 source x/y maps to viewer
X/Z; the bolt/stack direction is viewer Y. A sign-insensitive connected-leg CW of
minus n gives a right-handed LW/CW/TT display frame. Receiving-I LW/CW/TT uses
global Z/X/Y. The existing `create_region_specific_planar_orientations` rule rotates
CW/TT for the other Angle leg and the I web. These display directions never enter
or change a resistance or demand calculation.

`buildHybridScene` uses the existing region-embedded presentation builder and exact
backend owner/element/region identities. Axis lengths and anchors are presentation
only. No root, fillet or junction orientation is invented. Nominal source I8 depth,
web thickness and display crops retain their prior limitations and confer no new
physical-fit or resistance authority. Native geometry retains its original
canonical material directions.

Material axes (LW/CW/TT) is visible beside the camera controls without opening the
overlay menu. The established labels, colors and TT marker legend are reused in
3D and all orthographic views. Its visibility survives current-model replacement;
changing an overlay does not execute engineering or invalidate signed results.
Solid/X-ray mode changes renew only the two mesh material types. This prevents a
shader compiled as opaque from painting over the axes after a mode transition;
geometry, camera state and the demand-driven rendering loop are retained.

## Results, currentness and reports

Before calculation, a compact input/readiness message replaces the large
unevaluated result indicator. Executed checks use engineer-readable component and
mechanism names. Utilizations have three display decimals; the backend outcome is
never inferred from that rounded display. Exact values remain in Technical Audit
and the authenticated JSON. Required coverage and project-material limitations
remain visible beside the scoped numerical result. Field-use/provenance detail is
retained without repeated qualification notices.

The original account, signature, expiry, native currency, fingerprint, late-response,
revision and post-render export checks remain in force. Edits clear result/export
authority immediately. Basis-only or source-action changes retain unchanged
physical geometry rather than remounting its viewer. Reports render the current
immutable backend record; they do not calculate another design or generate
engineering conclusions using a language model. Full original native and source
evidence remains in the technical appendix and JSON.

## Bounded governance and verification

The P2 successor changes only the governed backend test count in the CI workflow,
then reconstructs the exact accepted P1 workflow before all older guards. The same
four Windows/Ubuntu jobs, security gates, exact 100% coverage scopes and thresholds,
14 live reports and 27 inherited report controls remain configured.

All 53 protected engineering identities and 171 historical controls retain their
accepted P1 raw working identities and published Git blob identities. The two
dependency locks retain exact P1 predecessor records through the separately
owner-approved P2 security successor. The cross-platform
check permits only the exact pre-existing P1/Git checkout byte representations
recorded in the successor, including Git's existing newline rules. Final external
verification separately checks unchanged raw working files and unchanged published
blob OIDs; no generic engineering tolerance or data normalization is introduced.
The bounded dependency exception pins Vitest and coverage-v8 to 4.1.12 with seven
matching Vitest internals, and pypdf to 6.21.1. All other frontend package records
and 54 backend versions are unchanged. The successor reconstructs exact P1 files
before the unchanged older guards; no audit suppression or coverage reduction is
introduced. Material values, frozen engines, original workbook streams, native
F8/F9 authority, C13 criteria and Section 2.3.2 requirements are unchanged.

The delivered evidence records targeted and full local QA, numerical preservation,
actual PDFs and rendered pages, desktop/narrow browser cases, exact-SHA hosted CI
and an isolated final candidate runtime. Completion is readiness for owner review,
not owner acceptance, qualification, merge, freeze or deployment.
