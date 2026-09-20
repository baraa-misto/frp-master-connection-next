# CME-2B RC1 R1 validation

Starting authority: clean synchronized main `c4b8552e33a6d20d3f5ec5257fa741ffebc6a176`, count 126; CME-1 implementation `d62064a7d96ba139841c222f90b62b8e7c4601c8`; fourteen existing immutable tags. Expected implementation count 127; no new tag.

## Evidence obligations

The new `backend/tests/calculation/test_stainless_plate.py` independently exercises all eleven positive cases, fourteen negative cases and eleven invariants in the byte-exact RC1-R1 golden. Decimal repeating oracle values are compared at their prescribed serialized precision, with exact rational resistance/utilization proofs independently retained; display precision never selects a governing check. The only RC1-to-R1 golden changes are the three native stress-conversion fields and corrected AISC 360-22 metadata. All resistance expected values remain unchanged.

| Order checklist | Evidence |
|---|---|
| 1-24 material/source/grade/fabrication | Closed catalogue, trusted-record/domain/adversarial tests in `test_stainless_plate.py`; source/artifact hashes in register |
| 25-39 thickness/tolerance/units | Boundary, verified/unverified credit, property-domain, SI and ambient-context tests |
| 40-80 holes/detailing/net area | Five-row tests, unsupported diameter/type, spacing/edge/contact, net deduction and SI identity tests |
| 81-99 tension/shear | Independent positive fixtures, U classification, factors, deterministic governing and monotonicity tests |
| 100-125 block/bearing/tearout | Uniform/nonuniform paths, both branches, supplied candidates, l1 definitions, per-hole demand and unsupported-branch tests |
| 126-146 result/fingerprint | Independent status channels, retained failures, full provenance, exact ratios, unit/context invariance and input mutation tests |
| 147-157 source integrity | Exact archived-byte hashes; independent controlled golden cardinalities and source signature tests |
| 158-172 frozen compatibility | New `test_stainless_plate_isolation.py` plus all unchanged `test_connector_material*`, native/freeze regressions; reviewed zero existing production diff and exact tag inventory |
| 173-180 architecture/hygiene | Pure-module import audit, unchanged dependency/lock/API/frontend/hardware trees, no PDFs, no golden-driven production, reviewed changed paths |

The coverage map does not itself certify a gate as passed. The complete command evidence must also pass before publication: backend-check, frontend-check, check-all (including clean install and audits), JSON validation, reviewed staged whitespace/diff, and all historical tests. Configured coverage must be 100% and both npm audits zero. No expected values, historical assertions or coverage policy are weakened.

## Publication evidence

Exact commit, final counts, command logs and direct hosted CI run/head SHA/job results are recorded in the external completion report after publication, not fabricated into a pre-commit document. Required subject: `feat: implement CME-2 C2-M and C2-P1 stainless plate provider`. One normal non-force main push; no amend, no tag and no second correction commit under this order. Direct hosted Backend/Frontend Ubuntu/Windows success for the exact pushed SHA is mandatory before final acceptance.

Local software QA is not family-level stainless engineering approval. Synthetic numerical source records remain test-only. No existing connection family is stainless-enabled.
