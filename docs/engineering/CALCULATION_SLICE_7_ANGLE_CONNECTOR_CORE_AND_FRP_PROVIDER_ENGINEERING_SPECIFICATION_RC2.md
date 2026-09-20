# FRP Master Connection — Calculation Slice 7 — Material-Neutral Angle Connector Core + FRP Resistance Provider — Engineering Specification RC2

## 1. Status

Controlled shared calculation authority — RC2.

RC2 supersedes the unexecuted RC1 package before implementation.

Accepted baseline:

`18419606f4143f27240a39374b25e294a9f39253`

Expected commit count before implementation:

`103`.

Expected hosted Stage 4.1 family-freeze CI:

GitHub Actions run #98, 4/4 green.

## 2. Architecture

Separate two immutable layers:

### Core

`ANGLE_CONNECTOR_INTERFACE_WRENCH_CORE_RC1`

Material-neutral.

### Resistance provider

`ANGLE_CONNECTOR_RESISTANCE_PROVIDER_RC1`

Material-specific.

Only the FRP provider is implemented in RC2.

## 3. Core geometry

Support one L-angle connector with:

- length `L_A`;
- member-connected leg width `b_M`;
- support-connected leg width `b_S`;
- thickness `t_A`;
- inside heel radius `r_i`;
- exact member-side reference `r_M`;
- exact support-side reference `r_S`;
- heel reference `r_H=(0,0,0)`.

Core validates geometry but performs no material resistance calculation.

## 4. Core frame

Right-handed:

- `A_A`: connector extrusion axis;
- `B_A`: heel toward member-connected leg;
- `C_A`: heel toward support-connected leg.

Require:

`A_A × B_A = C_A`.

Material-specific axis interpretation belongs to the provider.

## 5. Core wrench input

At `r_M`, accept complete signed wrench:

`F_M=(F_A,F_B,F_C)`

`M_M=(M_A,M_B,M_C)`.

No component discarded.

## 6. Exact heel transport

`F_H=F_M`

`M_H=M_M+(r_M-r_H)×F_M`.

## 7. Exact support handoff

Member action represented at `r_S`:

`F_M@S=F_M`

`M_M@S=M_M+(r_M-r_S)×F_M`.

Connector-on-support handoff equals this shifted member action.

Support-on-connector reaction is the exact negative.

## 8. Exact equilibrium

Shift support reaction to the heel and require exact zero force and zero moment.

No tolerance residual dumping.

## 9. Core fingerprint

Core fingerprint includes:

- geometry;
- frame;
- references;
- input wrench;
- heel wrench;
- support handoff;
- exact equilibrium.

It excludes:

- connector material family;
- material strengths;
- resistance factors;
- source package;
- provider result.

This separation is mandatory so future 316SS support does not change the core demand identity.

## 10. Provider dispatch

Input provider key is separate from the core.

RC2 registry:

`FRP -> FRP_ANGLE_CONNECTOR_RESISTANCE_PROVIDER_RC1`

Unsupported provider keys fail closed:

`CONNECTOR_RESISTANCE_PROVIDER_NOT_IMPLEMENTED`.

No silent FRP fallback.

## 11. FRP provider applicability

FRP provider requires:

- pultruded FRP L-angle;
- homogeneous accepted FRP material architecture;
- connector geometry compatible with the core record;
- source-controlled FRP properties;
- qualified source package for nonzero full-wrench body strength.

## 12. FRP material axes

Provider interprets:

- `LW || A_A`;
- member-leg in-plane transverse direction along `B_A`;
- support-leg in-plane transverse direction along `C_A`;
- leg through-thickness directions normal to each physical leg.

## 13. FRP instep shear

Method:

`ASCE_74_23_EQ_8_15_CLIP_ANGLE_INSTEP_SHEAR_RC1`.

Backend-derived effective instep length:

`l_sp=L_A-sum(physical end reliefs intersecting continuous instep)`.

Nominal:

`R_sh,sp=l_sp t_A F_sh`.

Design:

`phi R_sh,sp=0.70 l_sp t_A F_sh`.

Demand:

`V_instep=|F_A,H|`.

Do not use this equation for other force or moment components.

## 14. FRP qualified package

Method:

`QUALIFIED_FRP_ANGLE_ASSEMBLY_FULL_WRENCH_ENVELOPE_RC1`.

Package binds exactly to:

- core geometry fingerprint;
- FRP material/property fingerprint;
- member-side fastener layout fingerprint;
- support-side fixture/anchor layout fingerprint;
- reference/frame fingerprint;
- source version.

No interpolation.

## 15. Signed FRP design strengths

Qualified package supplies positive/negative design strengths for:

- `F_A`;
- `F_B`;
- `F_C`;
- `M_A`;
- `M_B`;
- `M_C`.

Missing demanded sign -> fail closed.

## 16. FRP qualified coverage

As demanded, package must explicitly cover:

- angle body;
- heel/instep;
- member leg;
- support leg;
- out-of-plane response;
- through-thickness/delamination;
- contact;
- prying effect on connector;
- secondary bolt-bending effect on connector;
- combined interaction.

## 17. FRP interaction

Method:

`RATIONAL_LINEAR_QUALIFIED_ANGLE_ASSEMBLY_INTERACTION_RC1`.

Only execute when the qualified package explicitly authorizes it.

For each signed component:

`D_j+=max(D_j,0)`

`D_j-=max(-D_j,0)`.

`U_Q=sum(D_j+/R_j+ + D_j-/R_j-)`.

Exact boundary `U_Q=1` passes.

## 18. FRP source/result states

Provider states include:

- `INVALID`;
- `SOURCE_REQUIRED`;
- `SOURCE_NOT_APPLICABLE`;
- `NOT_EVALUATED`;
- `FAIL`;
- `PASS_WITH_QUALIFIED_SOURCE_AND_ENGINEERING_REVIEW_REQUIRED`.

Ordinary unqualified PASS is prohibited.

## 19. Support handoff boundary

Core always returns exact connector-on-support group wrench.

No material provider calculates anchor or concrete capacity.

FRP provider may declare prying/contact coverage but shall not fabricate individual anchor reactions unless a separately accepted contract provides them.

Otherwise:

`FLEXIBLE_FIXTURE_PRYING_DISTRIBUTION_EXTERNAL_REQUIRED`.

## 20. Future 316SS provider boundary

No structural stainless resistance is implemented.

Do not add:

- stainless Fy/Fu tables;
- stainless plate/angle resistance;
- stainless prying;
- stainless bolt bearing;
- AISC stainless equations;
- user-selectable 316SS connector material.

Future provider shall plug into the same core/provider interface.

## 21. Default core benchmark

Geometry:

- `L_A=8 in`;
- `b_M=4 in`;
- `b_S=4 in`;
- `t_A=0.5 in`;
- `r_i=0.25 in`.

References:

- `r_H=(0,0,0) in`;
- `r_M=(0,2.5,0) in`;
- `r_S=(0,0,2.0) in`.

Input at `r_M`:

`F=(4,6,-1) kip`

`M=(1.5,-0.5,1.0) kip-in`.

Expected heel:

`F=(4,6,-1) kip`

`M=(-1,-0.5,-9) kip-in`.

Expected connector-on-support:

`F=(4,6,-1) kip`

`M=(11,-8.5,-9) kip-in`.

## 22. FRP test-only benchmark

Use test-only adjusted:

`F_sh=8 ksi`.

With `l_sp=8 in`, `t_A=0.5 in`, `phi=0.70`:

`phi R_sh,sp=22.4 kip`.

Instep utilization for default `F_A=4 kip`:

`0.17857142857142857142857142857142857142857142857142857142857142857142857142857143`.

## 23. Test-only qualified FRP envelope

Use the same test-only signed design strengths from the superseded RC1 golden solely for arithmetic verification.

Expected default:

`U_Q=0.92666666666666666666666666666666666666666666666666666666666666666666666666666667`.

Never create a production default qualified source.

## 24. Provider-neutral versus provider-specific fingerprint proof

For identical geometry/references/wrench:

- core fingerprint is identical regardless of provider selection;
- FRP provider fingerprint/result is separate;
- unsupported future provider does not alter the core fingerprint.

This is a mandatory golden/test requirement.

## 25. U.S./SI equivalence

Equivalent inputs preserve:

- core geometry;
- references;
- heel/support wrenches;
- equilibrium;
- core fingerprint;
- FRP instep result;
- FRP qualified interaction;
- FRP provider fingerprint.

## 26. Frontend/product boundary

Frontend production changes:

`0`.

Physical Stage 4.2 product:

not begun.

## 27. Controlled golden coverage

Companion RC2 golden shall contain exactly G1-G72 covering:

- core contract;
- provider boundary;
- exact wrench transport;
- exact equilibrium;
- core fingerprint provider independence;
- FRP instep shear;
- FRP source binding;
- signed strengths;
- coverage/interaction;
- pass/fail/source states;
- unsupported 316SS provider behavior;
- external support handoff;
- U.S./SI;
- no frontend/product work;
- all freeze regressions.

## 28. Frozen invariance

Require exact:

- Stage 4.1 family freeze;
- Stage 4.1A freeze;
- Calculation Slices 5 and 6;
- all Stage 2.3 through Stage 3.7 freezes;
- historical fingerprints.

## 29. Acceptance boundary

RC2 is accepted only if:

- generic core contains no FRP-specific resistance assumption;
- FRP provider is isolated behind the provider contract;
- future unsupported provider fails closed;
- core fingerprint remains provider-independent;
- exact wrench transport/equilibrium closes;
- Equation 8-15 stays in its FRP applicability;
- complete FRP body strength requires qualified source data;
- no 316SS resistance is implemented;
- full QA/object-isolated/hosted CI pass.

**END OF CALCULATION SLICE 7 ANGLE CONNECTOR CORE AND FRP PROVIDER ENGINEERING SPECIFICATION RC2**
