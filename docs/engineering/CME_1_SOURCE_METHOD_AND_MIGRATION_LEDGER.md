# CME-1 source, method and all-family migration ledger

Contract: `CME-1-RC1`. Accepted predecessor: `998911ea78872b852ef097dd4e20d666a33a935a` (124 commits).

This is a connector-material foundation, not a stainless design release. Primary members remain FRP. No existing editor activates stainless. No stainless strength, stiffness, resistance factor, weld/bend credit, or connector capacity is supplied by this phase.

## Source audit and exact remaining gaps

The approved companion's S1–S8 records remain unchanged. ASCE/SEI 74-23 source SHA-256 is `A7127E37572D5D625C5F338FFB9A1D2D53F396897AFB26E0B4698A0131FE65BC`; Erratum 1 is `5B58E842DA9025934D12EB386C416E94CB3B53999B21F59B0606F2B09D9DE550`. Relevant supplied text and the C8-1 table image were reviewed during preflight. These establish inherited FRP and interface limitations, not new stainless equations. The source's cited steel specification is ANSI/AISC 360-16; it is not permission to silently substitute equations from a later stainless specification.

| Source / route | Evidence actually available | CME-2 requirement before numerical use |
|---|---|---|
| ASCE/SEI 74-23 §§1.4.2, 2.9, 5.5.2, 8.1/8.1.3, 8.2/8.3; C8-1/C8.4 | Supplied controlled source and erratum; native FRP checks and row fractions retained | Resolve applicability for mixed FRP/stainless layers, actual material directions, member local failures, qualified reinforcement alternatives and external foundation design |
| ANSI/AISC 370-25 / 313-25 | Editions identified by approved publisher metadata; ordinary publisher requests returned 403 during this execution; no access bypass | Obtain full authorized normative text, choose edition/design basis explicitly, verify applicability and exact clauses, factors, fabrication and quality requirements |
| ASTM A240/A240M-26 | Official abstract/scope, plate/sheet/strip and independent unit-table warning; no mechanical tables reviewed | Verified 316/316L/dual-certification stock, condition and thickness-specific properties, original table units, limits and provenance |
| ASTM A276/A276M-25 | Approved catalogue identity only | Full bar/shape requirements; permitted hot-finished/extruded form, properties, condition, dimensions and fabrication applicability |
| ASTM A666/A666M-24 | Approved catalogue identity only | Full flat-product annealed/cold-worked requirements and domains; no inferred cold-work strength credit |
| ASTM A1069/A1069M-23 | Approved catalogue identity only | Laser-welded built-up stock/joining requirements; no automatic equivalence to rolled or bent sections |
| Existing ASTM F593 fastener sources | Separate historical fastener authority | Cannot establish connector-body Fy/Fu/E/G/Poisson ratio or fabricate missing fastener strength; retain source/thread applicability |
| Slice 7 RC2 and Slice 2 RC1 | Actual unchanged native core/provider and row-distribution functions exercised | Native transport remains valid for an already-resolved wrench, but neither an FRP source nor FRP_STEEL distribution automatically qualifies a different assembly/material response |

Publisher references: [AISC standard listing](https://www.aisc.org/aisc/publications/current-standards/aisc-370/), [AISC release](https://www.aisc.org/news/aisc-releases-updated-structural-stainless-steel-standards-ansiaisc-370-25-and-ansiaisc-313-25/), [ASTM A240/A240M-26](https://store.astm.org/a0240_a0240m-26.html), [ASTM catalogue](https://store.astm.org/products-services/standards-and-publications/standards/steel-standards.html). Listings/abstracts identify sources; they do not supply numerical authority.

Required numerical-method work is **pending CME-2**:

- Plate tension/net section, compression rupture and stability, flexure, shear, bearing, tear-out/block paths and applicable interactions: exact stainless clauses, section/slenderness/applicability limits, properties, factors and independent benchmarks.
- Angle body/heel/leg and through-thickness response: verify load path, bending, instability, local contact, prying and secondary bolt effects; no universal heel formula is assumed.
- Tees and built-up/special bodies: fabrication route, joining/weld properties, quality requirements, residual-stress/condition applicability and force-transfer checks. A geometric tee is not automatically a qualified rolled tee.
- FRP member interfaces: preserve bearing/net-section/shear-out/block-shear and directional demand paths; address pull-through/delamination/bolt-axis response only with applicable authority. Never apply FRP factors to stainless.
- Common physical fasteners: actual unequal plane forces and total interaction, no automatic double shear from two penetrations or duplicate capacity per displayed plane.
- Response compatibility: actual material/fabrication/property set, geometry/thickness, attachments, boundary/contact, temperature/environment, load signs and method version. No half/quarter sharing solely from equilibrium; source-qualified response remains a separate gate.
- Moment classification, stiffness/rotation, full supporting-member design and concrete/anchor capacity remain separate. Unknown response remains unavailable, not zero; a future passing body check cannot certify the connection.

No unresolved source in this ledger is filled by vendor typical values, synthetic qualifications, source URLs or user-entered text.

## Complete discovered product/mode migration

`CME_1_FAMILY_PROVIDER_MIGRATION_INVENTORY.json` declares all 16 native routes / 15 UI products, 445 finite native schema choices, role policies and exact native mapping/preview/design entry points. Modes are schema declarations, **not a claim that every Cartesian combination is geometrically applicable**; each existing builder retains its own fail-closed restrictions. The executable coverage check compares actual OpenAPI preview routes, actual Shear/Moment selector IDs and each native schema's finite choices. A future undeclared route/product/mode fails without altering any historical hash.

| Native route(s) | Physical connector ownership / members | Future provider and response work |
|---|---|---|
| single-bolt, multi-row | Direct FRP participants; `NO_CONNECTOR_BODY`; independent fasteners | Retain native member/fastener checks; no artificial body selector |
| tee-connector | One monolithic Tee; receiving support + connected FRP member | Tee fabrication/body methods; actual two-interface transfer and member directions |
| multi-member-tee | One shared Tee, not one per slot; independent Upper/Middle/Lower FRP members; shared support bolt group | Atomic aliases; complete shifted slot/support wrenches; qualify material-dependent response before reuse |
| clip-angle | One discrete clip angle; FRP receiving/connected members | Angle body and two interfaces; all native connected/support profile restrictions |
| paired-clip-angle | Positive and negative discrete angles; FRP connected/support members | Independent material descriptors; mixed-material assignment invalidates symmetry/response authority |
| beam-concrete-paired-angle | Two discrete angles, FRP beam and separate concrete wall | Preserve external signed wall wrenches; branch sharing/anchor response is not invented |
| direct-side-lap-concrete | Direct FRP Angle/Channel against finite wall; `NO_CONNECTOR_BODY` | Preserve selected-side/lap/anchor positions and external concrete capacity boundary |
| column-base-web-angles | Single/Double base angles; FRP W/I/RHS/SRS/Angle column; concrete foundation | Native selected-face/leg constraints, exterior full-through hardware, component/foundation action distinction |
| beam-web-splice | Two discrete web plates, two FRP beams | Plate/body interactions and common-bolt interface methods; exact native reverse paths and eccentricity |
| wi-major-axis-moment-splice | Web plate pair and outer/split-inner flange plates; two FRP W/I beams | Native Slice 5 complete component moments, unequal plane demands and rational-method review boundaries |
| channel-major-axis-moment-splice | Back/opening web plates and four flange plates; two FRP Channels | Native Slice 6 reference/shear-center torsion and unequal web-face split; no invented warping resistance |
| wi-beam-concrete-wall-moment | Top/bottom flange angles and positive/negative web angles; FRP W/I beam; separate wall | Slice 5/7/8/native Stage 2.5A boundaries; four external wall groups; qualified out-of-plane attachment demand |
| wi-beam-frp-support-moment | Four discrete angles; FRP W/I beam + one of five receiving-support modes | Through-bolt/member-local/support-zone sources; no equal hollow-wall sharing or solid-section thin-plate assumption |
| angle-column-two-leg-moment-base | Two discrete angles on different column legs; FRP Angle column; separate foundation | Actual column reference/eccentricity, complete total foundation action, separate direct contact; no assumed 50/50 response |
| wi-rhs-srs-column-moment-base | TWO_X/TWO_Y/FOUR_XY active discrete angles; FRP W/I/RHS/SRS column | Retain centered 2×1 / 1×1 defaults, shared shanks, perpendicular clearance, signs and LAST VALID; source-qualified branch response, never automatic half/quarter sharing |

Shared native profile/mode families include Angle/Channel/W/I/flat plate/RHS/SRS where supported, all seven shared support targets, three nonempty Tee slot positions/combinations, W/I/RHS/SRS/Angle Single/Double shear bases and all nine current moment-base family/layout modes. Unsupported native schema choices (for example legacy round-hollow candidates) remain unsupported; registration does not activate them.

Member reinforcement is tracked separately as `FRP_REINFORCEMENT_RESTRICTED`. No current material-planning route manufactures a doubler or relabels one as a free connector plate; any future reinforcement-producing route needs an explicit canonical role and qualified-alternative policy.

## Native numerical and source boundaries

The planning endpoint builds the native preview, then derives IDs/roles from server-authored physical records. It executes no resistance and persists nothing. Shared aliases resolve atomically; placeholders are not counted as physical bolts. Readiness records and source hashes are not source approvals.

The provider registry delegates unchanged native inputs to actual FRP functions. Returned objects retain native values, warnings, statuses, qualifications and fingerprints; the adapter does not normalize numbers or generate another resistance result. The Slice 7 adapter covers source-present/source-absent native cases. SS316 dispatch always returns `PROVIDER_NOT_IMPLEMENTED`, with null capacity/utilization and no FRP fallback.

Plan identity is separately namespaced. It binds sorted physical assignments, role/form, grade/fabrication/method, selected source revision/content/domain and response signature; it does not alter a legacy engine's identity. Direct single-bolt previews have no legacy preview digest: their new plan geometry identity uses the existing native physical code-mapping fingerprint payload, not a claimed historical digest.

## Inherited Tee startup limitation — Classification B

`TEE_DEFAULT_GEOMETRY_HISTORICALLY_INVALID_AT_STAGE_3_2_FREEZE` is a geometry/default-product limitation, not a stainless source gap or a CME-1 regression. The actual Stage 3.2 tag `stage-3.2-tee-connection-freeze` has annotated object `17aaec64e72131a7030780f3c581e8c4dc1d19c0` and peeled target `d16b354732c90bf3bf7847c62be652c230a9f91e`. The actual frozen startup request, executed through its own frozen backend, returns HTTP 422 with native reason `OUTSIDE_SELECTED_LEG_SURFACE`; the current startup returns the same outcome. The API wraps this as `CANONICAL_TEE_MAPPING_INVALID` with the finite opposing broad-face message. CME-1 does not repair, bypass, mask or worsen it.

The revised browser classification is `HISTORICAL_DEFAULT_INVALID_GEOMETRY_PRESERVED`: Tee remains mounted/editable, its family/material policy remains discovered, primary members remain FRP-only, and SS316 remains `PROVIDER_NOT_IMPLEMENTED`. This is **not** a successful default preview or a qualification result. The existing valid U.S. Tee benchmark remains a separate native recovery fixture, not a replacement startup default. All other 14 selectable workspaces retain their normal browser gates. Any default geometry repair requires a separately controlled Tee successor.

The clarification is archived byte-exact in `docs/governance/FRP_MASTER_CONNECTION_CME1_TEE_HISTORICAL_LIMITATION_BROWSER_GATE_CLARIFICATION_R1.md` (SHA-256 `752322414CEBC4C7A1DEF0DDA21B9E912023FE8476CF7F54AAB2C7DB1E215631`). Dedicated backend and frontend `test_cme1_tee_historical_limitation.py` / `cme1TeeHistoricalLimitation.test.tsx` regressions exercise validation, readiness, rejection and existing-fixture recovery. The historical backend runs when the tag object is available; tagless verification checks the committed historical manifest and captured startup identities without fetching or claiming historical execution.

Before resuming, all 26 preserved CME-1 file hashes and the binary patch were verified. The saved unstaged patch SHA-256 is `89D27F8CB13B299FDC121A84BB0F9F738C0C9504B76193C8457718AB6F7DB969`; the empty staged patch is `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`. Both diagnosis checkouts were clean and all thirteen local/remote freeze-tag objects and targets matched. No Tee correction commit was created.

## Next controlled gates

CME-1 foundation acceptance does not accept full 316SS expansion. CME-2 must supply the missing normative/property/method authority and independent numerical benchmarks. CME-3 then activates **all applicable** family adapters in staged plate, angle, and Tee/fabricated batches, with material-dependent response and FRP/native regression evidence for each. Direct/reinforcement exceptions remain explicit. No automatic freeze or next-phase numerical implementation is authorized here.
