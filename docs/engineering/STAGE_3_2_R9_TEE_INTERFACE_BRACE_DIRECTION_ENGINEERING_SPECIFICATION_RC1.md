# FRP Master Connection — Stage 3.2-R9 Independent Tee Interfaces + Brace Direction + Complete Fastener Presentation — Engineering Specification RC1

## 1. Status

**Controlled owner engineering specification — RC1**

Stage 3.2-R9 consolidates three product gaps identified during Stage 3.2 visual acceptance:

1. the two physical Tee bolt groups must be independently configurable and must not be forced to have equal bolt counts or equal layouts;
2. the connected brace needs an arbitrary backend-authoritative in-plane inclination control that is distinct from profile roll about the member axis; and
3. the Tee 3D scene must use the same accepted solid bolt/head/nut/washer presentation as the existing direct/reference connection.

R9 creates **new connection-placement geometry authority only for brace inclination**.

R9 does **not** create a new demand equation, resistance equation, fastener strength model, connector-body resistance model, or member-body resistance model.

## 2. Accepted starting baseline

Expected repository baseline after Stage 3.2-R8:

- `HEAD == origin/main`: `c05ac82ce49c8516503f9eaacbdb526e881c8f50`
- subject: `fix: resolve profile wall bolt paths`
- commit count: `53`
- tracked files: `331`
- clean worktree/index
- frontend source tree: `40956420c22c42910a8a2cbe82c74ed2e6a5f407`
- immutable Stage 2.3 freeze tag: `stage-2.3-interface-geometry-freeze`
- freeze target: `5bc545ab8251f9bd49dedc776962937ed5e822a2`

Stage 3.2-R8 hosted CI is accepted 4/4 green with 259/259 frontend tests across 20 files.

## 3. Controlling inherited behavior

R9 shall preserve without modification:

- Stage 2.4A accepted row-distribution authorities and their applicability limits;
- Stage 2.4B resistance calculations;
- Stage 2.5A eccentric in-plane demand mechanics;
- Stage 2.5B resistance handoff;
- Stage 2.6A group-mode compatibility;
- Stage 2.6B automatic integration;
- Stage 3.1 material/fastener authority architecture;
- Stage 3.2 Tee two-interface topology;
- Stage 3.2 Tee-body `NOT_EVALUATED` limitation;
- Stage 3.2 interface-normal fail-closed behavior;
- Stage 3.2-R2 member/profile architecture;
- Stage 3.2-R4 exact-unit geometry;
- Stage 3.2-R5 deterministic cross-platform geometry/fingerprints;
- Stage 3.2-R6 current/pending/invalid/last-valid preview state behavior;
- Stage 3.2-R7 Angle leg bolt-path rules;
- Stage 3.2-R8 Channel/W-I/RHS wall bolt-path rules and RHS access qualification.

No previously controlled fingerprint may change for a legacy/default input.

# PART A — INDEPENDENT TEE INTERFACES

## 4. Physical independence rule

The Tee assembly has two distinct physical interfaces:

- `Brace ↔ Tee Stem`
- `Tee Flange ↔ Support`

They transfer the same connector load path through the Tee body, but they are **not** one-to-one matched bolt sets.

There is no engineering rule requiring:

`number of bolts on Tee stem == number of bolts on Tee flange`

or:

`row count A == row count B`

or:

`bolts per row A == bolts per row B`.

Each physical interface owns its own:

- row count;
- bolts per row;
- pitch;
- gauge;
- end distances;
- side distances;
- bolt coordinates;
- stable bolt IDs;
- penetration/layer paths;
- demand result;
- resistance result;
- geometry fingerprint.

Changing one interface shall not mutate the other interface's engineering geometry.

## 5. Geometry-domain counts

The profile/Tee preview geometry shall allow independently, subject to finite-surface geometry:

- `rows >= 1`
- `bolts_per_row >= 1`

for each interface.

This is a **geometry capability**.

It does not imply that every current automatic calculation method is authorized for every count combination.

Examples that shall be physically representable when finite geometry permits:

- Stem `1 x 2` = 2 bolts; Flange `2 x 2` = 4 bolts;
- Stem `2 x 1` = 2 bolts; Flange `2 x 2` = 4 bolts;
- Stem `2 x 3` = 6 bolts; Flange `3 x 2` = 6 bolts;
- Stem `3 x 2` = 6 bolts; Flange `2 x 2` = 4 bolts.

No hidden equality validator shall couple the groups.

## 6. Calculation applicability remains separate

If an interface geometry is valid but a current Stage 2 method does not support that row/count configuration:

- preview geometry remains valid;
- the unsupported design method shall be identified as not applicable / not evaluated / qualification required according to existing status architecture;
- the other interface shall not be changed merely to enter a supported method;
- no new row-distribution equation may be invented.

In particular, a `1 x 2` physical group shall not be automatically assigned a new multi-row distribution rule merely because its geometry is supported.

If an already accepted single-row/single-bolt-group authority applies exactly, it may be reused under its existing prerequisites.

## 7. Independent identity and stale behavior

Interface A and Interface B shall have separate canonical form/revision identities.

Changing only Interface A:

- stales the current design result;
- requests a new preview;
- changes only Interface A geometry/result identity;
- preserves Interface B geometry unless the change physically forces a connector-level geometry rejection.

Changing only Interface B follows the inverse rule.

A connector-level dimension change may legitimately affect both because the shared Tee body changed.

# PART B — BRACE INCLINATION

## 8. Separate engineering concepts

The UI/domain shall distinguish:

### Brace inclination

Rotates the **entire brace member axis** within the current Tee brace-placement plane.

### Profile roll about member axis

Rotates/orients the brace cross-section about its own longitudinal axis using the existing R2 profile-orientation semantics.

These are not aliases.

Rename the normal user-facing `Profile orientation` label to:

`Profile roll about member axis`

or repository-equivalent wording.

## 9. Brace inclination input

Add an exact numeric engineering input:

`brace_inclination_degrees`

User-facing label:

`Brace inclination`

The control shall accept arbitrary decimal degree values within the current planar Tee-brace domain:

`-90° <= θ <= +90°`

Default:

`0°`

Examples accepted:

- `0`
- `30`
- `-30`
- `27.5`
- `42.75`
- `90`
- `-90`

Values outside the current domain shall be rejected explicitly.

Do not implement this as a preset-only dropdown. Presets may be added only as optional convenience around the arbitrary numeric field.

## 10. Inclination sign/reference convention

The angle is measured in the backend-defined Tee brace-placement plane.

`0°` shall reproduce the existing Stage 3.2 Tee brace direction exactly.

Positive inclination rotates the brace toward the template's canonical **up** direction.

Negative inclination rotates it toward the opposite direction.

The sign convention shall be independent of camera/view orientation.

Use the existing canonical template/global frame to define:

- `L0` — existing 0° brace longitudinal unit direction;
- `U0` — canonical in-plane up unit direction;
- `N` — brace placement/interface-plane normal.

Require:

- `L0 · U0 = 0`
- `L0 · N = 0`
- `U0 · N = 0`
- right-handed repository-consistent frame.

For inclination `θ`:

`Lθ = cos(θ) L0 + sin(θ) U0`

and the in-plane transverse direction shall rotate consistently so the placement frame remains orthonormal/right-handed.

Reuse the deterministic trigonometric authority established by Stage 3.2-R5. Do not introduce a second trig implementation.

## 11. Connection-surface coincidence

Changing brace inclination shall rotate the complete connected member while preserving the selected physical brace connection surface as the Interface A contact surface against the Tee stem.

The backend shall recompute:

- connected-member placement;
- selected profile surface transform;
- Interface A local frame;
- Interface A bolt coordinates;
- physical bolt axes;
- finite-surface containment;
- penetration/layer paths;
- relevant reference/frame trace.

Do not rotate only the display mesh.

## 12. Interface A bolt-group orientation

Interface A layout coordinates remain defined in the existing canonical group frame tied to the connected brace/interface.

When brace inclination changes:

- row/gauge/pitch semantics do not change;
- the physical bolt-group pattern rotates with the connected brace/interface placement as defined by existing layout axes;
- all holes must remain fully inside the finite Tee stem and connected-member surface patches;
- invalid rotated layouts fail closed under existing R6 preview behavior.

R9 does not authorize automatic resizing or layout relocation to make a rotated pattern fit.

## 13. Tee and support placement

Changing brace inclination does not, by itself, rotate the Tee flange or the supporting member.

The Tee/support remain in their existing template placement.

Only geometry that is physically dependent on the brace/Interface A placement shall change.

Interface B shall remain geometrically identical for a pure brace-inclination edit unless a connector-level validity rule explicitly invalidates the assembly.

## 14. Load/action semantics

Preserve the existing Tee member-end action input convention.

Changing brace inclination does **not** silently rotate the user-entered global/canonical force vector.

Instead:

- current canonical/global action and physical reference point remain what the user entered;
- the backend recomputes their transformation into the updated interface/member frames;
- existing Stage 2.5A / Stage 3.2 orchestration resolves the resulting demand without equation changes.

If a future member-axis-load convenience mode is desired, it requires a separate controlled feature.

## 15. Inclination and demand fingerprints

For nonzero inclination, the engineering identity shall include the exact normalized inclination value and resulting authoritative geometry.

Backward compatibility requirement:

- omitted inclination in legacy requests shall mean `0°`;
- explicit `0°` shall be semantically identical to omitted/default;
- all existing controlled `0°` Stage 3.2/R4/R5 fingerprints shall remain exact.

Nonzero R9 cases receive new deterministic fingerprints under existing hashing architecture.

## 16. Inclination stale behavior

Changing brace inclination is engineering-significant:

- stale/clear prior design result;
- request new backend preview;
- invalidate stale selected-bolt state if entity geometry no longer matches;
- do not reset camera unnecessarily.

Changing profile roll follows existing engineering-stale behavior.

# PART C — COMPLETE FASTENER PRESENTATION

## 17. Presentation parity rule

The Tee 3D viewer shall use the already accepted fastener presentation from the direct/reference connection rather than a reduced Tee-specific bolt depiction.

For every displayed Tee bolt on both interfaces, render as applicable:

- solid shank;
- bolt head;
- nut;
- authoritative washer(s) already available in the fastener model/presentation path.

Do not introduce a separate Tee-only fastener geometry standard.

## 18. Schematic head/nut ratios

Until authoritative standard hardware geometry is modeled, preserve the accepted **presentation-only** schematic ratios:

### Bolt head

- across flats: `1.50 d`
- height: `0.625 d`

### Nut

- across flats: `1.50 d`
- thickness: `0.875 d`

These values:

- are not engineering connection geometry;
- do not enter calculation;
- do not enter engineering fingerprint;
- do not imply an ASTM/ASME hardware dimension.

## 19. Washer presentation

Where the current accepted fastener snapshot/model has authoritative washer geometry, render it using that authority.

Do not invent washer engineering dimensions from the schematic head/nut ratios.

If a washer property is not authoritative in the current model, preserve the same direct-workspace behavior rather than creating Tee-specific data.

## 20. Hardware placement direction

Reuse the direct/reference connection's hardware placement convention based on the actual physical bolt axis and layer/entry/exit side.

Do not hard-code world-axis head/nut placement.

For both Tee interfaces:

- head and nut shall lie on opposite sides of the penetrated stack;
- hardware shall rotate with bolt axis;
- a changed brace inclination shall move Interface A hardware consistently;
- Interface B hardware remains tied to Interface B axes;
- no hollow/cage shank regression.

## 21. Presentation-only identity

Head/nut schematic dimensions, visual tessellation, and colors shall not enter engineering fingerprints.

Fastener diameter and authoritative washer geometry continue to participate only where already engineering-relevant.

# PART D — APPLICATION / API / UI

## 22. API compatibility

Extend the Tee request/schema backward-compatibly with optional:

`brace_inclination_degrees`

Default it to exact zero when omitted.

Do not break current Stage 3.2 requests.

The result/preview trace shall expose the normalized accepted inclination and authoritative brace direction/frame so the client does not infer it.

## 23. Sidebar organization

Within `Connected Member`, show in a clear order:

1. Brace profile family
2. Family-specific dimensions
3. Brace inclination
4. Profile roll about member axis
5. Brace connection surface

Use a numeric input for inclination.

Interface A and Interface B layout sections remain separate.

## 24. User-facing independence

Do not label either physical group merely as generic `Interface A/B` in the normal sidebar.

Continue:

- `Brace ↔ Tee Stem`
- `Tee Flange ↔ Support`

Each shows its own row/count controls.

If the user selects geometry-valid but method-unsupported counts, explain the design-method limitation without changing the input.

## 25. Viewer/inspector

Expose inclination in an existing frame/placement inspector or concise connected-member trace.

When editing/focusing Interface A, keep existing R2/R6 highlighting behavior.

Complete fastener hardware shall remain visible in Front/Top/Side/3D views as physically applicable.

# PART E — CONTROLLED REGRESSION

## 26. Required interface-independence cases

At minimum prove:

### I1

- Stem: `2 rows x 1 bolt` = 2 total bolts
- Flange: `2 rows x 2 bolts` = 4 total bolts

Expected:

- preview geometry valid when finite bounds permit;
- total counts exactly `2` and `4`;
- no equality validator;
- changing Stem count does not change Flange coordinates.

### I2

- Stem: `1 row x 2 bolts` = 2 total bolts
- Flange: `2 rows x 2 bolts` = 4 total bolts

Expected:

- preview geometry may be valid;
- design applicability is determined independently;
- no new multi-row method is invented.

### I3

Change only Flange from `2 x 2` to `3 x 2` under valid geometry.

Expected Stem geometry value-equivalent.

## 27. Required inclination cases

### D1 — 0°

- exact legacy geometry;
- exact legacy controlled fingerprints.

### D2 — +30°

Using R5 deterministic trig:

- `cos(30°) = 0.8660254037844386`
- `sin(30°) = 0.5`

Expected longitudinal basis:

`L30 = 0.8660254037844386 L0 + 0.5 U0`

### D3 — -30°

Expected:

`L-30 = 0.8660254037844386 L0 - 0.5 U0`

### D4 — arbitrary decimal

`27.5°` is accepted as a numeric engineering input and produces a deterministic nonzero placement/fingerprint.

No preset limitation.

### D5 — boundary

`+90°` and `-90°` accepted subject to physical geometry validation.

Values outside the current planar domain reject before calculation.

## 28. Required fastener-presentation cases

For each Tee interface:

- shank count equals engineering bolt count;
- head count equals displayed bolt count;
- nut count equals displayed bolt count;
- washer count follows existing authoritative presentation rules;
- head/nut are on opposite sides of stack;
- hardware axis matches bolt axis;
- head/nut schematic ratios match accepted values;
- changing `d` scales the presentation;
- engineering fingerprint is unchanged by schematic head/nut rendering.

## 29. Cross-feature cases

At minimum:

1. valid Angle brace at `+30°`, Stem `2 x 1`, Flange `2 x 2`;
2. valid Channel brace at `-30°`;
3. valid RHS brace at nonzero inclination retains `INTERNAL_FASTENER_ACCESS_REQUIRED`;
4. inclination edit leaves Interface B geometry unchanged;
5. invalid rotated Interface A layout triggers R6 last-valid-preview state;
6. correcting the layout recovers current-valid preview;
7. profile roll change remains distinct from inclination change.

## 30. Controlled golden

The companion R9 golden controls:

- interface independence semantics;
- inclination basis cases;
- arbitrary numeric inclination acceptance;
- default-zero backward compatibility;
- schematic head/nut presentation ratios.

It does not authorize new resistance values.

## 31. Visual acceptance after R9

### V1-R9 — Independent interfaces

Set:

- Brace ↔ Tee Stem = `2 x 1`
- Tee Flange ↔ Support = `2 x 2`

Verify 2 bolts vs 4 bolts physically, with no forced equality.

Then change only one group and confirm the other does not move.

### V2-R9 — Brace inclination

Use a valid Angle brace.

Check:

- `0°`
- `+30°`
- `-30°`
- one arbitrary value such as `27.5°`

Verify the entire brace and Interface A geometry follow the inclination while Tee/support and Interface B remain fixed.

### V3-R9 — Profile roll independence

With brace inclination fixed at `+30°`, change profile roll using existing supported values.

Verify this changes cross-section orientation without changing the requested brace inclination.

### V4-R9 — Hardware

Verify both interfaces show:

- solid shank;
- head;
- nut;
- washer presentation as authorized.

Rotate the 3D view to inspect both sides.

### V5-R9 — Invalid rotated geometry

Deliberately make a rotated Interface A layout invalid.

Verify R6 last-valid-preview state and design gating.

Then recover.

## 32. Acceptance boundary

R9 is accepted only if:

- interface bolt counts/layouts are truly independent;
- a 2-bolt Stem group can coexist with a 4-bolt Flange group;
- unsupported calculation count combinations fail closed without geometry coupling;
- arbitrary in-plane brace inclination works backend-authoritatively;
- profile roll remains a separate concept;
- nonzero inclination correctly updates physical geometry/frame/action transformation;
- zero inclination preserves all legacy fingerprints;
- complete accepted fastener presentation appears on both interfaces;
- no new engineering calculation equation is introduced;
- all previous controlled hashes/fingerprints remain exact;
- hosted CI is 4/4 green;
- V1-R9 through V5-R9 pass.

Only then resume final Stage 3.2 beam/unit-system acceptance and closure.

**END OF CONTROLLED ENGINEERING SPECIFICATION — RC1**
