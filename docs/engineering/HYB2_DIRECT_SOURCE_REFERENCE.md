# Direct L4/I8 source and review status - HYB2-D1-R1

R2 supplements this preserved R1 record: see `HYB2_DIRECT_R2_CORRECTED_LTV.md`.
R2 confirms the Xb edge datum and adds a separate owner COS reference stream
and actual-hole ledger. Earlier SIN formulas remain historical; physical
effective fracture endpoints remain unreconciled. R2 governs current interpretation.

## Source and domain

Source XLSX SHA256: 1dcfa90eb1e33101e350b41760b13f6d2f7f87225191e11145362c35f8121e83.
Original private workbook and metadata stay outside Git. The earlier beam and Clip Tee
sources, routines and delivered archives remain separate.

L4x4x0.5 / I8x4x0.375, one-sided direct contact, two 0.5-in 316SS single-shear bolts,
no reinforcement. Phi=30.9 degrees; d_span=2 in; Xc=1 in; Xb=1-.1875-.375=.4375 in.
P=91.55 lbf, V=13.4 lbf, entered M=0. Polyester 100F Ts=.85; source listed/SF4 values.
Eight source summaries reproduce seven unique comparisons; D46 and D159 are the same
bolt group. Ten geometric outputs are derived, not cached. D34=.04079661668589,
D46/D159=.01847954299921, D75=.10089213623933, D121=.01810810844621,
D146=.07316775599129, D205=.05956412716101, D239=.04039767880103.

Bounded variations: acute angle, positive dimensions/thickness, contained holes, changed
spacing/Xb/Xc, supplied polyester temperature points 75/90/100/125/135/150F and positive
P/V magnitudes in source directions. No interpolation, reversal, reinforcement or
finite-moment structural method. Owner reports satisfactory field use; qualification
or an independently documented testing envelope is not supplied.

## Coordinate and path mapping

x right, y up; brace u=(cos(phi),-sin(phi)), v=(sin(phi),cos(phi)). Bolts at
(0,+/-d_span/(2cos(phi))); vertical spacing=2.33082600938364968... in. d_span is not
bolt diameter. The same centers serve both members. Candidate brace cut x=-Xb;
column near/far flange edges x=Xc and Xc-4. Brace side strip retains supplied L61,
with opposite edge distance=leg-d_span-L61. Nominal holes are explicit .563-in
geometry witnesses absent from source resistance operands; no deduction is invented.
Fillet, washer/head/nut/tool access and full physical-model adoption are not established.

P paths reach proposed boundaries at Xb/cos(phi) and Xc/cos(phi); column V path=Xc/sin(phi).
Global P transverse length is the actual vertical spacing. Source V tensile length is
d_span*sin(phi), which differs from the vertical-pair projection along u
(spacing*sin(phi)=d_span*tan(phi)). Its actual fracture segment/calibration and Xb's
fabrication datum remain Q3. The .375 in Xb's expression does not replace actual .5
brace thickness. Source lengths are center-derived, not established net areas.

A separate brace-aligned rotation about the same centroid preserves spacing and
boundary datums: x=+/-d_span/2, y=-/+spacing*sin(phi)/2. Fresh cut distances are
-.5625/1.4375 in and near column distances 2/0 in. That saved rotation does not fit.
No resized boundary, moved source input or inherited structural result is used.

## Arithmetic corrections and demand boundary

Historical E46 stays literal OK; corrected status follows D46, including overload.
Historical R50=2*blank R47 remains a distinct witness; corrected link uses R49.
The independent planar equal-stiffness pair equation is qx=Fx/2-M*y/(2h²), qy=Fy/2
at y=+/-h. Pure couple, reversal, force/moment sums and existing reference transport
are tested. This mathematical witness does not adopt a FRP transfer law or the source
simultaneous scalar P/V envelope. Unsupported moments/signs/out-of-plane components
remain in original action ledgers and affected supplemental checks are withheld.

Source D31/D221 retain Ts twice. Actual source CW properties and stale labels are
traced. No current ASCE factors/materials/F593 values are substituted. Fixed source
316SS included-thread allowable=12.75 ksi. Inactive #REF/reinforcement branches stay
inactive. No old-source storm relief is active in this direct source.

## Separate status dimensions

The inactive hybrid adapter separates current applicable outcomes from reference
comparisons, analytical coverage, native status and qualification. Scoped evaluated
PASS/FAIL never becomes blanket YELLOW from unrelated notes. Zero checks cannot pass.
Reference work has a neutral heading, no actual design UR and no adopted coverage.
The executive summary names omissions, material limits and qualification. Current
partial/reference reports are permitted; stale exports are refused. Existing native
signed/account/currentness authority and public routes are unchanged.

All 17 actual mandatory mechanisms have source-use records per alignment (34 total).
The source advances receiving-column local/global arithmetic; actual physical mapping
adoption remains pending. A synthetic joint-release test covers multiple mechanisms
with one ratio/capacity and cannot install real coverage. No caller adoption flag exists.
The supplied R1-S01 through R1-S14 tests exercise both wording and underlying state.

## Verification scope

The additive governance update retains exact P2/C82/B7 workflow reconstruction, updates
the backend count and adds four report fixtures through the existing inert harness.
Configured coverage scope, dependency pins and all 53/173 controls remain unchanged.
The renderer prints immutable records and performs no engineering evaluation. Final
local/hosted evidence is external. PR1 stays open/draft/unmerged. C13, Section 2.3.2,
method adoption and owner acceptance remain open. No public activation or release.
