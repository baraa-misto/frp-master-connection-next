# FRP Master Connection - CME-1
# Shared FRP / 316SS Connector-Material Foundation and All-Family Integration Plan - RC1

**RECOMMENDED CODEX EFFORT: HIGH**

**Program:** Connector Material Expansion (CME). This identifier does not renumber any existing calculation slice or frozen development stage.

**Task type:** Implement shared backend contracts, role enforcement, source/applicability and provider dispatch infrastructure, native FRP compatibility adapters, additive capability/planning interfaces, and an exhaustive existing/future-family registration mechanism. Produce the implementation-ready stainless rollout ledger.

**Not this task:** Implement or claim a complete stainless resistance engine, convert all existing workspaces to stainless, activate a production stainless design selector, change primary-member material, or freeze CME-1 automatically.

## 1. Owner-authorized product direction

The long-term product shall offer FRP or 316 stainless steel for each applicable connecting body: clip angles, base angles, flange angles, splice/web/flange plates, tee connectors and other verified connecting bodies. Apply the architecture to every current applicable shear and moment family and require it for future families.

Beams, columns, braces, and structural/support members remain FRP-only. A structural member with an angle, tee, channel, hollow, solid or plate cross-section does not become a selectable stainless connector merely because of its shape. Concrete foundations remain concrete. Bolts, nuts, washers, anchors and connector bodies have separate material identities.

This order is the first implemented foundation of that program. It must leave a real reusable code path and complete migration inventory, not only a prose plan. Conversely, registering SS316 as a target must not be described as having implemented stainless design.

## 2. Exact starting repository state

Repository: `C:\Users\green\Documents\New project\frp-master-connection`.

Remote: `https://github.com/baraa-misto/frp-master-connection.git`.

Require in the active execution checkout:

`HEAD == origin/main == remote main == 998911ea78872b852ef097dd4e20d666a33a935a`

Expected commit count: **124**.

Use `git log -1` to verify the actual subject and record it; this order does not guess a subject that was not supplied in the completion evidence.

The Stage 4.5 annotated freeze tag is:

`stage-4.5-wi-rhs-srs-column-moment-bases-freeze`

Its peeled target must remain `998911ea78872b852ef097dd4e20d666a33a935a`. Verify all **13** existing freeze-tag object identities and peeled targets locally and remotely using the committed freeze ledger. Do not derive product counts from tag counts.

Owner-reported accepted baseline evidence: 5,045 backend tests; 848 frontend tests; 100% configured coverage; zero audit findings; fresh isolated verification; hosted CI #119, attempt 2, four jobs green. Treat those as historical evidence, not today's freshly executed commands.

Require clean worktree/index in the active checkout. Leave obsolete drafts and other running worktrees untouched. A clean separate working area is permitted; do not require a shallow verification clone to contain the full count-124 history or main branch. Commit-count checks belong in the full-history execution checkout.

If actual baseline identity, tag identity or unrelated worktree state differs, consolidate and stop before mutation. Do not reset, discard, amend, rebase or force-push to make it match.

## 3. Package and authority hierarchy

Read this file and its companion completely:

`FRP_MASTER_CONNECTION_CME_1_ACCEPTANCE_AND_REFERENCE_FIXTURES_RC1.json`

Companion SHA-256:

`247B49CA529AB9F8C509025DBF8DFA3B832F5BE102C1464ED518DC370D2FD89A`

The owner handoff separately provides this order's SHA-256. Verify both final sentinels. Do not require a file to contain its own digest.

Authority order for this task:

1. The owner's current connector-only material direction and count-124 accepted baseline.
2. Applicable source provisions and the already-controlled native engineering specifications, with edition/applicability recorded.
3. This CME-1 scope and companion contracts/fixtures.
4. Current repository conventions where consistent with the above.

The August 2026 handoff's old Stage 2.x stopping point is historical, not the current execution baseline. Do not reopen those stages or overwrite newer accepted controls.

This order adds architectural policy; it does not silently replace an ASCE reference with a newer stainless standard. No equation or material property may be invented to fill a source gap.

## 4. Source review and the stainless design-basis gate

The companion contains a source register S1-S8. It explicitly distinguishes reviewed source content, publisher metadata and unreviewed normative documents.

**Supplied ASCE/SEI 74-23:** Sections 2.9, 8.1 and 8.1.3 distinguish metallic connecting elements from FRP connecting elements requiring the stated qualification. Sections 8.2-8.3 retain FRP-side and fastener requirements. Section 1.4.2 requires compatibility and material properties as well as equilibrium in analysis. Table C8-1 distinguishes FRP/FRP and FRP/steel row distributions. Section 5.5.2 specifically addresses pultruded doubler plates. These provisions inform component roles and applicability, not a universal substitution license. [S1, S8]

**Stainless-specific standard discovery:** AISC's current publisher listing identifies ANSI/AISC 370-25; its June 30, 2026 release also identifies AISC 313-25. This package did not obtain or verify the complete 370-25 normative PDF. Record 370-25 as the candidate new stainless component basis requiring clause-level verification before numerical activation. Do not implement from a public-review draft or silently fall back to 370-21/ordinary carbon-steel equations. Preserve ASCE 74-23's actual cited AISC 360 edition in the historical reference chain. A documented code-basis bridge and project applicability review is a CME-2 prerequisite, not an assertion that the new edition is automatically adopted by every jurisdiction. [S3, S4]

**Material product forms:** The official ASTM A240/A240M-26 abstract covers plate/sheet/strip and expressly distinguishes inch-pound and SI standard values. The ASTM catalogue separately lists A276/A276M-25 bars/shapes, A666/A666M-24 annealed/cold-worked flat products and A1069/A1069M-23 laser-welded built-up shapes. These are source-discovery targets, not numerical property tables already checked by this package. [S5, S6]

Do not prescribe generic `Fy`, `Fu`, elastic modulus or design factors from the word 316SS. Exact grade, material condition, thickness/size, product specification, fabrication and source domain matter. Do not use an F593 fastener record as evidence for an angle or plate body.

Search existing project source locations and records first. Reuse previously supplied readable ASCE/erratum and native engine copies. If a new stainless source is not accessible, record one precise gap in the source ledger and finish the foundation; numerical stainless design is outside this order. Do not repeatedly ask the owner to reattach known PDFs.

Acquire new public publisher documents through ordinary approved access only. Do not bypass access controls, purchase a standard, disclose credentials or upload licensed/private material. Keep licensed PDFs outside Git. Store locators, verified metadata and permitted derived engineering records, not copied standards pages.

## 5. Why a resistance-only material switch is insufficient

Reuse the existing separation in Slice 7: its resolved-wrench transport core is material-neutral; its resistance provider is material-specific. That separation is valid for an **already resolved input wrench**. [S7]

It does not prove that load distribution remains unchanged after replacing a connector. Contact, connector flexibility, prying, bolt deformation, composite action and multi-connector sharing may depend on material and fabrication. Do not keep an FRP-qualified response after a stainless substitution without explicit domain support. The supplied Table C8-1 already demonstrates different material-pair branches in an applicable legacy method. [S1, S8]

The expansion architecture must therefore separate:

`topology/geometry -> applicability and material-dependent response -> resolved wrenches -> native transport -> per-component resistance -> completeness/qualification`

A material-neutral core can be reused without treating all upstream demand as material-neutral. No automatic half/quarter sharing, bolt-tension zero, rigid stainless assumption or friction/slip resistance is introduced.

## 6. Executable deliverables in CME-1

Implement all of the following using current acyclic repository conventions:

1. Immutable component-role, connector-material, fabrication, source-domain and capability contracts.
2. A pure component-role/material-assignment validator, including shared physical identity and protected reinforcement rules.
3. A shared connector-provider registry/protocol with native FRP delegation and explicit stainless-not-implemented behavior.
4. Material-sensitive response/source invalidation planning that does not fabricate branch forces.
5. A complete actual product/mode/connector inventory linked to executable registration checks.
6. Stateless additive capability and material-assignment planning endpoints, with no new resistance execution.
7. A small read-only Connector Material Readiness diagnostic, reachable without creating a third primary design category or changing the normal engineering workspace controls.
8. Executable regression and native integration tests for the above, plus a source/applicability/migration ledger for CME-2 and subsequent family integration.

Do not restructure all frozen engines as part of this foundation. Use new adapters around native interfaces where possible. No production stainless capacity evaluator is authorized in CME-1, even if a source happens to become accessible during execution.

## 7. Exhaustive inventory - current and future families

Before mutation discover the actual set of products and modes from backend dispatch, frontend selectors, canonical assembly builders and committed governance. Do not equate one freeze tag with one product or guess current IDs from document titles.

For each product/mode record:

- actual product/mode IDs, shear or moment category, relevant accepted baseline;
- actual primary members and their FRP material/axis authority;
- every physical connector body/assembly, aliases, paired components and shared-body identity;
- separate member reinforcement, fasteners and foundations;
- body form and manufacturing assumptions;
- native geometry, demand, transport, FRP resistance and qualification entry points;
- whether each upstream demand is material-neutral, material-dependent, externally qualified or unresolved;
- target provider/check families, family-adapter work, missing source needs and proposed rollout wave;
- explicit `NO_CONNECTOR_BODY`, `FRP_REINFORCEMENT_RESTRICTED` or equivalent disposition where applicable.

Coverage must include direct bolted connections, tees and multi-member tees, single/paired clip angles, concrete-support shear connections, web and moment splices, column-base shear, W/I and Channel moment splices, wall/FRP-support moment connections, the angle-column base, and W/I/RHS/SRS bases wherever they actually exist. These are discovery categories, not a predeclared exhaustive ID list. Include additional existing registered products without requesting filename-by-filename approval.

Create a machine-readable bijection between the runtime product/mode set and the inventory. A future product or mode lacking a declared role/material policy must fail the new registration test. Adding a new family legitimately extends the current registry; it must not invalidate an old frozen whole-file digest.

## 8. Component-role policy

Use explicit semantic roles, adapting names to existing enums:

- `PRIMARY_MEMBER`: beam, column, brace and FRP receiving/support member; FRP only.
- `CONNECTOR_BODY`: discrete angle, plate, tee, gusset or other connecting body; target families FRP and SS316 subject to capability.
- `MEMBER_REINFORCEMENT`: doubler/stiffener/local member reinforcement with its own source/applicability restriction. Not automatically equivalent to a free connector plate.
- `FASTENER_OR_HARDWARE`: bolt, nut, washer and anchor; preserve independent existing authority.
- `FOUNDATION`: concrete or other separately modeled support; not a connector-body selection.
- `UNCLASSIFIED`: rejected for substitution until explicitly classified.

Determine roles from trusted canonical assembly/registry data, not caller-supplied labels. A caller may identify a known physical component, but cannot relabel a column as CONNECTOR_BODY to change its material.

For a direct member-to-member joint there may be no selectable body. Do not convert its members just to make the material menu universal. For a pultruded-only doubler, an alternative stainless detail would require a separately verified design route; the ordinary body selector cannot override the restriction. [S1]

## 9. Material identity is not a shape, a grade label or fastener identity

Keep these fields independent:

- component role and physical ID;
- body shape: plate, angle, tee, fabricated body or other declared form;
- connector material family: FRP or SS316 target;
- grade identity: 316, 316L or explicitly dual-certified, without treating them as interchangeable strength records;
- stock specification and edition;
- fabrication route: plate-cut, formed/bent, hot-finished shape, extruded shape, conventional welded built-up, laser-welded or other source-defined route;
- material condition, thickness/size range and manufacturing data;
- exact property/source record and design-method version;
- physical frame and geometry.

A bent angle and a welded tee do not become a verified hot-rolled connector by sharing dimensions. No automatic cold-work strength credit, weld-strength credit, bend-radius approval or catalog dimension is inferred.

For FRP retain component-specific LW/CW/TT exactly. For stainless preserve body/local geometric axes, but do not relabel them as pultrusion/fiber directions or route its strength through FRP directional properties.

Missing properties remain unavailable, not zero. Invalid types, Boolean-as-number, nonfinite quantities, impossible ranges, contradictory records and ambiguous overlapping property domains fail validation.

## 10. Assignment semantics and shared components

Represent assignments by canonical physical connector ID, not array index or viewer alias. A shared tee or plate serving multiple connected members has one material identity. Conflicting alias assignments reject the entire proposed assignment transaction.

The foundation may represent independent FRP/SS316 choices for physically distinct connectors. It must report mixed-material response/qualification requirements rather than borrowing a symmetric equal-material solution. A monolithic connector cannot have one leg FRP and the other stainless. Built-up subcomponents need explicit physical IDs, joining/fabrication and source scope before independent material assignment is meaningful.

A future apply-to-all-connectors command must enumerate eligible bodies, exclude primary members/fasteners/restricted reinforcement, validate all changes first, and report which bodies were not changed. No partial silent conversion. CME-1 tests this planning behavior without adding a mutation endpoint.

Default and legacy behavior remains FRP connector bodies. Explicit stainless requests must never be silently ignored or converted to FRP by the new planning/dispatch path.

## 11. Source and design-basis contracts

A source descriptor shall identify content and applicability separately. Include sufficient fields for source ID/revision, document edition and clause/table, approval scope, content digest, stock/grade/fabrication/condition, thickness or size, property-name/value/units basis, temperature/environment domain where relevant, and method/assembly restrictions.

A file hash demonstrates identity, not engineering qualification. A publisher listing proves publication metadata, not a mechanical property. Distinguish at least:

- metadata identified;
- normative content verified;
- material property record verified;
- numerical method implemented and verified;
- family adapter verified;
- assembly response applicable;
- whole required-check coverage complete.

Reuse existing source-trust boundaries. New client request fields cannot mint an approved source, assign their own trust level or cause arbitrary file/network lookup. Exact typed source text, an unreviewed MTR, test fixture or source URL alone is not sufficient to execute production resistance.

ASTM source values may be independently tabulated in the two unit systems. Store original table-unit provenance and convert the selected physical value using existing helpers for display; never swap to a different printed table number merely because the display changes. Do not introduce a new global conversion precision.

For this phase the stainless normative rules/property gaps are explicit CME-2 deliverables. Do not fill them with web snippets, material-vendor typical values, inferred F593 strengths or synthetic numbers.

## 12. Shared provider protocol and native FRP adapter

Use one extensible protocol with inputs conceptually covering component role/material record, actual geometry/frame, resolved demand with provenance, method/version and source applicability. Keep framework/network/filesystem access out of pure domain/calculation functions.

Provider selection must use declared capability for material, body/fabrication and limit state. Do not select a provider merely from the label SS316, nor presume that a provider registered for plate tension handles angle prying or a welded tee.

Implement native FRP adapters only by calling the accepted existing provider(s) with the same native inputs. Do not duplicate equations, retabulate strengths or copy golden outputs into production. Test through actual native calls for every available provider class and every discovered family/mode's reference cases. Preserve native values, status precedence, warnings, qualified-source boundaries and legacy fingerprints.

SS316 has a representable descriptor but no implemented numerical provider under this order. Dispatch must return structured `PROVIDER_NOT_IMPLEMENTED` or the exact existing equivalent, null capacity and null utilization. Do not return a numerical zero capacity or ordinary PASS. Do not invoke the FRP connector-body provider as fallback.

A fake provider is allowed only through test injection to prove routing and stale-source handling. It must not be importable from the runtime registry or reachable through a production API. No synthetic stainless qualification in the application.

## 13. Demand and interface revalidation plan

For an already-resolved wrench, preserve the native proper-frame and reference transform:

`F_O = Q F_R`

`M_O = Q M_R + (r_R - r_O) cross F_O`.

Q has the declared local basis as columns in global coordinates and determinant +1. Equal-and-opposite reaction is at the same reference; it is not another applied load. A material choice alone cannot alter this algebra for fixed authoritative geometry/input demand. [S7]

For material-dependent response, require revalidation before any branch demand is reused. Source domain must cover the actual component material set, manufacturing route, geometry, attachment, boundary conditions, load signs and method version. An FRP source is invalid for stainless unless explicitly applicable. Invalidation preserves independently known external actions but removes unusable derived sharing/contact/prying results.

Native FRP/steel versus FRP/FRP row distributions remain separate, with original row order and applicability. This foundation does not authorize classifying every arbitrary stainless/FRP arrangement as the accepted FRP_STEEL method. Multi-plane common bolts, nonuniform forces and mixed-material branches need their own applicable mapping. [S1, S8]

FRP members continue to need actual local bearing/net-section/shear-out/block-shear/pull-through checks where applicable. Changing the connector material cannot cancel those checks or allow FRP factors to be applied to stainless resistance. A shared physical fastener is checked once under its applicable method with all required interface effects, not multiplied by the number of displayed planes.

## 14. Completeness and status semantics

Keep geometry, response availability, resistance availability, source/applicability and numerical comparison distinct. A descriptor may be representable without a verified design method.

Do not blanket-delete qualification warnings when selecting stainless. A blocker whose sole reason is an FRP connector body may eventually be superseded by an applicable stainless route, but unresolved FRP member response, one-sided framing, joint compatibility, contact, bolt tension, moment classification and anchor/concrete requirements remain independently evaluated.

For an explicit design result, an evaluated applicable failure remains visible even with missing required sources. A preview/planning operation executes no resistance and cannot create a new design PASS or FAIL. Unknown demand is not zero demand; not evaluated is not not applicable.

Connection-level ordinary PASS requires every demanded applicable scope to be covered. A future stainless body check passing does not certify the whole FRP connection or full supporting structure. [S1]

## 15. Additive API scope

Implement two narrowly bounded interfaces using the repository's actual API prefix, validation/error conventions and versioning:

- read-only connector-material capabilities, returning declared roles, inventory coverage and phase readiness;
- stateless connector-material assignment planning, consuming a known product/mode and physical component references plus proposed assignments and returning validation, selected targets, source invalidations and required future method coverage.

Suggested suffixes are `/connector-materials/capabilities` and `/connector-materials/plan`. Resolve exact paths in consolidated preflight; do not duplicate existing equivalent routes. Updating route inventory tests for these two authorized routes is expressly allowed.

The planning request shall include the product's existing native geometry/preview input (or an already-supported server-verified snapshot reference). Resolve the assembly through its native canonical preview builder; never trust client-supplied component roles or geometry labels. Do not invent new persistence to look up a plan. The plan endpoint must validate roles against that trusted canonical assembly data. It does not persist assignments, alter a saved design, recompute resistance, run a fake stainless result or expose private local paths/source files. Reject caller-supplied role escalation and unknown physical IDs. Reuse existing stateless request patterns; do not add authentication, persistence or new dependencies.

Leave existing family preview/design routes and their accepted FRP request/response contracts unchanged. Do not retrofit all production workspaces in this phase. Native adapters are exercised through application integration tests; real family conversion is a later controlled phase.

## 16. Read-only user diagnostic

Add a small read-only `Connector Material Readiness` panel/page using the existing diagnostic convention. It must distinguish:

- structural members: FRP only;
- current FRP support: native, existing scope;
- connector-body SS316 target: foundation registered, numerical rollout pending;
- per-family migration coverage and restricted/no-connector cases.

Do not add a third Shear/Moment category, replace the accepted Units/Shape/Layout controls, reset user geometry or show an operative stainless design choice before its family route is verified. No decorative recoloring that could be mistaken for a calculated stainless connector.

The future material selector is specified now as an independent connector-body choice, with stock/source details separately shown and fastener material unaffected. It becomes active only after the relevant method and family integration are accepted. Do not activate it under CME-1.

## 17. Fingerprints and backward compatibility

Do not change existing core/FRP fingerprints to add a material field. Keep legacy numeric/result identity exact for the same legacy request. Material-neutral core fingerprints retain their native exclusion of material/provider metadata.

Create a separate namespaced material-plan fingerprint binding actual material assignments, role/physical identity, source revision, fabrication, applicable method and response domain. Exclude display units, camera, timestamps, random IDs and list order after canonicalization. Keep source-native table units as engineering provenance, distinct from display units.

Missing optional future material fields in a legacy request must follow its native FRP path exactly. Explicit invalid data in the new plan request must reject, not downgrade silently. Document all new versioned envelope fields separately so historical snapshots are not rewritten.

## 18. Acceptance fixtures and independent proof

The companion defines **80 acceptance requirements and 24 reference fixtures**:

- F01-F12: role, assignment, alias, dispatch and source-invalidation contracts;
- F13-F18: six exact resolved-wrench transport cases with opposite reactions;
- F19-F20: ideal parallel-spring counterexamples showing why equilibrium alone does not fix load sharing;
- F21-F24: four existing native material-pair row-distribution identities.

F19-F20 are educational architecture tests, not an approved connection-response solver. Do not install parallel-spring force fractions as default column-base mechanics. None of these fixtures is a stainless resistance benchmark.

Use exact rational fixture comparisons over the stated integer/finite inputs. For inherited methods use their actual native comparisons without a new precision adapter. Preserve all existing benchmark files. No production function may read expected answers from the companion.

Each acceptance requirement needs a mapped executable regression/integration test or direct controlled evidence. Do not claim 80 requirements passed because a document lists them. Test guards at domain and new API level, FRP native equivalence, no-provider fallback, source signature invalidation and new-family inventory failure.

## 19. Complete phase roadmap and migration ledger

Create a current registry-backed migration ledger, with every existing product/mode included. The program commitment is all applicable existing and future connector bodies, not one chosen demonstration family.

The planned rollout is:

**CME-1 (this order):** common foundation, role guards, full inventory, source/method gaps and FRP compatibility.

**CME-2 (separate controlled engineering package):** verify the stainless code/property basis and implement shared numerical limit-state modules, progressing from applicable flat-plate checks to angle/body response and fabricated/tee cases. Build source-derived equations and independently verified numerical benchmarks before activation. Include mixed FRP/stainless interface demand and response rules; do not stop at connector strength alone.

**CME-3 (separate family-integration orders):** migrate all applicable existing shear and moment families in provider-based batches, enable the independent connector selector, and reverify FRP and stainless paths per body/load path. Incorporate the same registration/coverage gate in every future family. A body form not numerically covered remains explicitly pending, never silently declared migrated.

Prioritize common plate/angle providers for reuse, but do not claim a single universal angle formula checks all clip angles, moment supports and bases. Tees/fabricated parts need fabrication/joining coverage. Keep reinforcing-member exceptions in a separate qualified-alternative ledger.

The CME-2 handoff must identify exact missing sources, candidate method chapters, material stock/grade/condition/property domains, FRP interface rules, reference cases and family adapters. Full stainless scope is not accepted merely because CME-1 succeeds.

## 20. Preflight and bounded implementation authority

Before mutation run one consolidated review of baseline/tags, current product/mode registries, source copies, native interfaces, old scope guards, route inventories, dependencies, audit health and all safely discoverable incompatibilities.

Missing stainless strength sources are expected future-scope gaps, not CME-1 implementation blockers. A missing verified current-baseline authority or a genuine conflict in FRP member role/legacy semantics is a blocker. Report all safely discoverable blockers together; do not serially ask for routine filenames.

Within this task, automatically resolve module/path naming, additive route inventory updates, immutable-contract plumbing, native adapter placement and same-pattern historical-test maintenance. Record the concrete reviewed path allowlist before staging. A source-specific steel method ambiguity stays in the CME-2 ledger; do not resolve it by making up a new numerical rule.

## 21. Successor-safe governance and protected scope

Preserve all 13 historical tags/manifests and their exact historical source identities. Historical tests must anchor to their historical objects or existing controlled offline snapshots, not demand that today's mutable aggregate source/package/registry file retain an old whole-file hash forever.

Repository-wide tests-only maintenance of the already-known historical-vs-current pattern is authorized in one batch. Preserve original historical constants, evidence and tamper detection; preserve engineering assertions. Do not skip/xfail/delete safeguards or replace old hashes with current values. Prove both allowed current successor changes and forbidden historical-content changes.

Current change-scope checks must use this task's reviewed explicit paths, not turn a past task's allowlist into a perpetual prohibition on future development. Do not add another future-hostile whole-current-tree hash assertion.

New core/contracts/adapters, the two additive interfaces, read-only diagnostic, their tests and narrow governance are authorized. Numerical steel equations, new production family material switching, FRP mechanics, geometry defaults, factors, native units, qualification meaning, dependencies, lockfiles and workflows are not authorized by the normal scope.

## 22. Archive and documentation rules

Archive both approved CME-1 files byte-for-byte under repository governance/engineering-fixture paths using normal conventions. This archiving is authorized even when the exact source copies currently exist only in Downloads. Verify source bytes, staged Git blob bytes and eventual committed blob bytes against the approved digests. Do not normalize the controlled files to satisfy whitespace tooling.

These new files contain no intentional trailing hard-break spaces and should pass whitespace checks. No new whitespace exception is granted. Do not copy PDFs, images, logs, caches, environments or credentials into Git.

Create/update only necessary current records: architecture decision, source ledger, all-family material inventory/capability registry, migration plan, QA test mapping and handoff. Append to historical source-register prefixes according to their conventions. Avoid recursive self-hashes; keep artifact hashes in a separate register that is not included in its own digest.

Record current status truthfully as CME-1 foundation implemented/pending acceptance, not all stainless families designed or the whole product certified.

## 23. Network, environment and interruption handling

Owner authorizes ordinary dependency installation/verification through the existing approved package sources, full and runtime npm audits against `registry.npmjs.org`, read-only remote/tag/CI access, local server/browser use, and the normal project push after all stated gates.

Do not publish packages, modify credentials, disable Windows security, run force audit fixes or upload source/licensed documents to unrelated services. Equivalent `python -m mypy` using the same configured package and an existing trusted WSL/Linux verifier are permitted when a Windows executable wrapper is blocked. Use Git-aware blob/EOL checks.

For external audit endpoint/network failures, retain evidence and allow up to two bounded retries; do not label an unavailable scan zero findings. A newly disclosed vulnerability is not an endpoint error. No automatic dependency upgrade is included in CME-1; consolidate genuine out-of-scope remediation needs once.

On interruption, first inspect actual refs/index/worktree and resume the existing checkpoints. A model-capacity event is not authorization to restart, amend or discard code. Do not claim background continuation after execution stops.

## 24. Local and browser verification

Run full backend/frontend suites with current configured 100% coverage, Ruff, strict mypy, ESLint, strict TypeScript, production build, pip consistency, full/runtime npm audits, JSON and whitespace validation. Baseline scale is 5,045 backend / 848 frontend; actual totals may rise. Do not remove tests to preserve a count.

Run all accepted engineering regression suites and all historical freeze audits, not just CME tests. Verify legacy FRP behavior for every discovered product/mode, using existing real fixtures including qualified source-present cases where they exist. Compare actual native results, not only mocked delegates or serialized fixture echoes.

Automatically start or safely reuse approved local servers, verify the exact local URL, and open the application for browser smoke tests. Cover each existing selectable workspace sufficiently to prove it still mounts and previews normally, a representative explicit FRP design per provider path, the new read-only diagnostic and role-reject/planning responses. Check console/network errors and confirm preview/capability/planning does not run design automatically. Do not kill another stage's servers or obsolete worktrees. Report actual ports/PIDs and leave the verified application running.

## 25. Commit and object-isolated gate

Use explicit-path staging only. Review complete staged diff and confirm prohibited changes are zero. Put the new foundation and authorized same-pattern tests/governance in one normal implementation commit:

`feat: establish connector material foundation for FRP and 316SS`

Normal expected count: **125**. Do not amend count-124 or any published commit. Do not tag. Do not add a standalone commit merely to archive the two approved files.

After commit, verify the exact candidate in a fresh depth-one, no-tags, no-alternates/no-shared-object clone. Use a transport/clone method that actually enforces these conditions and report the checks. Run complete QA including CME/native/freeze regressions.

This clone cannot prove historical tag identities it does not possess. Verify those in the full-history checkout and use the existing committed immutable snapshot/manifest path for offline isolated tests. Report provenance; do not fetch hidden historical objects during isolated QA, skip tests or claim historical bytes were read when only a manifest assertion was available.

If a postcommit defect is demonstrably within the new CME-1 code/tests and not protected engineering, one amendment of the still-unpublished candidate is pre-authorized after diagnosis and local tests. Re-run all final local/object-isolated gates on the amended hash. A second amendment or protected-engineering change requires consolidated owner review. Never amend a pushed commit.

## 26. Publication and bounded Windows timing rule

After all local/browser/object-isolated gates pass, normal non-force push of the exact verified candidate to the named remote main is authorized. Verify execution-checkout HEAD, origin/main and actual remote main match. Push no tags.

Then obtain direct hosted results for Backend Ubuntu, Backend Windows, Frontend Ubuntu and Frontend Windows on that same hash. CI is after push, never an impossible pre-push prerequisite. Authentication unavailability is reported as unverified rather than inferred green.

For a Windows-only default 5-second timeout, with no assertion/request/runtime/product defect, retry the failed Windows job once. If repeated and diagnosed as test workload timing, a per-test limit up to 15,000 ms is permitted for up to three distinct test bodies in this cycle; a parameterized body counts once. Require 10 consecutive Windows passes of each complete body without sleeps, skipped assertions or global timeout changes. Do not increase a test already at 15 seconds.

A needed postpush timing change is a separate tests-only successor, full local/object-isolated verification, normal push and fresh four-job CI. Report actual increased count; no new approval merely because that authorized count differs from 125. A different real defect or out-of-scope failure requires one consolidated report.

## 27. Completion and next approval gate

Provide one evidence ledger with:

1. Starting and final refs/count/subject; all thirteen tag object/target checks.
2. Full actual product/mode inventory and every component-role disposition.
3. Implemented contracts, role enforcement and canonical-ID spoof/conflict tests.
4. Native FRP adapter equivalence and exact legacy fingerprint proof.
5. SS316 representable-but-not-enabled behavior and no FRP fallback.
6. Material-dependent response invalidation and remaining qualification scopes.
7. Source records actually accessible/reviewed versus metadata-only or missing.
8. All 80 acceptance requirements mapped to tests/evidence and all 24 fixtures checked.
9. Additive API/diagnostic paths and browser evidence; existing workspace regression.
10. Per-body/provider/family migration ledger and concrete CME-2 source/rule prerequisites.
11. Exact changed paths, archived order/matrix digests, protected-scope counts.
12. Local and isolated tests/coverage/static/build/audit results and actual evidence limitations.
13. Commit/amendment or timing-successor lineage if any; direct hosted run/attempt/four results.
14. Clean active state, untouched obsolete drafts and running local application URL/PIDs.
15. Explicit confirmation: primary members FRP-only; no production stainless resistance enabled; no family material selector activation; no new freeze tag or later-phase implementation.

Stop after completion. The next separately controlled engineering package implements the stainless numerical/provider basis and then family activation. Do not claim the complete 316SS expansion is finished at CME-1 acceptance.

**END OF CME-1 CONNECTOR MATERIAL FOUNDATION ORDER RC1 - DO NOT PROCEED IF THIS LINE IS MISSING**
