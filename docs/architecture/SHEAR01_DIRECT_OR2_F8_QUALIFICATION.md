# Direct Section 2.3.2 qualification contract — F8

Controlling owner order SHA-256: `8960AFFAED49B21CE64B146BAF6E0B01D03BCDFAC66A240B54CD4FECE7668095`.
Base candidate: `342e3f827d840928ca57e76037bc11a0fd345511`.
Scope is the Direct single-angle-to-W adapter. The eight F7 analytical records,
their aggregation, frozen engines, inactive RC3 and other families are preserved.
F8 never grants final GREEN or ordinary whole-connection PASS.

## Server authority and normal workflow

The authenticated MAT1 multi-row design endpoint adds `qualification_evaluation`
only for the Direct finalization contract. Selection submits an installed record
ID; arbitrary records, statistics, approval flags and computed capacities are
not request inputs. Optional `qualification_context` supplies actual project
product/hardware/fixture/action declarations; these are comparison inputs,
never evidence or approval. Missing product identity, bolt installation/grip,
support stiffness or action history cannot match an approved record. The ASCE
minimum material specification is not actual tested-product identity.

`GET /api/v1/frp-materials/direct-qualification/records` returns compact installed
IDs, revisions, digests, laboratory/RDP metadata and provider state. No public
write/approve/upload route exists. Public evaluations omit raw specimens and
proprietary document bytes. Authenticated REPORT1 snapshots pin the full private
audit during the same backend request. Export checks record availability,
revision and digest again; withdrawal, supersession, source mutation or invalid
provider index requires a fresh check. Export never recalculates engineering.

The panel displays concise limitations and final-status integration pending.
Design-affecting changes invalidate its evaluation through the existing MAT1
identity and workspace staleness; camera changes remain presentation only.
The default provider is empty. The normal owner remains 8 evaluated / 6 unresolved
/ YELLOW. The five unsupported response rows retain coverage-required reasons,
and the whole-joint row requires an approved matching record.

## Immutable records and controlled installation

Schema and record-provider adapters live in infrastructure. Application identity,
statistics and scope matching remain framework-independent under the existing
architecture gate.

`QualificationRecordSchema` retains raw specimens, exclusions, document
hashes/locators, laboratory/accreditation, RDP protocol/statistical/scope/mode
approval, separate applicable AHJ evidence, all tested scope and lifecycle.
Canonical UTF-8 JSON sorts keys, preserves numerical strings, rejects nonfinite
JSON and hashes content excluding its own digest. All changes create revisions.
Only AVAILABLE_FOR_MATCH may be consumed by the production provider.

`QualificationRecordProvider` supports controlled static records with an evidence
root and an external read-only `FRP_QUALIFICATION_RECORD_DIR`. Every read verifies
the controlled index, exact file set and byte hashes, sealed record digests,
document bytes, metadata, statistics and latest revision. Duplicate revisions,
in-process content changes, revision/index rollback and broken successor chains
fail closed. Retain old revision files and publish a higher revision to withdraw
or supersede. Administrator deployment must preserve the index and append-only
record history across service restarts; in-process pins alone are not durable
storage or a digital-signature service.

Offline command (from backend):

```
python -m frp_master_connection.qualification_admin evidence/record.json --output qualification-records
```

It writes an exclusive validation receipt with all schema/evidence/statistical
blockers and a canonical record. Only a package with no blockers is copied into
the immutable provider directory and indexed. It never promotes approval state.
The engineering administrator verifies scientific adequacy, professional
authority, laboratory conformity and project applicability before controlled
installation. Software checks metadata and byte identity; it does not
cryptographically validate professional seals or independently accredit a lab.

Synthetic origin is retained at record and document level, with digest and
source-byte checks. Synthetic records cannot declare AVAILABLE_FOR_MATCH or
activation permission, and production providers reject them. Test-only numerical
previews call an internal evaluator with an explicit nonactivating QA flag;
there is no public flag. Lifecycle/import unit tests use narrow authority policy
doubles, visibly documented in tests; these do not install approved evidence.

## Scope and capacity

Exact matching covers physical configuration, section dimensions and canonical
bolt coordinates, real end/side inputs, orientations, actual supplier/product/
resin/fiber/revision/qualification identity, controlled fastener alloy/condition/
marking/thread/nut/washer/installation, all six actions and frame/reference,
load history/rate/protocol, support ends/fixture/stiffness/restraints and actual
environment. Unknown fields are not wildcards; explicit inapplicable states are
limited to their declared physical context.

Supported rules: EXACT, approved enumeration/product-equivalence tuples,
one explicitly approved inclusive length range in canonical mm, and a full
six-component proportional action ray in N/N-mm with identical frame/reference.
Discrete configurations cannot use ranges. Multiple independent ranges require
additional correlated authority and remain blocked. Ray matching converts the
canonical decimal operands to exact rational cross products and scale bounds,
with no projection or force/moment tolerance. It rejects
changed moment/reference/history even when force magnitude is unchanged.

The five response IDs carry coverage provenance from one whole-joint capacity;
they do not receive invented component resistances. Whole-connection approval
also requires explicit RDP dispositions of heel/junction, delamination, local
bending, through-thickness, prying/axis tension, 3D eccentricity, physical Angle
block response and serviceability/damage. Peak strength alone is insufficient.

Reference/conditioned test baselines select existing MAT1 CM/CT/CCH at most once.
Different participating material factor sets require a separately approved
whole-joint basis and are currently blocked. Lambda remains the current governed
MAT1 load factor. No Chapter 8 phi, lap or delta factor is added to test strength.
General Ru <= Rd_q is separate from literal gravity Rd_q > 1.2D + 1.6L; the latter
requires known nonnegative nominal D/L and an approved gravity protocol.

Engineer Reports show a compact summary and clear limits. Full Technical Audit
retains complete immutable metadata, raw/excluded specimens, statistics/t trace,
all factor and field comparisons, action/reference scope, coverage, lifecycle,
design-scope digest and evaluation digest. No real record was supplied for F8.
