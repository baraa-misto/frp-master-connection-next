# Stage 3.3C3-R1 Material-Axes Coverage and Binding Correction

## Authority and baseline

The external correction order was read completely and verified at SHA-256
`402E53455241A97083A0D800138B3AB5FB785EECD2EAA01F349FD497E8E519D6`, including
its exact final sentinel. Work began from clean synchronized `main` commit
`3ab4d2c81c264ad698c9f13d78d8be8bbb86a626`, commit count 73. Backend tree
`5b29432bf56c71243c431381dd052ef07985be6c`, frontend tree
`629f8e89d2214f18a1d1f4afb2911a183ddebcb5`, and frontend source tree
`3a8b4755de77a778641dd5869329321ec2370dcd` matched the controlling baseline. Both
immutable freeze tags remained exact.

## Mandatory pre-mutation diagnosis

The Paired W/I + W Column Flange reproduction contained four exact connector material
records, three connected W/I region records, and three supporting W region records in
both the backend result and serialized API payload. The connector records retained
distinct `POSITIVE_CLIP_ANGLE` and `NEGATIVE_CLIP_ANGLE` owners and the accepted mirrored
R14B LW/CW/TT vectors. All backend physical primitives required for embedded anchoring
were present.

The first paired loss occurred in the frontend Single-to-Paired scene adapter. Its
shared material mapping hard-coded the Single connector owner before attempting an
embedded presentation. Paired owner-qualified element identities therefore could not
match either angle's primitives. Connected primitives also arrived owner-qualified,
but their material records used owner-local identities. Supporting material records
were omitted. A later paired relabel occurred after presentation construction and could
not recover a failed binding. `EngineeringScene` and the overlay toggle correctly
received the resulting null presentations and correctly rendered no indicators.

The Single Flat Plate + W Column Flange reproduction contained two connector, one
connected-plate, and three supporting-W material records in backend and API output.
The first Single loss was the frontend material mapping's omission of
`support_material_regions`. Connected and connector presentations were otherwise
correct. No backend production defect, renderer visibility defect, or toggle defect
was found.

## Correction and shared identity rule

The shared presentation adapter now resolves an optional backend owner-qualified
identity against actual rendered primitive owners, then uses the owner-local element
and material-region identity only for presentation binding. Primitive identities are
normalized by their exact owner prefix before region matching. Engineering material
IDs, serialized payloads, geometry, and fingerprints are not changed.

Single and Paired adapters both map connector, connected-member, and supporting-member
material regions before `EngineeringScene` receives the model. Positive and negative
angles retain distinct component ownership, so equal leg names cannot de-duplicate
their presentations. Support regions use the backend-authored support profile family,
region identities, origins, and LW/CW/TT vectors. Every anchor remains derived from
backend-authored box/mesh geometry through the existing shared region-embedded
presentation builder. No profile-specific coordinate or axis-vector workaround was
added.

## Coverage and engineering invariance

Automated regression covers Single and Paired connector components, the six connected
profiles, and all seven support targets. W/I and Channel expose web plus two flanges;
Angle exposes both legs; RHS exposes four walls and never a cavity axis; Flat Plate and
SRS expose the accepted plate/solid-volume basis. The Paired regression separately
requires positive connected/support legs and negative connected/support legs, unique
owner-qualified presentation keys, and non-null connected/support presentations.

Backend tests prove the already-complete payload and API serialization, exact positive
and mirrored-negative R14B bases, orthonormal region vectors, complete physical-region
matrices, and the exact pre-correction Single/Paired engineering fingerprints. C1
G1-G12, C2 G1-G18, C3 G1-G20, Stage 3.3A/3.3B, Tee R14B/R14C, Direct, controlled-hash,
and freeze audits remain in the complete gate. Backend production changed zero files;
material bases, properties, geometry, equations, results, statuses, and fingerprints
changed zero times.

The active frontend source tree is the presentation-only successor
`ea62799a02b41c30dbc25c9ad250a318aba953ae`. The accepted C3 tree
`3a8b4755de77a778641dd5869329321ec2370dcd` remains registered as its historical
predecessor. Package, lock, dependencies, workflows, controlled engineering artifacts,
and immutable freeze tags remain unchanged.

Complete local, integrated, object-isolated, push, hosted-CI, and post-CI visual
acceptance evidence is recorded only after each respective gate; none is inferred by
this record.
