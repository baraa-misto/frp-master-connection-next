# Frontend Application Shell

## Control status

| Control item | Value |
|---|---|
| Stage | 0.2.3 — permanent frontend toolchain and noncalculating application shell |
| Starting baseline | `f31940ea232ade6df935f5612393a7126fa56e30` |
| Implementation status | Complete and reviewed; controlled validation passed |
| Approval status | Provisionally accepted as the frontend application foundation |
| Freeze status | Draft / not frozen |

## Purpose and scope

Stage 0.2.3 establishes the first permanent browser application boundary for FRP
Master Connection. It is a private React and TypeScript package built with Vite and a
small, original, responsive shell. The shell communicates product structure and
safety limits while deliberately performing no engineering work.

The frontend is not a design tool. Engineering calculations are not implemented, and
no displayed content is a validated engineering result. The implementation contains
no project persistence, force entry, engineering geometry, calculation, visualization,
API integration, authentication, authorization, entitlement, billing, or report
generation.

## Package manager and lock policy

`frontend/package.json` is private and intentionally has no independent package
version. `npm@11.16.0` is the package manager, and the provisional tested runtime is
Node 24.18.0 with the narrow engine range `>=24.18.0 <24.19.0`. npm uses
`>=11.16.0 <11.17.0`. Direct dependency specifications are exact.

The backend metadata service remains the future authoritative source for the product's
runtime version. The visible frontend does not duplicate or invent that version.

`frontend/package-lock.json` is the authoritative exact resolved dependency tree for
Stage 0.2.3. It uses lockfile version 3 and the public npm registry and contains 290
nonroot records plus the root record, for 291 total. `npm ci`, rather than a mutable
install, is the controlling installation and reproducibility command.

Two independent clean installations consumed the existing lock and reproduced 266
normalized installed locations each. Their normalized tree hash was identical:
`E9BF9E4B1AA0A28402E2B262C2758C4365651F7AC6BB791D890DD6F59CD63192`.
Neither `npm ci` nor the subsequent QA changed `package.json`, `package-lock.json`, or
`.npmrc`.

Fresh `package-lock.json` generation from `package.json` alone is dependency-update
resolution, not the controlling Stage 0.2.3 reproducibility test. That separate
availability check resolved `electron-to-chromium` 1.5.401 instead of the accepted
lock's 1.5.400 and `node-releases` 2.0.52 instead of 2.0.51. Those transitive updates
are deferred to a separate controlled dependency-maintenance task. The accepted lock
remains unchanged at SHA-256
`E0F3FE693B6FDED14ADB4282E2820E9862B4E442145C24F3A6290F814B42DA65`, and no
production or cross-platform toolchain freeze is implied.

The two runtime dependencies are React 19.2.8 and React DOM 19.2.8. Development
dependencies are TypeScript 6.0.3, Vite 8.2.0, `@vitejs/plugin-react` 6.0.5, Vitest
4.1.10, `@vitest/coverage-v8` 4.1.10, React Testing Library 16.3.2, Testing Library
DOM 10.4.1, jest-dom 7.0.0, jsdom 30.0.1, ESLint 9.39.5, `@eslint/js` 9.39.5,
typescript-eslint 8.66.0, the React Hooks plugin 7.1.1, the React Refresh plugin
0.5.3, React types 19.2.18, React DOM types 19.2.4, and Node types 24.13.3.

## Application structure

- `src/main.tsx` and `src/app/mountApplication.tsx` form the tested bootstrap boundary.
- `src/app/` composes the application and its semantic shell.
- `src/domain/designCategories.ts` defines display-only primary category data.
- `src/features/CategorySelector.tsx` provides accessible category selection.
- `src/views/WorkspacePreview.tsx` arranges nonfunctional workspace areas.
- `src/components/PlaceholderPanel.tsx` provides reusable placeholder presentation.
- `src/styles.css` is the only styling implementation and uses native CSS.

No implementation was added to the reserved `geometry`, `services`, or `state`
directories merely to replace their `.gitkeep` files.

## Primary categories

The first selection level contains exactly two categories and begins with neither
selected:

1. **Shear Connections** — Non-moment-resisting beam, brace, splice, and support
   connections.
2. **Moment Connections** — Joint assemblies containing at least one intentionally
   moment-resisting member interface, including applicable shear.

The category controls are semantic buttons. `aria-pressed`, text, border treatment,
and an explicit selected label expose selection without relying on color alone.
Selection changes only a display heading; it creates no project or engineering data.

## Workspace and unavailable actions

The responsive workspace preview labels Project, Members and Geometry, Manual Forces,
Results, 3D View, Front View, Top View, and Side View. Every panel explicitly states
that its associated capability is not implemented. It contains no force or geometry
input, structural value, model, canvas, result, or drawing dimension.

Calculate and Generate Report are disabled in the DOM. Both reference an accessible
explanation stating that calculation and reporting behavior are unavailable. They have
no event path, endpoint, or state transition that can produce a result.

## Accessibility, layout, and visual treatment

The shell uses semantic `header` and `main` landmarks, a logical heading hierarchy,
keyboard-operable buttons, visible focus indicators, accessible selected states, and
described disabled actions. The near-black text, off-white surfaces, neutral borders,
and steel-blue `#4A6FA5` accent provide restrained contrast. Layouts collapse for
narrow screens, and the stylesheet honors reduced-motion preferences without adding
unnecessary animation. System fonts and native CSS avoid external asset and font
requests. This treatment is provisional and is not a frozen design system.

## Trust boundary

The frontend is an untrusted client. It establishes no identity, accepts or stores no
account or organization ownership claim, authorizes no project access, and enforces no
role, capability, entitlement, subscription, or billing state. It stores no token,
credential, secret, private service address, or database identifier. It uses no cookie,
`localStorage`, `sessionStorage`, or IndexedDB persistence.

There is no backend API client or proxy in this stage. A future integration must obtain
authoritative identity, authorization, project data, product metadata, calculations,
and report behavior from reviewed server boundaries; browser state cannot become
authority for any of them.

## Visualization boundary

Three.js, React Three Fiber, Drei, and their type packages are not permanent
dependencies in this stage. The 3D area is text-only and renders no structural model.
When canonical geometry work is separately authorized, the 3D workspace must be
lazy-loaded or otherwise split from the initial route and must remain a derived view,
never a source of engineering resistance or calculation input.

## Validation evidence

The reviewed Windows validation used Node v24.18.0 and npm 11.16.0. The package has 19
exact direct specifications; its authoritative lock has 291 records including root and
290 nonroot records. Two independent `npm ci` environments produced 266 installed
locations each and the identical normalized tree hash recorded above. The repository
bootstrap script and aggregate `frontend-check.ps1` script passed, as did `npm ls
--all`, zero-warning ESLint, and strict TypeScript.

Two test files ran 35 tests, all passing. V8 coverage was 19/19 statements, 6/6
branches, 9/9 functions, and 19/19 lines: 100% for every measured dimension. This 100%
coverage applies only to the current Stage 0.2.3 executable shell. It does not validate
engineering mathematics, an engineering calculation engine, or commercial use.

The production build transformed 22 modules and generated three files: `index.html`
at 529 bytes, the main JavaScript asset at 195,692 bytes, and the CSS asset at 5,212
bytes. Vite emitted zero warnings and no source map. A Vite preview bound only to
`127.0.0.1` returned HTTP 200, referenced both built assets, and was stopped
successfully. Full and runtime-only npm audits each reported zero vulnerabilities at
every severity.

Both clean installations passed dependency-tree, lint, type, test, coverage, build,
and audit gates with the same outcomes. Validation changed no repository-controlled
file. Temporary clean installations and all build, coverage, cache, tree, log, and
preview outputs were removed. The repository scripts reproduce the local environment
and fail-fast quality gates without a global installation.

## Explicit exclusions and remaining risks

This stage excludes project storage, force entry, engineering contracts, member or
connection geometry, calculations, code criteria, visualization, 2D drawing
generation, API integration, authentication, ownership, authorization, entitlement,
billing, reports, templates, routing, external state management, telemetry, CI, and
deployment configuration.

Remaining work requiring controlled validation or review includes:

- Linux and CI reproduction;
- retesting on a newer Node 24 patch before broadening the supported range;
- real-browser screen-reader testing;
- automated contrast testing;
- browser zoom testing;
- real-device responsive testing;
- real-browser reduced-motion validation;
- end-to-end browser automation;
- API contract and backend metadata integration;
- authentication, project ownership, authorization, entitlement, and billing design;
- project persistence;
- the canonical geometry model and visualization boundary; and
- qualified engineering calculation development and validation.

`PRIMARY_CATEGORY_NAME_BY_ID` duplicates the two names held in
`PRIMARY_DESIGN_CATEGORIES`. The current values agree and the reviewed tests pass, so
this is a minor future drift/maintenance risk rather than a Stage 0.2.3 blocker.
Refactoring it after validation is deliberately deferred to a separate controlled
change.

Stage 0.2.3 implementation is complete and reviewed, validation passed, and the shell
is provisionally accepted as the frontend application foundation. Stage 0.2.4
integrated repository QA/CI has not started. This evidence does not approve a
production runtime, cross-platform toolchain, design system, deployment, engineering
method, or commercial release. Engineering calculation implementation has not started,
and the application remains unusable as an engineering design tool.

## Stage 2.3 engineering-workspace implementation

The shell now hosts one real, bounded Shear workflow for the verified single-bolt/
single-row slice. It uses a strict same-origin typed API client, J1 U.S./SI input-only
loaders, supported member/bolt/material/load/factor controls, explicit resolved-demand
and fail-closed member-end modes, stale-result clearing, a server-authoritative
summary/table/trace, and canonical visualization. Moment Connections remains clearly
not implemented.

Three.js and React Three Fiber are exact-pinned presentation dependencies. A pure
scene-model boundary maps the backend snapshot into 3D/Front/Top/Side views; WebGL
does not calculate geometry, demand, resistance, status, or units. The workspace is
session-only and uses no browser persistence. Semantic labels, keyboard focus,
non-canvas inspectors, an accessible canvas description, responsive layouts, and
reduced-motion styling are required. Authentication, authorization, entitlement,
project persistence, reports, multirow work, and approved bolt-demand distribution
remain absent.

## Stage 2.3R connection-first refinement

The shell now prioritizes the connection viewer while retaining a compact 340-pixel
desktop property sidebar, responsive single-column fallback, independently scrolling
property groups, a sticky evaluation control, and a collapsible results/details
drawer. Materials and the locked F593 preset use compact source cards. Engineer-
friendly labels are the normal presentation; stable internal IDs, versions, and
fingerprints remain available under diagnostics and exact details.

At narrow widths, the sidebar, viewer, and results drawer remain within the document
width; wide calculation tables scroll within their own container. Editable numerical
fields show concise unfocused values and reveal the unchanged exact request string on
focus, so presentation cleanup does not alter transport precision.

The refinement adds no route, browser persistence, analytics, alternate API host,
frontend engineering formula, identity claim, or dependency. Three.js remains lazy-
loaded through the established React Three Fiber boundary.

## Stage 2.3R4 viewport-interaction correction

The viewer owns exactly one OrbitControls instance per mounted camera/canvas lifecycle
with explicit left-rotate, right-pan, and wheel-zoom mappings. The associated change
listener updates the viewport-corner triad through direct SVG attributes and invalidates
the demand-rendered scene; it never writes workspace React state on every camera change
and uses no `useFrame` or request-animation-frame loop. Cleanup removes the listener
and disposes the controls.

Selectable model geometry records a pointer-down candidate but defers selection until
a matching primary-button pointer-up stays within the four-pixel click threshold.
Pointer-down remains available to OrbitControls, so dragging over W, angle, bolt, or
contact geometry navigates while clicks still select. Static legends and the corner
triad are pointer-transparent. Navigation cannot call the calculation API, stale a
result, edit geometry, or enter a fingerprint; controlled inputs remain the only
physical-geometry editing surface.

## Stage 2.3R5 request scheduling and status shell

The frontend has separate Model/Geometry Status and Design Results surfaces. The
preview scheduler classifies every controlled value as preview-affecting, design-only,
or presentation-only. Numeric preview edits wait 200 ms, discrete preview edits issue
immediately, and each request carries a monotonic sequence and model revision.
`AbortController` cancels superseded work; an older or aborted response cannot replace
the latest model, surface an error, or make design results current.

Only the explicit `Run Design Check` action calls the design endpoint. A current,
valid, design-ready preview is required. Preview-affecting edits visibly stale any
previous result, including while a new preview is pending or invalid. Design-only
edits stale results but do not request a preview. Presentation-only edits do neither.
Local invalid numeric fields suppress preview transport and explain the field error;
network errors retain the prior model as outdated and offer Retry. No browser
storage, persistence, background calculation, or frontend engineering formula is
introduced.

## Stage 2.3R6 shared inputs and preview-only extents

The workspace holds one member-action state object. Sidebar fields and applied-arrow
editors read and update those same strings; the overlay owns only a temporary draft
while an editor is open. Valid Enter/blur commits through the shared updater, Escape
or invalid blur cancels, and invalid text triggers no request. The next accepted
preview supplies direction, sign, and unit display.

Engineering-and-preview edits, including `e1`, directed angle, and loads, increment
the engineering revision and stale old design. View-extent edits increment only the
preview revision. Design-only factors stale without preview; camera/display controls
do neither. Angle relationships and connected-end geometry are never computed in the
frontend. `Run Design Check` remains the only design request.

## Stage 2.3R7 projected action-label shell

The visualization shell projects presentation points from the existing force-arrow
and moment-arc primitives into an absolute DOM label layer. The layer is full-size but
pointer-transparent; only applied label/editor bounds are interactive. One
OrbitControls change callback updates both the fixed corner triad and label element
coordinates without a React state update per camera change, `useFrame`, or an
animation-frame loop. The current React/Three/R3F dependencies and lock are unchanged.
The fitted physical-unit profile also supplies presentation-only camera clipping
planes so equivalent U.S. and SI scenes remain visible without changing model data.

All six applied components use signed concise values and server-returned units beside
their own primitives. The old detached action-card container is removed. Positive
convention symbols are separately styled, nonnumeric, pointer-transparent, and
noneditable. The editor retains the one workspace action state plus a temporary local
draft; sidebar synchronization, preview debounce/cancellation/latest-response-wins,
stale-design behavior, and explicit `Run Design Check` are unchanged.
