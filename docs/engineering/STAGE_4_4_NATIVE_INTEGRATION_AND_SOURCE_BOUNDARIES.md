# Stage 4.4 native integration and source boundaries

## Controlled authority

Product `ANGLE_COLUMN_TWO_LEG_MOMENT_BASE_CONNECTION`, contract `4.4-RC1`.
Starting main: `1faa1ff522d0e0a39a42e2dc2d3974b5dba98479`, count 114.
Order SHA-256: `71C62369A68ED8CB61BB04539FF9F2C13D2B9B237C6B10449C3CBE5340487009`.
Matrix SHA-256: `A09FB76C07AB12AB9C435CAD1B29806D4B4DB839B12191444BE4507DFE0D9BB8`.
These are integration/project authorities, not additional prescriptive ASCE formulae.

S1 externally held ASCE/SEI 74-23: `A7127E37572D5D625C5F338FFB9A1D2D53F396897AFB26E0B4698A0131FE65BC`.
S2 Erratum 1: `5B58E842DA9025934D12EB386C416E94CB3B53999B21F59B0606F2B09D9DE550`.
Reviewed actual PDF pages 19-20, 22-26, 46-52, 111-112 and the erratum:
Sections 1.4.2, 1.7.2, 2.3.2, 2.4, 2.9, 2.10, 8.1-8.4, C8.3.4/C8.4.
The erratum changes the Chapter 5 transverse-modulus description, not base response.
No licensed PDF or extended standard quotation is registered here.

## Consolidated preflight and physical catalogue

The clean active clone started at the exact count-114 frozen Stage 4.3 target.
All eleven annotated tag objects and peeled targets were compared with the established
local/remote register. The original desktop worktree's ten obsolete freeze drafts
were hash-checked and left untouched. Full proposed new-product/shared-glue/test/
governance scope was projected through the historical security guard before implementation.

No preset adjustment was necessary: equal L 8/8/.5 in and unequal L 8/6/.5 in;
18 in display length; finite 32/32/12 in pedestal; independent 6/6/6/.5 in
connectors with .25 in inside radius and centers 4/4 or 4/3 in. Each group is
2 across x 2 along, gauge 3 in, pitch 2 in, center 3 in. Bolts/anchors .5 in,
source-defined .563 in holes, 4 in embedment. U.S.-source holes convert exactly,
not to regenerated metric nominal holes. The accepted profile's sharp-corner
representation and native overlap/centroid are retained.

There is one actual L column, two different-leg exterior brackets, eight two-leaf
member shanks, eight distinct blind foundation shanks, sixteen member washers and
eight exterior foot washers. Member head/nut endpoints use explicitly known geometry;
the anchor nut is the existing schematic external-anchor presentation, not new strength
authority. No nut below the pedestal, backing plate, sleeve or cavity material is invented.
Hardware, hole, fillet, free-boundary and positive-volume interference checks fail closed.
The L-shaped prepared end footprint is represented by actual nonoverlapping rectangles.

Base axes are X/Y leg-parallel, Z vertical; they are not principal section axes.
Q1=(+X,+Z,-Y), Q2=(-Y,+Z,-X), both determinant +1. Native connector heel is the
intersection of leaf midsurfaces: bracket 1 heel (center,-t/2,t/2), bracket 2
(-t/2,center,t/2). Physical member/foot pattern centers are mapped to heel-local
coordinates by subtracting t/2. No fictitious physical recentering or hidden face flip.
The column material LW is Z; each connector LW is its own horizontal extrusion A.

## Native callable and numerical boundaries

All paths below are under `backend/src/frp_master_connection`.

| Boundary | Reused authority / callable | Stage 4.4 behavior |
|---|---|---|
| Actual column reference | `domain/member_profile.py`, `profile_member_axis_reference` | Accepted Decimal-28 ROUND_HALF_EVEN centroid, not a rational reserialization |
| Physical surfaces/material basis | accepted profile topology, R14B region basis and shared solid/hardware helpers | New two-leg placement only; actual LW/CW/TT on six leaves |
| Complete angle transport | `calculation/angle_connector_core.py::resolve_angle_connector` | Material-neutral Slice 7 core, exact finite native wrench consumed unchanged |
| In-plane bolt demand | `calculation/in_plane_wrench_demand.py::calculate_in_plane_wrench_demand` | Slice 8 exact rational mechanics, native Decimal-80 projections; explicit independent M_C |
| FRP body | `calculation/frp_angle_connector_provider.py` | Native applicable instep check and exact signed full-wrench qualified source |
| Member capacity/source | `application/wi_wall_moment_sources.py` | Existing attachment coverage and FRP provider; distinct actual column material/context |
| Normal/contact response | `calculation/support_attachment_response.py` | Existing exact action/shaft validation, new Stage 4.4-specific domain/coverage |
| Bolt capacity | `calculation/equations.py` and `sourced_bolt_interaction.py` | Native sourced shear/tension/combined checks; actual grip/thread/plane and complete verified demands |
| Local FRP | existing bearing, pull-through and multirow engines | Actual layer direction/thickness/hardware; no new failure equations |
| New total/reference algebra | `calculation/angle_column_base_response.py` | Fractions over authoritative finite native quantities; exact shifts/sums/proofs |

The independent source-present tests assemble core geometry/frames/member and foot
references from the original physical request and source record, not the adapter's
exported requests. Bolt coordinates are assembled independently from row/line dimensions;
direct Slice 8 calls then compare complete native results. Reordered bolt inputs preserve
per-ID native vectors but retain the dependency's ordering-sensitive fingerprint.
F44-01..14 are separate exact rational mathematical checks, never replacement Decimal
oracles for inherited engines. No epsilon, residual clipping/redistribution, M/z shortcut,
equivalent eccentricity for free moment, or Stage 2.5A modification is introduced.

## Qualified response and demand accounting

Input is column-on-base F=(Vx,Vy,N), M=(Mx,My,0) at the actual lower-end centroid.
Positive N is uplift, negative N compression. Independent Mz is rejected;
reference-generated Mz is retained. Required total at O is available independently
of allocation. Opposite reaction is a separate sign convention, not another load to add.

`QUALIFIED_ANGLE_COLUMN_TWO_LEG_BASE_RESPONSE_RC1` binds actual geometry/material/
hardware, both leg assignments, five actions and complete frames/references to
provenance, applicability and compatibility/coverage. Exact equilibrium is necessary,
not qualification. Missing branches are not zero; inactive branches/contact need explicit
certification. Pressure must lie in real prepared L material, be compressive and integrate
to its furnished action without unsupported friction.

The production registry is empty. Nonzero default inputs therefore yield SOURCE_REQUIRED:
total foundation actions are known, branch/member/anchor forces are unavailable, and no
resistance is evaluated on invented demand. Zero/no-preload may prove zero transfer.
Synthetic source IDs and assumed test strengths exist only under tests and cannot be
resolved by typing them in the workspace.

With an applicable base response, both complete member wrenches go to Slice 7.
Each member in-plane (F_A,F_B,M_C) goes directly to Slice 8. The complementary
(F_C,M_A,M_B) remains required. A separately qualified normal/contact source must
recover that complement and supply actual complete per-bolt tension/prying/shaft
demand; its shear must equal the unchanged opposite Slice 8 projection. Neither
the source nor Stage 4.4 rebalances the native finite projection.

Pin bearing uses actual column LW=B versus connector LW=A. Native row-pitch
reduction requires an established constant cardinal direction. Concentric,
authorized extrusion-end net/inter-row paths use actual geometry; free-moment,
oblique, heel/common-zone or incompatible paths remain explicitly source-limited.
Pull-through uses both native branches and actual washer/layer properties only
after normal demand is qualified. No invented heel, delamination, secondary bending
or prying capacity. Existing F593 identity supplies no unqualified nominal strength.
Qualified local-zone coverage may address named unresolved paths but never erase a
native evaluated failure. Evaluated FAIL governs, all subordinate failures remain visible.

Each foot exports its net full wrench. An optional furnished anchor/contact breakdown
must bind actual group/points/foot boundaries and exactly recover its parent with any
explicitly source-authorized free couples. Absent breakdown stays UNAVAILABLE_EXTERNAL.
Net feet plus direct column contact are summed once; optional breakdown actions are never
added again. No individual anchor force, concrete strength or foundation PASS is calculated.

## Application and verification scope

Stateless authenticated defaults/preview/design-check endpoints live under
`/api/v1/calculations/angle-column-two-leg-moment-base`.
Preview performs zero resistance calculations. Engineering edits clear incompatible
qualification, stale design and request debounced latest-response-wins preview.
View length/selection/camera are presentation-only. Invalid input keeps an explicitly
last-valid scene and blocks design; no old failure table is presented as current.
Independent full-width bolt/attachment groups and five signed editable load arrows use
one request state. The new product shares the viewer without changing historical products.

External: anchors/concrete/foundation adequacy; overall column strength/stability;
stiffness/rotation/full-strength classification. Internal source qualification/review
does not become an ordinary whole-connection PASS. No Stage 4.5 or 316SS work.

## Historical guard maintenance

`tests/calculation/test_scope_boundaries.py` formerly applied its nine-file security
successor rule to every later product tree. It now separates immutable old evidence
from this explicitly registered product scope using test-only
`stage_4_4_scope_authority.py`. The original protected digest
`968847BF52C927427D5D71F31FD1395E04892697BB109BECDADD2070AF1BDD2E`
and all previous timeout/dependency/freeze pins remain unchanged.

`tests/golden/stage_4_4_historical_scope_evidence.json` captures actual original
513e1c9 and 1faa1ff Git entries before maintenance; canonical LF SHA-256
`0A2CAC24EA9FA064097056E731CDFF9294D3CF872B8FE132850F9E51B5017540`.
Full-history runs compare actual Git objects. Tagless runs authenticate the pinned
historical listing and label reconstructed historical scope; they do not pretend to
fetch absent objects or compare successor HEAD as historical content.

The helper permits only named new Stage 4.4 files, exact additive route/selector
and route-inventory blobs, and explicitly named current governance records. Tests
reject old content/add/delete/rename/commit/tree corruption, unrelated production/
workflow mutation, wildcard historical exemption and unsafe file modes. Forward probes
register a separate future governance/product/test example in memory without changing
history or granting that production permission today. Exact route inventory tests in
`tests/test_api.py` and `tests/test_calculation_api.py` add only the three new routes.
No historical engineering assertion, manifest, golden, dependency or tag changed.
