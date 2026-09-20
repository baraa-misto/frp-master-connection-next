# Project Ownership and Entitlement Model

| Control item | Value |
|---|---|
| Baseline | FMC-BL-001 |
| Stage | 0.1 - conceptual model only |
| Status | Draft / not frozen |
| Authentication, entitlement, billing, and persistence | Not implemented / providers not selected |

## Purpose

This document defines the provider-neutral concepts needed to associate saved projects and reports with authenticated owners and, where applicable, organizations; authorize operations; and grant commercial product capabilities. It deliberately does not select an identity provider, payment/subscription provider, billing model, plan shape, organization-administration model, expired-access policy, or database design.

Project/report access and product entitlement are enforced server-side. Frontend state, routes, hidden buttons, client-supplied owner IDs, and knowledge of a resource identifier are not authorization.

## Core concepts

| Concept | Meaning | Security rule |
|---|---|---|
| Account ID | Stable internal identity for an authenticated person/account, mapped from trusted provider identity by the server. | Derived from trusted server context; a client-supplied account ID cannot impersonate or authorize. |
| Organization ID | Optional stable internal identity for a customer organization/team. | Use is optional. Server verifies membership and organization scope for every organization operation. |
| User role | Role/permissions an account holds in a specific context, such as its relationship to a project or organization. | Scoped, explicit, and deny-by-default; exact role catalog is pending. |
| Organization role | Role assigned through an account-to-organization membership. | Does not automatically grant every product, project, billing, or administrative capability. |
| Product ID | Stable provider-neutral identifier for an FRP Master product. | Entitlements target internal product IDs, not payment-provider price/subscription IDs. The framework must support several FRP Master products. |
| Capability right | Fine-grained permitted product action, such as project creation, calculation, report generation, or read-only access. | Checked server-side per operation; possession of one right does not imply another. |
| Entitlement | Time/state-bounded grant of product/capability rights to an account or organization, optionally with limits. | General model; not hard-coded to a subscription type or provider. |
| ProjectRecord | **Provisional — PRV-014:** ownership/lifecycle/security envelope around a versioned `EngineeringProjectDocument` and snapshot references. | Always loaded through trusted owner/organization scope. Ownership fields are not editable as ordinary engineering input. |
| EngineeringProjectDocument | **Provisional — PRV-014:** versioned canonical calculation input separated from the ownership envelope. | Contains no authorization grant. It may be portable without transferring ownership. |
| CalculationSnapshot | Immutable engineering attempt/result record associated with a project. | Access follows project/snapshot authorization; engineering status does not grant access. |
| ReportSnapshot | Immutable presentation derived from a calculation snapshot. | Separately authorized for create/read/export while remaining associated with the owning project scope. |

## Ownership model

Every saved `ProjectRecord` is associated with an authenticated owning scope:

- an individual/account-owned project has an owning Account ID; and
- an organization-associated project has an Organization ID and records the accountable creating/acting Account ID as appropriate.

Whether an organization project is legally/operationally owned only by the organization, jointly associated with its creator, or transferable is a **Pending Architecture Decision** requiring business and security approval. The persistence model must not infer ownership from the last editor, email domain, browser session, report author, or a client-controlled field.

Under **Provisional PRV-014**, `ProjectRecord` ownership/lifecycle metadata is separate from the `EngineeringProjectDocument`. Account IDs, organization IDs, role assignments, entitlements, billing state, and audit metadata are excluded from the engineering calculation fingerprint. Their exclusion does not permit access without authorization.

Ownership changes, organization reassignment, sharing, duplication, archival, recovery, and deletion require dedicated authorized operations and audit records. Exact policies are future decisions; ordinary project update endpoints must not transfer ownership.

## Role model

Roles describe what an identity may do within a resource/organization scope; entitlements describe which product capabilities the commercial/account framework makes available. Both may be required.

The conceptual model supports:

- account-level rights for individually owned resources;
- organization membership with one or more scoped organization roles;
- project-specific roles or grants where future sharing requires them;
- separation of organization administration, billing administration, project work, and read-only review; and
- narrowly scoped administrative support actions with explicit audit and no implicit engineering approval.

Exact role names, inheritance, custom roles, invitation workflow, guest access, administrator capabilities, and support impersonation are **Future Decisions**. Until a role/action mapping is approved, an unknown or ambiguous role grants nothing.

Organization membership alone does not establish a product entitlement, and an organization entitlement alone does not establish access to every organization project. A project authorization requires the applicable resource relationship/role as well as the required product capability.

## Product and capability model

A general entitlement targets a stable Product ID and one or more capability rights. This permits a future account/organization framework to support FRP Master Connection and additional FRP Master products without coupling engineering code to billing products.

The minimum conceptual capability families are:

| Capability family | Example operation boundary | Non-implication rule |
|---|---|---|
| Project creation | Create a new owned project within an authorized account/organization scope. | Does not automatically allow calculation or reporting. |
| Project read-only | List/open permitted projects and view permitted historical calculation/report snapshots without editing or recalculating. | Does not allow edit, new calculation, new report, ownership change, or export unless separately granted. |
| Project editing | Modify canonical engineering inputs and save a new project revision. | Makes prior results stale; does not authorize calculation. |
| Calculation | Request an authoritative calculation and create an immutable calculation snapshot when the engineering capability is supported. **Provisional PRV-012** locates that authority server-side. | Entitlement cannot turn unsupported engineering into `PASS`/`FAIL`. |
| Reporting | Create a Summary/Detailed report snapshot from authorized immutable result data. | Does not authorize recalculation or change result status. |
| Report read/export | View or export an authorized report artifact. | Does not grant access to unrelated projects, source data, or reports. |
| Administration | Manage approved organization/project/product settings. | Exact scope is pending and must be narrowly defined/audited. |

These are conceptual rights, not frozen API names. A product entitlement may grant any approved subset. The commercial model must not be encoded as a single `isSubscribed` or `isPaid` flag.

## Entitlement record

A future entitlement record conceptually includes:

- entitlement identity and internal Product ID;
- subject scope: Account ID or Organization ID;
- capability rights;
- effective start and end dates/times;
- controlled state;
- source/provenance of the grant without making provider IDs authoritative to engineering services;
- optional usage limits and current metering reference;
- optional seat limit and seat-allocation/concurrency reference;
- administrative reason/audit reference where applicable; and
- version/revision information for deterministic policy evaluation.

Dates are evaluated server-side against a trusted time source. Missing, malformed, contradictory, or unverifiable dates do not grant access.

### Entitlement states

| State | Conceptual meaning | Access policy boundary |
|---|---|---|
| Trial | Time-bounded evaluation grant. | Trial duration and capabilities are undecided. |
| Active | Currently effective grant under its approved rights/dates/limits. | Does not override project roles or engineering support. |
| Suspended | Temporarily restricted by an authorized administrative/commercial process. | Exact read/write behavior is undecided. |
| Expired | End date or approved expiration transition has been reached. | Expired-access policy is explicitly undecided. |
| Canceled | Grant is canceled, potentially immediately or at a future effective boundary. | Cancellation timing/access behavior is undecided. |
| Administrative | Explicit non-commercial or manually administered grant/restriction with reason and audit trail. | Does not imply unrestricted administrator access; exact use is undecided. |

State alone is insufficient. The policy evaluation also considers dates, Product ID, requested capability, subject scope, limits, resource relationship/role, and administrative restrictions. Unknown states fail closed.

## Authorization decision

For every protected request, the authenticated engineering API conceptually evaluates:

1. **Trusted identity:** verified server-side Account ID/session context exists.
2. **Resource scope:** the ProjectRecord/snapshot/report resolves within an account or organization scope accessible to that identity.
3. **Role/right:** the identity's current scoped role permits the requested resource operation.
4. **Product entitlement:** an effective entitlement grants the requested Product ID and capability.
5. **State, date, and limits:** state, effective dates, usage/seat constraints, and administrative restrictions permit the request under approved policy.
6. **Resource lifecycle:** project/report status permits the operation.
7. **Engineering capability:** for calculations, the requested calculation slice is supported, applicable, versioned, verified, and engineer-approved.

Steps 1-6 are security/commercial authorization. Step 7 is an independent engineering fail-closed boundary. An engineering `PASS` never grants access; a valid entitlement never converts unsupported engineering into a result.

The server returns only data authorized for the trusted context. A user-provided Account ID, Organization ID, Project ID, report key, or capability claim selects a requested resource/action but never proves permission.

## Server-side project isolation

- All project, snapshot, and report list/lookups are scoped from trusted identity and authorized organization context.
- Object identifiers are treated as opaque locators, not bearer credentials.
- Create operations derive owner/organization scope on the server; they do not trust an arbitrary owner in a client document.
- Update and calculation operations reload current ownership, role, and entitlement instead of trusting cached frontend state.
- Database scoping is supplemented by service-level authorization and future isolation tests.
- Report/object storage access is issued or streamed only after current server authorization.
- Cross-scope requests fail without exposing protected existence, names, owners, result status, or storage metadata.
- Background jobs carry a server-issued, narrowly scoped authorization/work context; they do not accept raw client owner claims.
- Administrative access, if later permitted, is explicit, least-privileged, time/reason bounded where appropriate, and audited.

Exact database row-level security, tenant keying, caching, and job-token mechanics are **Pending Architecture Decisions**.

## Usage and seat limits

The model can carry optional usage and seat limits without requiring them for every entitlement. Possible metrics, metering windows, reset behavior, concurrent-seat semantics, seat assignment, overage behavior, reservation/release, offline behavior, and dispute correction are **Future Business/Architecture Decisions**.

Limit enforcement is server-side and concurrency-safe under the future approved design. Missing or inconsistent limit state cannot be resolved by a client assertion or assumed unlimited. The absence of a limit on a valid entitlement can mean unlimited only when the approved entitlement policy explicitly says so.

## Expired and changed access

The expired-subscription access policy remains **Undecided**. No decision is made here about whether expired, suspended, or canceled subjects may read projects, download existing reports, export data, edit, recalculate, or create new reports.

Before production, the policy must explicitly address each operation, customer data portability, legal/contractual obligations, retention, reactivation, grace periods, and organization-member effects. Until that policy is approved and configured, the system cannot infer continued access from cached UI state or past entitlement; an unresolved policy evaluation fails closed for the requested protected operation.

Historical calculation/report snapshots remain immutable regardless of entitlement transition. Immutability does not itself guarantee continued access; access follows the future approved policy.

## Billing separation

The billing model remains **Undecided**: provider, payment/subscription arrangement, monthly versus annual term, named-user versus concurrent-seat licensing, individual versus organization plans, trials, bundles, enterprise licensing, and grace/cancellation behavior are not selected.

Future provider events map through trusted server adapters to internal entitlement records. Payment/subscription identifiers and client-reported payment state are not product capabilities. The calculation engine has no dependency on billing state, provider SDKs, prices, or account identity.

## Local development boundary

**Provisional architecture:** early local development may use a server-injected `LocalDevelopmentIdentity` and local adapter-backed ProjectRecords. It must remain explicit, non-production, and outside engineering inputs/fingerprints. Production must require trusted authentication and server-side ownership, entitlement, and project isolation; it cannot assume a single anonymous owner or local-only storage.

## Fail-closed rules

- No trusted Account ID: deny protected access.
- Optional Organization ID absent: evaluate only explicitly allowed individual scope; never guess an organization.
- Organization ID present but membership/role unresolved: deny organization-scoped access.
- Unknown role, Product ID, capability, entitlement state, date interpretation, or limit outcome: grant nothing by default.
- ProjectRecord ownership missing/ambiguous: deny access and require controlled resolution.
- Frontend says visible/enabled but server policy denies: server denial prevails.
- Billing provider says paid but no valid internal entitlement exists: deny the capability pending trusted reconciliation.
- Entitlement permits calculation but engineering capability is unsupported/incomplete/not covered: return the applicable engineering non-success state; never `PASS`/`FAIL` from placeholder logic.
- Warnings cannot replace an authorization denial, entitlement denial, project-isolation failure, or required engineering status.

## Pending decisions

### Future business/security decisions

- Identity, payment, and subscription providers.
- Billing period, licensing metric, plan types, trials, bundles, enterprise terms, and expired-access policy.
- Organization administration, project transfer/sharing, roles, guests, support access, usage/seat policies, and data retention.

### Pending Architecture Decision

- Exact authorization policy representation, persistence schema, tenant isolation, caching, metering, background-job context, and audit mechanisms.
- Cloud/database/object-storage providers, deployment topology, and MES website/Client Login integration.

These choices must be approved before production. They must remain outside engineering calculation behavior; pure calculation functions remain **Provisional — PRV-011**.
