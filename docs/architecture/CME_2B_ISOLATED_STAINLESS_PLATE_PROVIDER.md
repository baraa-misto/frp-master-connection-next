# CME-2B isolated stainless plate provider

Status: development/draft, internal numerical implementation only. CME-1 and all fourteen historical freeze tags remain unchanged. No public family, material editor, route, schema or native FRP provider is activated or changed.

## Authority and boundaries

The controlling R1 order is `FRP_MASTER_CONNECTION_CME_2B_C2_M_C2_P1_CODEX_ORDER_R1.md` (SHA-256 `04834ED9D03779278378B38B5F3C9AE625BE99DBD998E4D656DAB989E59593B7`). The approved engineering/source artifacts and exact hashes are registered in [the artifact register](../governance/ARTIFACT_AND_VERSION_REGISTER.md). Source reconciliation and owner approval close the final-source/property/bridge locks; older pending descriptions in the immutable approval chronology do not reopen those locks.

`domain/stainless_material.py` owns the closed conservative U.S.-source 25/70 ksi catalogue. Commercial aliases do not certify a grade. An independently known S31600, S31603 or dual-certified identity is retained without raising resistance. MTR/cold-work overstrength cannot replace the catalogue. A240/A240M-24 and A480/A480M-24 identify the flat-product chain; final ANSI/AISC 370-25 supplies the bounded stainless methods. S31600 is not a welding route; other grades still require future welding authority. Hardware remains wholly separate.

`calculation/stainless_plate.py` is a pure internal boundary. `PlateRequest` describes the physical plate and resolved section/path/hole checks. `PlateContext` is a server-owned catalogue of exact `TrustedPlateRecord` bindings; it is not an API DTO or a user-entered source override. It defaults to no approved records. Each record binds the complete request, geometry authority, resolved-demand authority, content identity, property thickness domain and optional thickness-tolerance evidence. Synthetic test records are never production qualification or registered providers.

No existing family imports these modules. Public CME-1 SS316 planning and its unconditional unavailable-provider guard remain frozen. This stage does not populate a production family response/qualification catalogue.

## Numerical responsibilities

The provider uses the repository-native `PhysicalQuantity.to` conversion exclusively, including the R1 exact stress conversion. Rational arithmetic preserves unrounded comparisons; deterministic Decimal output uses the native quantity precision of 100 with ROUND_HALF_EVEN. There is no second stress conversion, equivalent force generation, force redistribution or golden lookup.

Applicable locators: ANSI/AISC 370-25 B4.2a, B4.4b, D3, J3.2-J3.5, J3.10a and J4.1-J4.3. The covered methods are gross/net tension, connecting-element shear yielding/rupture, supplied resolved block paths, and service-deformation-considered per-hole bearing/tearout. U=1 requires a trusted direct-all-elements transfer classification; Ubs requires a resolved uniform/nonuniform classification. The provider does not derive block paths, shear lag or individual bolt forces. The approved source plan owns force-direction l1 and section/path geometry; numerical checks never promote client-entered areas, capacities, classifications or forces to trusted authority.

Physical hole diameter is distinct from the source net-area deduction. The automatic standard-round-hole domain is the five approved U.S. hardware rows only; 3/8-inch and nonstandard/slotted holes fail closed. Nominal and design thickness, default reduction, verified tolerance credit, spacing/edge/contact dispositions and warnings remain separate. Continuous-contact longitudinal detailing uses plate-local Y, with the actual contact contract and thinner element supplied in the trusted geometry plan.

Results retain all covered checks and deterministic unrounded governing selections, the complete resolved request and matched source record, independent geometry/material/method/demand/response dispositions, nominal/design thickness and a provider-specific fingerprint. An evaluated FAIL is retained alongside missing demand or unqualified material-dependent response. `ISOLATED_COVERED_CHECKS_PASS` means only the evaluated local numerical checks pass; it is never whole-connection acceptance. Missing/unsupported checks do not create capacity.

## Reproducibility and future scope

Method identity: `C2_P1_AISC_370_25_FLAT_PLATE_LRFD_RC1_R1`. The unchanged native canonical fingerprint helper binds physical quantities, exact certified identity, property/source/method identity, complete plan and demand provenance, nominal/design thickness and credit evidence. Display units, formatted output and ambient Decimal context do not govern it. Historical fingerprints are not rehashed.

FRP members, fasteners, receiving-member design, foundation/anchors, corrosion suitability and whole-connection acceptance remain external/not evaluated here. Material-dependent response is C2-R; angles C2-A; Tees C2-T; compression/stability/flexure/combined action C2-P2; family activation/UI CME-3. None is implemented or authorized by this stage.

## Verification

See [CME-2B validation](../qa/CME_2B_VALIDATION.md). Exact native public payload equality is tested before/after isolated execution across all sixteen routes. Existing real native adapter, canonical-role, inventory, adverse-input, Tee historical-limitation, source and freeze tests remain unmodified and required.
