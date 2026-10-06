# Direct F5: controlled ASCE minimum shape material basis

Owner review required. Do not merge or freeze Direct.

The immutable RC1 Isophthalic polyester and Vinyl ester records specify ASCE/SEI
74-23 Table 1-2 minimum characteristic pultruded-shape properties. They are code
specification records, not manufacturer test results. The separate RC0 owner
nominal records, values, digests and screenshot provenance remain unchanged.

The controlled edition is 2023 with Erratum 1 effective January 13, 2026.
The erratum corrects Chapter 5 wording and does not amend the material tables.
The supplied controlled PDF identity and exact locators are in the catalog.

MAT1 authenticates the catalog digest and exact record identity, then binds the
selected values once at the Direct adapter boundary. Only the verified Direct
shape contract permits this binding. Plate products and other family adapters
remain deferred. No mean structural-analysis modulus authority is created.
Missing transverse compression and Poisson ratio do not become unrelated Direct
qualification gates. The pull-through rows use FRP thickness, never bolt diameter,
with exact discrete selection and no interpolation. Ordinary in-plane Direct
does not acquire a pull-through check.

The backend resolves reference condition from Section 2.4.2. Sustained temperature
drives the existing exact Decimal Table 2-2 factors. Maximum temperature separately
drives required product Tg: `max(180°F, Tmax + 40°F)`. Actual product Tg is not
fabricated. Furnished-product conformance is procurement/project QA responsibility.
The specification includes Table 1-1 physical and Section 1.3.4 durability criteria;
the 75% qualification retention criterion is not an extra resistance multiplier.

Unknown project conditions, extraordinary exposure, specified chemical exposure,
and sustained temperature above 140°F remain separate project/source gates.
User-defined records remain unqualified even if fields are labeled characteristic.
A supplied actual Tg below the project threshold preserves numerical FAIL precedence.

Direct normal selectors use RC1. RC0 is available through explicit development
diagnostics. Generic initial project conditions remain incomplete. The automatic
Tg display and calculated factor display consume backend responses; the frontend
does not calculate resistance or qualification. Signed snapshots retain selected
record, source, digest, original/consumed values, factors, Tg requirement and issues.
Reader reports use that selected authority. Legacy physical IDs remain compatibility
identities and raw details remain in Full Technical Audit.

Existing first-row eccentric, supporting-W independent path, block-shear and
Section 2.3.2 whole-connection limitations remain visible. Frozen equations,
physical geometry, F593, dependency locks and goldens are unchanged.

Verification: 75 F5 backend cases, production/legacy and stale UI regression
tests, complete configured 100% coverage gates, signed report generation on both
CI platforms, exact predecessor numerical comparison and all 53 protected hashes.
The external review package contains actual evidence and final SHA/CI metadata.
