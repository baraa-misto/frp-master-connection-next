# Security Policy

## Current scope

Stage 0.1 defines security boundaries but does not implement authentication, authorization, entitlement, billing, project persistence, report storage, or production deployment. The repository must not be treated as a production security implementation.

## Reporting a concern

Report suspected vulnerabilities, exposed secrets, authorization defects, licensed-source exposure, or project-isolation failures through the private security channel designated by Masters Engineering Solutions. Do not publish sensitive details in a public issue. A permanent reporting address and response service level remain pending business approval.

## Non-negotiable controls

- Identity must come from trusted server context; a client-supplied owner identifier is never authorization.
- Entitlements and project access must be enforced server-side.
- The frontend is never calculation authority. **Provisional — PRV-012:** the current architecture recommendation places authoritative calculations on the server.
- Secrets, credentials, certificates, private keys, licensed sources, proprietary data, and generated customer reports must not be committed.
- Public website, authenticated portal, engineering services, databases, and object storage must retain separable security and deployment boundaries.
- The calculation core must remain independent of authentication, payment, email, and website providers. Pure calculation functions are **Provisional — PRV-011**.
- Logs and audit records must avoid unnecessary engineering inputs, source content, secrets, and personal data.

Use local environment files only when a later stage supplies an approved template. `.env` and secret-bearing variants are ignored; an intentionally sanitized `.env.example` may be tracked later.

## Future security verification

Threat modeling, dependency review, secure configuration, authorization and tenant-isolation tests, audit integrity, secrets scanning, data-retention controls, incident response, and production penetration testing are future release gates. No provider or deployment topology is selected in Stage 0.1.
