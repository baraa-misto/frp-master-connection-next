# Direct Owner Round 2 F2 candidate

This bounded successor to `015e55c004017124728f7e8c03948dc232b3c8de` remains on
`codex/shear01-direct-f1` for review. It does not freeze Direct or activate qualification.

## Audit conclusions

The exact accepted 4 × 4 × 0.5 in Angle / 8 × 8 × 0.5 × 0.5 in W, 2 × 1 starter
remains physically valid. Its W contact-patch distances are 1.3376262658470832
and 0.9981601717798214 in. The reported owner 0.086 in value cannot be bound to
this starter without its authenticated request/report. A deliberate e1 = 4.77 in
QA placement reproduces approximately 0.086 in; it is not claimed as the owner's case.

The current validator checks selected contact-patch boundaries, including the W
outer negative flange strip outside the web projection. Such a boundary is not
automatically a free physical member edge. This candidate labels it explicitly,
retains the existing minimum max(1.5d, hole radius, washer radius), and supplies
backend vertices, axes, all four signed distances, controlling boundary and a
face-normal diagnostic overlay. It does not change the validator or physical mapping.

No controlled ASTM F593-17 Group 2 316/316L cold-worked condition/diameter Fnt
table was found. Fnt remains missing; accepted Fnv thread-plane rules remain.
This is a catalog source-data gap, not a per-connection supplier certification
requirement. Selected hardware remains the specified project hardware.

Both immutable ICE seeds remain DEVELOPMENT_NOMINAL. The supplied ICE manual
describes average sample properties with a different property/scope basis; it
does not qualify these exact records or the owner's 4 in Angle. Promotion needs
controlled exact-product/revision/shape/thickness, statistical characteristic
property evidence, reference conditioning and Tg applicability. Procurement
conformance notes remain distinct from design basis and Section 2.3.2.

## UI and reports

Sustained operating material temperature controls existing backend CT rules;
maximum expected material temperature controls the separately reported Tmax/Tg
comparison. Missing Tg is NOT CONFIRMED and does not erase calculable CT.
Entered Tg comparison PASS is not controlled product qualification. The strict
existing CT applicability boundary and all completeness gates remain unchanged.

Rational elastic bolt-group method is neutral information. Geometry invalidity
is red, completion actions amber, and stale/inactive results gray. Numerical
results, warning/blocker counts and family-specific engineering remain unchanged.
Invalid reports identify the boundary and hardware dimensions; exhaustive native
geometry remains in Full Technical Audit. The renderer only reads signed snapshots.

Clearance witnesses are opt-in Direct API transport metadata. Shared native preview
records and their historical fingerprints retain their original structure. Report
snapshot invalidation follows submitted geometry/material/condition/hardware inputs;
preview bookkeeping no longer discards a signed response to those same inputs.

## Required publication gates

Backend: 7847 tests, 100% statement/branch coverage, Ruff, strict mypy, dependency
and package validation. Frontend: 1200 tests, 100% statement/branch/function/line
coverage, TypeScript, ESLint, build and audits. Actual signed F2 PDFs are generated
on Windows and Ubuntu. External evidence records actual outcomes and exact SHA;
these counts do not claim success before QA. Main and protected tags stay unchanged.
