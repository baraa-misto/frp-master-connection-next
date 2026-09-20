# FRP Master Connection Project Baseline

## Document control

| Field | Value |
|---|---|
| Baseline ID | `FMC-BL-001` |
| Stage | 0.1 — Repository and controlled-document foundation |
| Status | Approved product baseline; implementation not started |
| Baseline date | 2026-08-03 |

## Purpose and product boundary

FRP Master Connection is an original web-based engineering calculation, visualization, documentation, and reporting product for pultruded FRP structural connections. Its long-term delivery model is an authenticated, paid web service reached through the Masters Engineering Solutions website and Client Login.

FRP Master Connection is not a structural-analysis or frame finite-element program, a replacement for SAP2000, a nonlinear connection FEA program, a general serviceability program, or a decorative stress-contour program. It may not invent load paths, equations, capacities, or code requirements. Stage 0.1 implements no engineering equations, capacities, resistance factors, numerical code criteria, utilization calculations, or engineering PASS/FAIL logic. The repository is not yet a design tool, and no output may be used as an engineering design result.

The product is developed in a repository separate from FRP Master Pro. No code, data, or proprietary implementation is copied from FRP Master Pro, the MES website, other sibling repositories, proprietary software, or RAM Connection.

## Approved foundational requirements

The following decision text is controlled by the corresponding stable identifier in the Decision Register.

1. **APR-001.** Manual force entry is the primary force workflow.
2. **APR-002.** Forces are entered per member and per load combination.
3. **APR-003.** Positive sign conventions and actual signed-force directions are shown graphically.
4. **APR-004.** Shear and Moment are the two main design categories.
5. **APR-005.** Moment Connections include both moment and shear analysis and design.
6. **APR-006.** Non-moment-resisting brace connections may be included under Shear Connections.
7. **APR-007.** The central data object is a complete joint assembly.
8. **APR-008.** A joint may include multiple members.
9. **APR-009.** Members may approach from different directions and inclinations.
10. **APR-010.** Direct member-to-member bolting is a first-class interface method.
11. **APR-011.** No artificial connector is created when members are physically bolted directly together.
12. **APR-012.** T-sections are first-class connector components.
13. **APR-013.** One T-section may connect multiple braces and a beam at the same joint.
14. **APR-014.** A joint may contain direct and connector-assisted interfaces simultaneously.
15. **APR-015.** Shared connectors receive combined-demand checks.
16. **APR-016.** Shared supporting-member regions receive combined checks where applicable.
17. **APR-017.** Doublers are first-class engineering components.
18. **APR-018.** Bolt stacks and penetrated layers are explicitly modeled.
19. **APR-019.** Joint equilibrium is calculated or verified.
20. **APR-020.** The software provides synchronized 3D and dimensioned 2D views.
21. **APR-021.** Complex joints may require interface-normal and section views.
22. **APR-022.** Geometry support and calculation support are separate statuses.
23. **APR-023.** Unsupported or unqualified calculations fail closed.
24. **APR-024.** The initial product does not depend on force import.
25. **APR-025.** Automatic optimization comes only after the checking engine is validated.
26. **APR-026.** FRP Master Connection remains a separate repository from FRP Master Pro.
27. **APR-027.** The calculation engine must be traceable, deterministic, edition-aware, and testable.
28. **APR-028.** Calculation, visualization, dimensioning, and reporting must use one canonical engineering model.
29. **APR-029.** FRP Master Connection’s final delivery model is an authenticated, paid web service.
30. **APR-030.** Users will ultimately access the software through the Masters Engineering Solutions website and Client Login.
31. **APR-031.** Authentication, authorization, entitlement, and billing may be implemented later, but the initial architecture must remain SaaS-ready.
32. **APR-032.** Saved projects must eventually be associated with an authenticated owner and, where applicable, an organization.
33. **APR-033.** Project and report access must be enforced server-side, not only through frontend controls.
34. **APR-034.** The commercial model is not yet frozen, so product access must use a general entitlement model rather than a hard-coded subscription type.
35. **APR-035.** The engineering calculation engine must remain independent from selected authentication and payment providers.
36. **APR-036.** The public MES website, authenticated software portal, and engineering services should have separable deployment and security boundaries.
37. **APR-037.** The system should be capable of supporting several FRP Master products through one future account and entitlement framework.
38. **APR-038.** Early local development is permitted, but production architecture must not assume a single anonymous user or local-only project storage.

## Force convention baseline

Manually entered member-end forces represent actions applied by the member to the joint assembly. Each action belongs to a connected member and load combination and has an explicit reference point and coordinate frame. Entered actions are initially treated as final factored design actions; the application must not silently apply additional load factors. Positive sign-convention graphics and applied signed-force graphics are distinct display modes. Unsupported components may not be ignored, and eccentricity between an action reference point and its interface must be retained. Exact axes, reaction signs, allowed reference points, and treatment of non-factored combinations remain pending engineering decisions.

## Product-selection baseline

The first product-selection level contains exactly these two categories:

- **Shear Connections**
- **Moment Connections**

A Moment Connection is a joint containing at least one intentionally moment-resisting interface and includes both moment and shear analysis and design. A non-moment-resisting brace connection may be classified under Shear Connections. Combined moment and shear demands are not independent when they share a component or FRP region.

## Canonical model and fail-closed controls

The central engineering object is `JointAssembly`. Direct bolted interfaces, T-section connectors, doublers, bolt groups, bolt stacks, load paths, and shared regions are first-class concepts. The same canonical engineering values drive calculation, 3D, 2D, dimensions, and reports; rendered geometry is never a source of structural resistance.

Geometry-supported does not mean calculation-supported. Placeholder calculations may never return `PASS` or `FAIL`. Intended controlled result states are `PASS`, `FAIL`, `INVALID GEOMETRY`, `NOT APPLICABLE`, `NOT COVERED BY SELECTED CODE`, `ENGINEERING REVIEW REQUIRED`, `CALCULATION NOT SUPPORTED`, `INCOMPLETE INPUT`, and `STALE RESULTS`. Warnings are supplemental and cannot substitute for a required unsupported or incomplete state. Engineering-input changes make prior results stale. Summary and Detailed reports must ultimately derive from the same immutable result data.

## Delivery, validation, and change control

Manual entry remains the initial force workflow; SAP2000 force import is outside the initial MVP. Automatic connection selection and optimization are deferred until the checking engine is validated. Each calculation slice requires source mapping, an applicability definition, independent verification, and qualified engineering approval before implementation or commercial validation.

Authentication, authorization, entitlement, billing, and final MES website integration are not implemented in Stage 0.1. The architecture must nevertheless preserve ownership and organization association, server-side project isolation, general entitlements, separable security boundaries, and calculation-engine independence from authentication and payment providers. `PRV-012` provisionally locates calculation authority server-side, and `PRV-017` provisionally recommends replaceable ports/adapters; neither implementation choice is approved by this baseline.

Approved decisions in this baseline are not reopened without a genuine engineering, safety, security, or architectural conflict. Any such conflict must be recorded in the Decision Register with evidence, impact, approval authority, and a superseding or rejected decision; convenience or implementation preference alone is insufficient.

## Stage 2.3 implemented workspace boundary

The first interactive workspace is limited to the verified single-bolt/single-row
Shear calculation slice and remains session-only. Canonical backend geometry, frames,
material axes, bolt/hole paths, reference points, action directions, calculation
results, statuses, versions, and fingerprints are authoritative. The Three.js browser
view is presentation only. Explicit resolved one-bolt demand is executable; a
member-end action without an approved distribution method remains fail-closed. The
workflow does not establish a whole-joint J1 PASS or a commercially validated design.

Moment workflow, project persistence, reports, multirow equations, automatic demand
distribution, block shear, generated prying, ICE production qualification, and locked
F593 `Fnt` sourcing remain outside the implemented baseline.

## Stage 2.3R2 controlled presentation-geometry boundary

For the current verified J1 workspace template, the backend is the sole authority for
brace angle and member placement. The brace-to-column angle is acute and
sign-independent, defaults to 45 degrees, remains in the current vertical plane, and
has plan angle fixed at 0 degrees. The W column remains vertical and continuous
through a fixed connection station, with editable positive local view extents above
and below; brace segment length is independently editable and positive. These are
controlled geometry/presentation inputs, not new resistance, distribution, or
whole-connection methods.

The default longer column must preserve the selected connection, bolt/path/layers,
loaded-end mapping, verified Q12 values, governing W-flange result, and Section 2.3.2
qualification. Browser rendering may show only exact-known bolt/washer geometry and
must retain stable internal IDs behind friendly labels. Cross-platform derived-float
checks use the approved mathematical tolerance; production canonical geometry is not
clamped.
