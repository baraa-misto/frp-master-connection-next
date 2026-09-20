# FRP Master Connection — Stage 4.1B Channel Major-Axis Moment Splice — Decision

## Decision

Proceed with **Stage 4.1B — Channel Beam Major-Axis Moment Splice** as the Channel successor to the frozen Stage 4.1A W/I moment splice.

The product uses:

- two identical, collinear, equally oriented unlipped FRP Channels;
- a positive beam-end gap;
- one back-face and one opening-face FRP web splice plate;
- one outer and one inner FRP splice plate on the top flange;
- one outer and one inner FRP splice plate on the bottom flange;
- common physical through-bolts through every Plate/Channel/Plate stack;
- accepted Calculation Slice 6 Channel centroid/shear-center/component-resultant authority;
- accepted local FRP, plate-body, and common-bolt resistance engines;
- controlled rational methods for the Channel-specific load path.

No W/I assumptions may be silently copied where the Channel centroid, web plane, or shear center differs.

## Accepted prerequisite

Calculation Slice 6 is accepted and controlling:

Commit:

`b275a647bbbc1786d169302f060402fbfb062aab`

Subject:

`feat: add Channel moment reference and resultant engine`

Hosted CI:

GitHub Actions run #95, latest attempt #6, 4/4 green.

Calculation Slice 6 supplies:

- exact Channel centroid;
- exact major/minor section properties;
- rational or explicit verified shear-center source;
- canonical centroid wrench;
- top/web/bottom component wrenches;
- transverse eccentricity ledger;
- generated centroidal torsion;
- web free torsion;
- exact six-component equilibrium.

Stage 4.1B shall consume those records and shall not recreate them in product orchestration.

## RC1 actions

Normal user actions:

- signed axial force `P_L`;
- signed major shear `V_V`;
- signed major-axis bending moment `M_T`.

Require zero / reject:

- minor shear;
- minor-axis bending moment;
- user torsion.

Generated torsion from the major-shear/shear-center reference remains mandatory and is not treated as user torsion.

## Channel orientation

Both Channels have identical orientation:

- web back face at negative side of the opening direction;
- opening toward `+T_CH`;
- Beam A and Beam B are collinear without mirroring one Channel.

Back-to-back or toe-to-toe Channels are not RC1.

## Physical splice topology

### Web

Two physical web splice plates:

1. `BACK_WEB_SPLICE_PLATE`
2. `OPENING_WEB_SPLICE_PLATE`

Every web bolt path:

`BACK_WEB_SPLICE_PLATE -> CHANNEL_WEB -> OPENING_WEB_SPLICE_PLATE`.

### Top flange

- one outer full-width plate;
- one inner centered strip.

Every top flange bolt path:

`TOP_OUTER_FLANGE_SPLICE_PLATE -> TOP_CHANNEL_FLANGE -> TOP_INNER_FLANGE_SPLICE_PLATE`.

### Bottom flange

- one outer full-width plate;
- one inner centered strip.

Every bottom flange bolt path:

`BOTTOM_OUTER_FLANGE_SPLICE_PLATE -> BOTTOM_CHANNEL_FLANGE -> BOTTOM_INNER_FLANGE_SPLICE_PLATE`.

Total FRP splice plates:

`6`.

## Channel flange inner-plate centering

The single inner plate on each flange is centered on the actual Channel flange-region centroid:

`T_inner_plate_centroid = b_f/2`.

This preserves the Slice 6 transverse coordinate of the flange longitudinal resultant.

The inner plate shall fit entirely on the open flange surface without positive-volume interference with the web.

For RC1:

`b_inner <= b_f - 2 t_w`.

The default uses equality.

No inner plate is placed against the web centroid or shifted toward the flange tip.

## Flange wrench decomposition

Reuse the accepted method:

`RATIONAL_BALANCED_FLANGE_FACE_COUPLE_DECOMPOSITION_RC1`.

For each top/bottom flange:

`F_o + F_i = N_f`

`e_o F_o + e_i F_i = m_T,f`

where the offsets are measured in `V_CH` from the authoritative Channel flange-region centroid.

The actual outer and inner plate centroid force lines control.

Because both flange branch force lines remain at the exact transverse coordinate `T_f`, this decomposition preserves the Slice 6 transverse eccentricity contribution:

`M_V,f=(T_f-T_c)N_f`.

No separate artificial minor-axis moment is introduced.

## Channel web-face branch decomposition

Introduce:

`RATIONAL_CHANNEL_WEB_FACE_SHEAR_CENTER_COUPLE_DECOMPOSITION_RC1`.

The Slice 6 web wrench at the Channel web centroid contains:

- longitudinal force `N_w`;
- major shear `V_w`;
- local major-axis moment `m_T,w`;
- free torsion `m_L,w`.

The identical back/opening web splice plates are symmetric about the Channel web centroid.

Assign:

`N_back=N_open=N_w/2`

`m_T,back=m_T,open=m_T,w/2`.

Let:

`e_back=T_back-T_w < 0`

`e_open=T_open-T_w > 0`.

Solve the vertical branch forces exactly:

`Q_back + Q_open = V_w`

`-e_back Q_back - e_open Q_open = m_L,w`.

Therefore:

`Q_back=(m_L,w + e_open V_w)/(e_open-e_back)`

`Q_open=V_w-Q_back`.

The back/opening branch wrenches, shifted to the web centroid, shall recover the complete Slice 6 web wrench exactly.

No 50/50 web-shear assumption is allowed.

## Meaning of generated torsion

For RC1, the centroidal torsion is a reference-generated wrench caused by representing major shear through the Channel shear center and then shifting the equivalent wrench to the centroid.

Stage 4.1B physically closes that reference effect with the unequal back/opening web-face shear couple.

It does not claim a user-applied Saint-Venant torsion resistance design.

Open-section warping, connection-local distortion, unequal-face contact, and torsional stiffness remain mandatory engineering-review / Section 2.3.2 qualification subjects.

## Rational Channel web face sublayers

Introduce:

`RATIONAL_CHANNEL_WEB_FACE_SUBLAYER_TRANSFER_RC1`.

For local FRP connection failure-path verification only, represent the Channel web as two rational face sublayers:

- back-face effective thickness `t_w/2`;
- opening-face effective thickness `t_w/2`.

The back sublayer receives the actual back branch group demand.

The opening sublayer receives the actual opening branch group demand.

Both retain:

- actual web height;
- actual material axes;
- actual complete bolt grid;
- signed loaded-edge direction.

The physical Channel web remains one member.

This rational sublayer model preserves the unequal-face demand needed to transfer the shear-center couple.

## Flange face sublayers

Reuse:

`RATIONAL_BALANCED_FLANGE_FACE_SUBLAYER_TRANSFER_RC1`.

For local flange connection checks only:

- outer-face effective thickness `t_f/2`;
- inner-face effective thickness `t_f/2`;
- outer face receives `F_o`;
- inner face receives `F_i`;
- actual Channel flange geometry/material axes/bolt grid are retained.

The physical flange remains one member.

## Common-bolt unequal-plane shear

Reuse:

`RATIONAL_ASYMMETRIC_TWO_PLANE_COMMON_BOLT_SHEAR_RC1`.

For both flange and web common bolts:

- actual demand on physical plane 1 comes from the first plate branch;
- actual demand on physical plane 2 comes from the second plate branch;
- the planes are checked independently;
- governing physical bolt utilization is the maximum plane utilization.

No blind equal-plane assumption.

No blind `2 × single-plane capacity`.

## Web plate body design

Each web splice plate is evaluated independently using its own:

- longitudinal force;
- vertical shear;
- local major-axis moment;
- exact beam-side group-reference translations.

Reuse:

`RATIONAL_LINEAR_ORTHOTROPIC_SPLICE_PLATE_BODY_INTERACTION_RC1`

and:

`RATIONAL_SIMPLY_SUPPORTED_CLEAR_BODY_PANEL_RC1`

with Calculation Slice 4 pure-mode plate strengths.

The back and opening web plates may have substantially different governing utilization because their shear-center branch forces are intentionally unequal.

## Flange plate body design

Each flange splice-plate branch carries longitudinal force only in RC1 after the complete flange wrench has been resolved into outer/inner force lines.

For clear plate bodies:

- tension -> Calculation Slice 4 longitudinal tension;
- compression -> Calculation Slice 4 longitudinal compression/buckling;
- rational clear-body panel mapping retained.

Outer and inner flange plates are separate physical components.

## Local FRP connection checks

Reuse accepted local FRP engines where applicable for:

- pin bearing;
- net tension;
- shear-out;
- cleavage;
- block shear / accepted local failure-path logic.

Apply independently to:

- back web plate;
- opening web plate;
- rational back Channel-web face sublayer;
- rational opening Channel-web face sublayer;
- top outer flange plate;
- top inner flange plate;
- bottom outer flange plate;
- bottom inner flange plate;
- rational outer/inner Channel-flange face sublayers.

No new strength equation is invented.

## Bolt-axis action / prying boundary

All supported RC1 branch actions are in the respective plate planes.

Authoritative bolt-axis force:

`0`.

Do not invent:

- bolt tension;
- prying;
- pull-through demand;
- secondary bolt bending resistance;
- torsional stiffness.

Actual out-of-plane deformation/contact and open-section connection distortion remain qualification/review items.

## Exact whole-connection equilibrium

At the Channel centroid, the physical splice branches shall recover exactly:

- `P_L`;
- `V_V`;
- `M_T`;
- generated `M_L,C`;
- zero minor shear;
- zero minor-axis moment.

The individual nonzero Slice 6 transverse eccentricity contributions shall remain traceable.

No residual force or moment may be discarded.

## Result status

Precedence:

1. invalid/rejected input;
2. any required evaluated failure -> `FAIL`;
3. required source/method unavailable -> `NOT_EVALUATED`;
4. all required numerical component-strength checks pass ->
   `PASS_WITH_RATIONAL_METHOD_REVIEW_REQUIRED`.

Ordinary unqualified `PASS` is prohibited.

## Qualification / classification

Always:

`RATIONAL_METHOD_ENGINEERING_REVIEW_REQUIRED=true`

`CHANNEL_MOMENT_SPLICE_CONNECTION_QUALIFICATION=REQUIRED_2_3_2`

`MOMENT_CONNECTION_STIFFNESS_CLASSIFICATION=NOT_EVALUATED`

`MOMENT_ROTATION_CAPACITY=NOT_EVALUATED`

`FULL_STRENGTH_CLASSIFICATION=NOT_EVALUATED`

`OPEN_SECTION_WARPING_CONNECTION_RESPONSE=NOT_EVALUATED`.

## Mandatory disclaimer

Backend ID:

`CHANNEL_MAJOR_AXIS_MOMENT_SPLICE_RATIONAL_DESIGN_DISCLAIMER_RC1`.

Controlled meaning:

Stage 4.1B uses exact Channel centroid/section geometry plus the accepted Calculation Slice 6 rational-or-explicit shear-center reference and component-resultant engine. It physically resolves flange-region force/local-moment wrenches into outer/inner longitudinal force lines and resolves the web shear-center/free-torsion wrench into unequal back/opening web-face branch forces. Local/code-based FRP and bolt strengths are used where applicable, with inherited rational plate-body and face-sublayer methods. ASCE/SEI 74-23 does not prescriptively qualify a moment-resistant open-section FRP Channel beam splice. The engineer of record shall review the shear-center source, structural-analysis reference convention, open-section warping/distortion, relative stiffness and contact assumptions, unequal web-face load transfer, bolt/plate restraint, and Section 2.3.2 qualification. Rotational stiffness, rotation capacity, full-strength classification, and open-section warping connection response are not established.

## Frozen-family boundary

All Stage 2.3 / 3.2 / 3.3 / 3.4 / 3.5 / 3.6 / 3.7 / 4.1A freeze tags remain immutable.

Calculation Slice 5 and Calculation Slice 6 remain exact.

No historical W/I or shear product behavior changes.

## Future scope

Not Stage 4.1B RC1:

- user torsion;
- minor-axis moment;
- minor shear;
- lipped Channels;
- unequal-flange Channels;
- back-to-back Channels;
- unequal beams;
- outer-only flange splice;
- flange plates shifted off the flange centroid;
- open-section warping strength;
- connection stiffness / moment-rotation classification.

**END OF STAGE 4.1B CHANNEL MAJOR-AXIS MOMENT SPLICE DECISION**
