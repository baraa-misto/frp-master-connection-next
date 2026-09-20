# FRP Master Connection Product Charter

## Mission

FRP Master Connection will provide a traceable, deterministic, edition-aware environment for checking, visualizing, documenting, and reporting pultruded FRP structural connections. It is an original engineering product built around complete joint assemblies and a single canonical engineering model.

Stage 0.1 establishes repository and document controls only. It contains no validated calculation engine and is not an engineering design tool.

## Intended users

- Qualified structural engineers designing or reviewing pultruded FRP connections.
- Engineering designers and detailers working under appropriate engineering supervision.
- Reviewers, approvers, and project stakeholders who need traceable inputs, applicability, results, drawings, and reports.
- Future MES account and organization administrators who manage access without influencing engineering results.

The product does not replace professional judgment, source verification, independent review, or the engineer’s responsibility for the design.

## General workflow

1. Create or open an owned engineering project and its joint assembly.
2. Select exactly one top-level category: **Shear Connections** or **Moment Connections**.
3. Define members, directions, interfaces, connecting and reinforcement components, bolt groups, and bolt stacks.
4. Enter final factored member-end actions manually for each connected member and load combination, with an explicit coordinate frame and reference point.
5. Review positive sign conventions separately from applied signed-force directions.
6. Confirm geometry support, calculation support, source applicability, material qualification, and complete input.
7. Request authoritative checks only for approved capabilities; unsupported or unqualified conditions fail closed. `PRV-012` provisionally locates those calculations server-side.
8. Review synchronized 3D, dimensioned 2D, interface/section views, joint equilibrium, load paths, shared-component demand, and structured results.
9. After validation gates exist, create Summary or Detailed reports from the same immutable calculation result data.

The initial product does not depend on force import. SAP2000 import, automatic connection selection, and automatic optimization are deferred.

## Product exclusions

FRP Master Connection is not:

- a structural-analysis or frame finite-element program;
- a replacement for SAP2000;
- a nonlinear connection FEA program;
- a general serviceability program;
- a decorative stress-contour program; or
- a mechanism for inventing load paths, equations, capacities, or code requirements.

It does not infer missing engineering decisions, silently factor entered actions, treat geometry support as calculation approval, or convert an incomplete or unsupported check into `PASS` or `FAIL`.

## Original-product and source-use policy

The product must be designed and implemented independently. No code, data model, geometry implementation, proprietary behavior, or protected source content is copied from FRP Master Pro, RAM Connection, the MES website, another sibling repository, or another proprietary installation.

Licensed standards are controlled sources, not repository content. ASCE/SEI 74-23 is registered bibliographically; its equations, tables, figures, commentary, and substantial text are not reproduced. Engineering mappings require verified controlled access, traceable citations, applicability review, independent verification, and approval.

## Manual-force-first principle

Manual member-end action entry is the primary workflow. An action is applied by a member to the joint assembly and is tied to that member, a load combination, an explicit coordinate frame, and an explicit reference point. Actions are initially assumed to be final factored design actions. Sign-convention and applied-action displays must make direction explicit, and no additional load factors may be applied silently.

## Commercial objective

The intended product is an authenticated, paid web service accessed through the Masters Engineering Solutions website and Client Login. The commercial model and providers are not selected. Architecture must support authenticated ownership, optional organizations, general entitlements, server-side isolation and authorization, auditability, and several future FRP Master products without coupling the calculation core to authentication, billing, payment, email, or hosting providers.

## Validation-first principles

- No calculation family is commercially validated before source mapping, applicability definition, independent verification, and qualified engineering approval.
- The calculation engine must be deterministic, traceable, edition-aware, reproducible, and testable. Pure calculation functions are a provisional architecture recommendation under `PRV-011`, not an approved requirement.
- Geometry, calculation, visualization, dimensioning, persistence, and reporting derive from one canonical engineering model while remaining separate representations.
- Rendering meshes never determine resistance, and stress contours are not shown without validated stress analysis.
- Shared components and supporting regions receive combined-demand checks where applicable; interface-only checks do not complete a joint review.
- Unsupported, incomplete, stale, unqualified, or out-of-scope conditions use explicit fail-closed states.
- Engineering-input changes stale prior results; calculation and report snapshots are immutable.
- Optimization begins only after the checking engine and relevant calculation families are validated.
