# Contributing

FRP Master Connection is governed as engineering software. Contributions must preserve traceability, fail-closed behavior, repository isolation, and the distinction between approved, provisional, and pending decisions.

## Stage 0.1 contribution boundary

Do not add production application code, engineering equations, resistance factors, capacities, numerical code criteria, force-distribution logic, utilization calculations, optimization, report generation, or placeholder functions that return `PASS` or `FAIL`. Do not install application dependencies during this stage.

## Controlled changes

1. Identify the affected baseline requirement, decision, source, risk, and artifact.
2. State whether the change is editorial, provisional, pending, or proposed for approval.
3. Do not silently reopen an `Approved` decision. Record a genuine engineering, safety, security, or architectural conflict and the responsible approval authority.
4. Keep source edition, errata set, applicability, verification evidence, and engineer approval traceable.
5. Update the artifact/version register and handoff manifest when the controlled artifact set or stage state changes.

Only the statuses defined in `docs/governance/DECISION_REGISTER.md` may be used in the decision register. A document marked draft is not an engineering approval.

## Licensed and proprietary sources

- Never commit a licensed standard, proprietary installation data, credentials, or private customer/manufacturer data.
- Do not reproduce ASCE/SEI 74-23 equations, tables, figures, commentary, extended excerpts, or numerical criteria in repository documentation unless a later approved source-handling process explicitly permits the specific use.
- Keep authorized local source copies outside Git or under `reference-private/`; verify ignore behavior before placing anything there.
- Record source metadata and mappings without treating a bibliographic entry as engineering validation.

## Engineering implementation gate

Before a calculation family is implemented or commercially described as validated, it requires source mapping, an applicability definition, deterministic and unit-aware implementation planning, independent verification, representative pass/fail and boundary cases, and qualified engineering approval. Unsupported or incomplete conditions must use a required fail-closed state; warnings cannot substitute for that state.

## Change workflow

- Work on a focused branch and leave unrelated user work untouched.
- Use clear, reviewable changes; do not fabricate artifact hashes, approvals, test results, or source references.
- Run checks appropriate to the stage and report exactly what ran.
- Never commit secrets or generated private reports.
- Obtain engineering approval for engineering-method changes and security/architecture approval for trust-boundary changes.

Stage 0.1 has no application test suite because it has no application code. Repository and document validation must not be represented as calculation validation.
