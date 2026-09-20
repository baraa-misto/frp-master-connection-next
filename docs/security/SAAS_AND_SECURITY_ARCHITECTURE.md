# SaaS and Security Architecture

| Control item | Value |
|---|---|
| Baseline | FMC-BL-001 |
| Stage | 2.2B - trusted stateless calculation route; authorization/entitlement still absent |
| Status | Draft / not frozen |
| Production authentication, authorization, entitlement, billing, and deployment | Not implemented / providers not selected |

## Purpose and security objectives

FRP Master Connection is intended to become an authenticated paid web service accessed through the Masters Engineering Solutions (MES) website and Client Login. Stage 0.1 defined boundaries that keep the engineering core deterministic and provider-independent while enabling future server-side identity, authorization, entitlement, ownership, storage, and audit controls. Stage 0.2.2 implements only the trusted identity-resolver seam, fixed local/test identity, and production fail-closed application composition. Stage 0.2.3 adds only an untrusted noncalculating frontend shell. Neither stage implements authentication, authorization policy, entitlement, billing, ownership storage, project storage, API integration, or an audit service.

The architecture must protect:

- customer engineering projects, results, reports, and ownership metadata;
- account, organization, entitlement, billing, and audit data;
- application secrets, credentials, certificates, and private keys;
- proprietary software and qualified engineering rules/data; and
- private licensed sources, including ASCE/SEI 74-23.

Security controls must fail closed. An authentication, authorization, entitlement, tenant-isolation, version/provenance, or required data-access failure does not become an engineering `PASS` or `FAIL`; the requested operation is denied or returns a controlled non-success response without disclosing protected data.

## System boundaries

| Boundary | Responsibility | Trust and access rule |
|---|---|---|
| MES public website | Public marketing, product discovery, and future entry point to Client Login/software portal. | Public/untrusted boundary. It has no direct project database, report storage, calculation engine, licensed-source, or secret access. |
| Authentication and account system | Future sign-in, session/account identity, credential recovery, and trusted identity assertions. | Provider not selected. The engineering API accepts identity only after server-side verification through a trusted integration. |
| Entitlement and billing system | Future product/capability rights, commercial state, dates, limits, and billing-provider integration. | Provider and billing model not selected. Billing facts are translated server-side into general entitlements; billing state does not enter engineering calculations. |
| FRP Master Connection frontend | Authenticated user experience, canonical-document editing, visualization, dimensioning, and request/response presentation. | Treat as an untrusted client. It may request an owner/project/capability but cannot grant access or establish engineering authority. |
| Authenticated engineering API | Security policy-enforcement point and application coordinator for projects, calculations, snapshots, reports, and audit events. | Establishes trusted server identity, authorizes every resource/action, enforces entitlement, validates inputs, scopes storage, and invokes the calculation core. |
| Pure calculation engine — **Provisional PRV-011** | Deterministic engineering-domain validation and future qualified calculations from explicit engineering inputs and versioned data. | No dependency on authentication, billing, email, MES website, or payment providers. It receives no credentials and makes no ownership decisions. |
| Project database | Under **Provisional PRV-014**, `ProjectRecord` ownership/lifecycle data, versioned engineering documents, snapshot metadata, and controlled references. | Private server-side resource. Every access is tenant/project scoped; no direct browser access. |
| Report/object storage | Future immutable report artifacts, snapshots/exports, and other controlled objects. | Private by default. Access is granted by the API using opaque server-controlled object references and current authorization; object paths supplied by clients confer no access. |
| Audit records | Security and engineering-lifecycle events needed for accountability. | Append-controlled, access-restricted, tamper-evident design objective; audit data is not a user-editable project field or calculation input. |

The public MES website, authenticated software portal/frontend, and engineering services require separable deployment and security boundaries. They may be deployed together during approved development only if their logical boundaries remain explicit. Exact production topology is a **Pending Architecture Decision**.

### Implemented Stage 0.2.3 frontend boundary

The current frontend is an untrusted display client with no backend API integration. It does not establish identity, authorize project access, enforce entitlements, enforce billing, or store ownership or security claims. It contains no account ID, owner ID, organization ID, role, capability, entitlement, payment state, authentication state, session token, credential, secret, private service URL, or database identifier.

The shell uses no cookie, `localStorage`, `sessionStorage`, or IndexedDB persistence and accepts no identity through a URL parameter or mock user. Its disabled Calculate and Generate Report controls are usability-only placeholders; they are not policy enforcement and cannot invoke a server or produce a result. No authentication provider has been selected. The backend remains the future authoritative security, product-metadata, project, and calculation boundary.

## Trust flow

1. A user reaches the future authenticated product through the MES website or portal.
2. The authentication/account system establishes an identity assertion.
3. The engineering API verifies that assertion and constructs trusted server-side identity context.
4. For each operation, the API resolves resource ownership/organization scope, role/capability authorization, entitlement dates/state/limits, and project lifecycle policy.
5. Only after authorization does the API load the permitted project data; **Provisional PRV-014** names its separated records `ProjectRecord` and `EngineeringProjectDocument`.
6. For calculation, the API validates/version-resolves the engineering document and passes calculation-only data to the pure engine. The engine returns structured results; it receives no account, billing, or secret data.
7. The API stores new immutable snapshot metadata/artifacts under server-derived ownership scope and records required audit events.
8. Responses disclose only data authorized for the current identity and capability.

Every request is reauthorized server-side. A previously rendered page, cached frontend state, guessed identifier, owner ID in a request, or prior entitlement does not establish current access.

## Identity boundary

Identity comes from trusted server context after authentication verification. Client-provided account IDs, organization IDs, owner IDs, roles, entitlement claims, or project IDs are request selectors only; they are not authorization evidence.

**Implemented provisional Stage 0.2.2 shell:** protected product routes consume a `TrustedIdentityResolver` at the API boundary. The backend injects a fixed, immutable `LocalDevelopmentIdentity` automatically only in local or test mode. It accepts neither account nor organization ownership from request bodies, queries, paths, or arbitrary client headers. Production application creation fails closed without an explicit production-capable trusted resolver and rejects the local resolver. No identity is returned by the metadata route. `/health` may remain public because it exposes process/service health only; every protected product route consumes trusted server identity.

`TrustedIdentityResolver` establishes trusted server-side identity context only. Identity resolution alone is not project authorization, organization authorization, product entitlement, billing enforcement, or subscription validation. Those controls remain future backend responsibilities and require explicit server-side policy decisions for each protected operation.

The resolver's `production_capable` property is a composition guard that prevents known local/test resolvers from being selected while the application is configured for production. It is not cryptographic proof, external-provider certification, or a replacement for security review. Future production adapters require independent implementation and security validation.

This local identity is not an authentication implementation, anonymous production user, ownership database, or authorization grant. No authentication provider has been selected, and no entitlement or billing behavior exists. The Stage 0.2.2 review accepts only this provisional identity seam; it does not approve production authentication, authorization, entitlement, billing, subscription, or deployment controls.

Provider-specific identity tokens, claims, SDK types, and session behavior remain in an authentication adapter. They do not enter the calculation core or canonical engineering fingerprint.

## Authorization and project isolation

The authenticated API is the authoritative policy-enforcement point. It must enforce, at minimum:

- resource ownership or authorized organization membership;
- user/organization role where applicable;
- product and capability rights;
- entitlement state and effective dates;
- project lifecycle and operation-specific rights; and
- future usage/seat limits under an approved concurrency policy.

Each list, create, read, update, calculate, snapshot, report, export, share, delete, and administrative operation requires an explicit server-side authorization decision. Query filters alone are defense-in-depth, not the sole policy check. Project lookup must be scoped to the trusted account/organization context so cross-project or cross-tenant identifiers fail without confirming whether the protected resource exists.

Frontend visibility, disabled buttons, routes, and cached entitlement state improve usability but are never entitlement or authorization enforcement.

The conceptual ownership/rights model is specified in `PROJECT_OWNERSHIP_AND_ENTITLEMENT_MODEL.md`.

## Entitlement and billing boundary

Product access uses a general entitlement model rather than a hard-coded subscription type. Entitlement resolves product/capability rights and effective state; billing is one possible source of commercial events.

- Payment or subscription providers do not call or configure the calculation engine directly.
- Provider-specific products/prices map through server-side commercial configuration to stable internal product/capability rights.
- A paid invoice alone is not a client authorization credential.
- Billing webhooks/events, when implemented, are authenticated, idempotently processed, audited, and translated into entitlement state by a trusted server component.
- A billing/provider outage must not grant access by default.
- Engineering results remain immutable when entitlement changes; access to them follows the future expired-access and retention policies.

Authentication provider, payment/subscription provider, billing interval, licensing metric, plan shape, trial duration, bundles, enterprise terms, and expired-access policy are all **Future Decisions** and are not selected here.

## Calculation authority and engineering separation

**Provisional — PRV-012:** server-side calculation is authoritative. Independently of the final execution topology, a frontend is an untrusted client and cannot issue an official engineering result or persist a trusted calculation snapshot independently.

The calculation core:

- accepts only explicit, validated engineering inputs and controlled engineering data/version references;
- has no account, organization, role, entitlement, billing, website, email, or payment-provider dependency;
- does not read client sessions, HTTP headers, cookies, credentials, or storage permissions;
- does not derive resistance from rendered meshes or UI state; and
- returns explicit structured statuses, never a security decision.

The application/security layer decides whether a user may request or view a calculation. The qualified engineering layer decides only the engineering applicability/result for the supplied canonical input. Authorization denial must not be recorded as `FAIL`, and an engineering `PASS` must not bypass access controls.

**Provisional architecture:** authentication, entitlement, billing, project storage, report storage, audit, and external website integrations use replaceable ports/adapters around a framework-independent calculation core.

## Data and storage boundaries

### Project data

**Provisional — PRV-014:** `ProjectRecord` holds ownership/lifecycle/security metadata separately from the calculation-input `EngineeringProjectDocument`. Database queries and object references are derived from trusted server scope. Client-controlled owner fields cannot transfer a project.

Changes to ownership metadata do not change the engineering fingerprint, but they require authorization and audit controls. Changes to engineering inputs create a new project revision and make old results stale for the active document.

### Calculation and report snapshots

Calculation and report snapshots are immutable records. Object storage remains private; any download authorization is short-lived and scoped by the server or streamed through the authorized API. Guessing an object key, knowing a snapshot ID, or possessing an old UI link grants no access.

Report generation and retrieval must recheck project/report rights. Summary and Detailed reports use the same immutable result data; access presentation cannot alter engineering status.

### Licensed and proprietary sources

Private licensed sources are never shipped to the browser, committed to Git, embedded wholesale in results/reports/logs, or exposed through a generic API. ASCE/SEI 74-23 is registered by bibliographic/control metadata only; copyrighted equations, tables, figures, commentary, and substantial text remain outside the tracked repository.

Qualified proprietary data and rule mappings are exposed only to the minimum server-side components and personnel necessary. User-visible citations should disclose controlled references without disclosing licensed content.

### Secrets

Secrets, credentials, certificates, private keys, provider tokens, and database/storage credentials remain outside source control and engineering documents. They are injected through a future approved secret-management mechanism and scoped by least privilege. Exact provider and rotation mechanics are **Pending Architecture Decisions**.

## Audit boundary

Future audit coverage should include security-sensitive sign-in/account events supplied by the identity boundary; authorization/entitlement changes; project ownership/organization changes; privileged administration; project revisions; calculation/report snapshot creation; exports/downloads where required; and failed cross-scope access attempts.

Audit entries use trusted server identity and server-derived resource scope. They must avoid unnecessary secrets, raw licensed content, and sensitive engineering payloads. Exact retention, administrative access, privacy treatment, and whether audit unavailability blocks specific mutations are a **Pending Architecture Decision** requiring security and business approval.

## Fail-closed controls

- Missing, invalid, expired, or unverifiable identity: deny the protected operation.
- Missing/ambiguous project ownership or organization scope: deny without falling back to a global or first user.
- Missing capability right, inactive entitlement, or exceeded approved limit: deny that capability under the current policy.
- Client/server disagreement: server identity, ownership, entitlement, and calculation decisions prevail.
- Project/object identifier outside authorized scope: deny without leaking protected existence or metadata.
- Unavailable authorization/entitlement dependency: do not grant new access from an untrusted client claim; any availability exception requires a separately approved cached-policy design.
- Calculation version, source, applicability, input, or qualification failure: return the appropriate engineering non-success state, never placeholder `PASS`/`FAIL`.
- Storage write ambiguity: do not claim a snapshot/report was saved or immutable.
- Warning-only treatment cannot replace a required security denial or engineering unsupported/incomplete state.

## Security verification gates

Before production, validation must cover authentication boundary handling, object- and function-level authorization, cross-account and cross-organization project isolation, entitlement state/date/capability checks, report/object access, privilege changes, provider webhook authenticity/replay behavior, local-development identity exclusion, secret and licensed-source exposure, audit integrity, and calculation-authority controls for the approved topology. If `PRV-012` is approved, those controls include server-authoritative calculations.

Stage 0.2.2 tests cover only the implemented trusted-identity seam, client-header spoof resistance, identity-free health route, and production fail-closed composition. Stage 0.2.3 frontend tests confirm that rendered controls and source behavior contain no identity, ownership, entitlement, billing, token, storage, API, or engineering-result surface. The Stage 0.2.3 implementation is complete and reviewed, its validation passed, and the untrusted presentation shell is provisionally accepted as the frontend foundation. These tests are not authentication, authorization, tenant-isolation, penetration, real-browser/end-to-end, engineering, commercial, or production-readiness validation. The frontend performs no API request, establishes no identity, performs no authorization, enforces no entitlement or billing decision, and stores no ownership or security claim; the trusted backend remains the future authoritative security and calculation boundary.

## Future decisions - deliberately not selected

- Authentication, payment, subscription, email, cloud-hosting, managed database, and object-storage providers.
- Monthly/annual billing, named-user/concurrent-seat licensing, plan/customer types, trials, bundles, and enterprise licensing.
- Expired-subscription access, data retention, organization administration, seat/usage enforcement, and audit retention.
- Exact deployment topology, MES website/Client Login integration, and FRP Master Pro interchange.

These choices must remain behind stable boundaries. Selecting one later must not couple the engineering calculation engine to that provider.

## Stage 2.2B trusted calculation transport

The calculation POST route uses the existing server-selected identity resolver. JSON
contains no identity, organization, role, entitlement, engine/rule version,
fingerprint, result, PASS/FAIL, capacity, utilization, or governing authority fields.
Identity cannot alter engineering output or its fingerprint. The route logs and stores
no payload, creates no cache/project/report record, and returns no environment,
filesystem, PDF, credential, stack, or internal-repr data. This is identity
resolution, not authorization or entitlement; those controls remain future and must
fail closed when introduced.

## Stage 2.3 browser trust and storage boundary

The browser is an untrusted presentation and request-construction client. It calls
only the same-origin calculation path and cannot supply identity, engine/rule
versions, fingerprints, results, governing state, or visualization authority. All
engineering response data and the canonical visualization snapshot are server-built.
Transport, validation, identity, and unexpected-service failures remain visibly
distinct from HTTP 200 engineering outcomes.

The workspace writes no local storage, session storage, cookie, project, report,
database, cache, or analytics record. Its case label is not an identity or ownership
claim. Stage 2.3 adds no authentication, authorization, entitlement, cross-tenant
isolation, persistence, or production deployment assertion.

## Stage 2.3R security boundary

The refinement changes presentation and controlled input geometry only. It adds no
trust boundary, route, identity or owner field, storage, cookie, analytics, report,
external asset, credential, deployment provider, or client calculation authority.
Friendly labels and rounded display numbers never replace stable server IDs or exact
server-returned values. Solid/X-ray, overlays, camera fit, and inspectors remain
untrusted presentation state.

## Stage 2.3R5 preview trust boundary

The preview route retains the existing server-injected trusted identity boundary and
accepts no client owner, organization, role, entitlement, version, status, result, or
fingerprint authority. It is stateless: no request or response is persisted, cached,
reported, or written to browser storage. Strict DTO validation and canonical mapping
remain server-side.

Preview responses intentionally exclude resistances, capacities, utilization,
governing checks, design PASS/FAIL, qualification outcomes, equation traces, and
calculation fingerprints. Aborted and obsolete browser requests are discarded by
revision/sequence guards; network failures are shown as model-status failures and do
not convert an old model or design result into current evidence. The change adds no
credential, cross-origin endpoint, analytics, database, authentication, entitlement,
or deployment-provider decision.
