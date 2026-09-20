# ASCE 74-23 Single-Bolt Equation Catalog

| Control item | Value |
|---|---|
| Stage | 2.1A documentation only |
| Standard | ASCE/SEI 74-23, Chapter 8 |
| Errata | Erratum 1, effective 2026-01-13; Chapter 8 unaffected |
| Execution status | Prohibited in Stage 2.1A |
| Numerical implementation | Implemented separately by the controlled Stage 2.1B numerical engine |

## Copyright and use boundary

This original project catalog records only the user-authorized equation set, compact
variable relationships, original implementation explanations, and source locators
needed for concordance and Stage 2.1B traceability. It does not reproduce an ASCE table,
figure, commentary, examples, or extended licensed text. The licensed PDFs are not
tracked.

Every expression below is non-executable in Stage 2.1A. Production code contains no
resistance, capacity, utilization, or physical-input `PASS`/`FAIL` evaluation.

## 1. General factor sequence

For a future applicable FRP limit state:

\[
R_d=\lambda\,\phi\,C_{lap}\,C_{\Delta}\,R_{n,end-use}
\]

The planned factor identities remain separate. Stage 2.1A stores their provenance and
applicability but does not assemble or multiply them.

Source references: ASCE/SEI 74-23 Sections 2.4.2, 2.4.4, and 8.3.1 as applicable.

## 2. Bolt body area

\[
A_b=\frac{\pi d^2}{4}
\]

This future geometric input supports metallic bolt checks. It is intentionally absent
from production calculation functions in Stage 2.1A.

Source context: Chapter 8 bolt-strength equations.

## 3. Pure bolt tension or shear — Equation 8-2 basis

\[
R_{bt}=F_n A_b
\]

Future design resistance:

\[
R_{d,bt}=\phi_b R_{bt},\qquad \phi_b=0.75
\]

For a future ASTM F593 implementation:

\[
F_{nv}=0.60F_{nt}\quad\text{when threads are excluded from the shear plane}
\]

\[
F_{nv}=0.50F_{nt}\quad\text{when threads are included in the shear plane}
\]

The locked F593 preset has no `Fnt`; therefore the corresponding Stage 2.1A plan is
`SOURCE_DATA_PENDING`. A synthetic explicit-`Fnt` fixture can be ready without
executing these expressions.

Source reference: ASCE/SEI 74-23 Section 8.3.2.1, Equation 8-2.

## 4. Combined bolt tension and shear — Equations 8-3a/b basis

\[
R_{bt}=F'_{nt}A_b
\]

\[
F'_{nt}=1.3F_{nt}-\frac{F_{nt}}{\phi_bF_{nv}}f_v
\]

with the bound

\[
F'_{nt}\le F_{nt}
\]

The approved first-slice future shear-stress model is

\[
f_v=\frac{V_u}{n_sA_b}
\]

and the future design tension resistance is

\[
R_{d,bt}=\phi_bF'_{nt}A_b
\]

Stage 2.1A retains the demand and shear-plane thread/count metadata only.

Source reference: ASCE/SEI 74-23 Section 8.3.2.1, Equations 8-3a/b.

## 5. Pull-through — Equations 8-4a/b

\[
R_{tt,1}=0.5\pi d_wtF_{sh,tt}
\]

\[
R_{tt,2}=0.4\pi d_wtF_{sh,int}
\]

\[
R_{tt}=\min(R_{tt,1},R_{tt,2}),\qquad \phi_{tt}=0.50
\]

Future use of an in-plane shear characteristic as `Fsh,tt` requires an approved source
basis permitting that treatment. The locked ICE discrete pull-through values are not
substituted for these branches. In Stage 2.1A, zero explicit bolt-axis/prying demand is
not applicable; positive explicit demand requires washer and material inputs.

Source reference: ASCE/SEI 74-23 Section 8.3.2.2, Equations 8-4a/b.

## 6. Pin bearing — Equations 8-5/8-6

\[
R_{br}=td\,\zeta F_{br,\theta}
\]

\[
\zeta=1.0\quad\text{when threads are excluded from the FRP bearing surface}
\]

\[
\zeta=0.60\quad\text{when threads are included in the FRP bearing surface}
\]

Approved property selection is

\[
F_{br,\theta}=F_{br,L}\quad\text{for }\theta\le5^\circ
\]

\[
F_{br,\theta}=F_{br,T}\quad\text{for }5^\circ<\theta\le90^\circ
\]

Exactly 90 degrees is included under engineer interpretation
`TRANSVERSE_ENDPOINT_INCLUDED`. The ICE development plan records future
`phi_br = 0.60` metadata with `ENGINEERING_REVIEW_REQUIRED`; it cannot yield an
ordinary qualified pass.

Source reference: ASCE/SEI 74-23 Section 8.3.2.3, Equations 8-5 and 8-6.

## 7. Single-bolt net-section tension — Equations 8-7a/b

\[
R_{nt}=\frac{(w-d_n)tF_{t,i}}{K_{nt,i}},\qquad \phi_{nt}=0.45
\]

\[
S_{pr}=\frac{w}{d}
\]

\[
K_{nt,i}=C_i\left[S_{pr}-1.5\left(\frac{S_{pr}-1}{S_{pr}+1}\right)^\Theta\right]+1
\]

\[
\Theta=1.5-0.5\frac{w}{e_1}\quad\text{when }\frac{e_1}{w}\le1
\]

\[
\Theta=1\quad\text{when }\frac{e_1}{w}\ge1
\]

For a future pultruded-shape implementation, `Ci = 0.50` for both longitudinal and
transverse loading. For pultruded plate material, `Ci = 0.40` longitudinal and `0.50`
transverse. The mapped width is

\[
w=e_3+e_4
\]

Stage 2.1A supplies `w` only for the three approved printed side-distance cases and
returns unsupported for unequal uncapped sides.

Source reference: ASCE/SEI 74-23 Section 8.3.2.4, Equations 8-7a/b.

## 8. Shear-out — Equation 8-8

\[
R_{sh}=1.4\left(e_1-\frac{d_n}{2}\right)tF_{sh},\qquad \phi_{sh}=0.50
\]

The plan applies to in-plane tension or compression when required inputs exist. The
Stage 2.1A geometry planner never grants the perpendicular-return-element exemption
automatically; a possible condition is reported as not credited.

Source reference: ASCE/SEI 74-23 Section 8.3.2.5, Equation 8-8.

## 9. Single-bolt cleavage — Equations 8-9a/b

For tensile force parallel to LW:

\[
R_{cl,a}=0.15\left[(2e_2-d_n)F_{t,L}+2e_1F_{sh}\right]t,
\qquad \phi_{cl,a}=0.50
\]

When `e1/d < 4`:

\[
R_{cl,b}=\left(\frac{10}{9}-\frac{4}{9}\frac{d_n}{e_1}\right)^2R_{br},
\qquad \phi_{cl,b}=0.50
\]

When `e1/d >= 4`:

\[
R_{cl,b}=R_{br}
\]

using the bearing resistance factor. A future governing design resistance uses the
lesser factored branch. Compression and exactly perpendicular tension are not
applicable; oblique tension is unsupported; no interpolation is authorized.

Source reference: ASCE/SEI 74-23 Section 8.3.2.6, Equations 8-9a/b.

## 10. Geometry factor

\[
C_\Delta=\frac{s}{s_{min}}\quad\text{when }s<s_{min}
\]

\[
C_\Delta=1.0\quad\text{otherwise}
\]

The one-bolt/one-row slice has no pitch and stores planning value `1.0`. No multirow
pitch-strength implementation exists.

Source reference: ASCE/SEI 74-23 Section 8.3.1.

## 11. Single-lap factor

\[
C_{lap}=0.60
\]

for future applicable in-plane FRP bearing, net-tension, shear-out, and cleavage
strengths in a single-lap configuration. It does not apply to metallic bolt strength
or pull-through. Double lap stores `1.0` metadata. No factor is applied in Stage 2.1A.

Source reference: ASCE/SEI 74-23 Section 8.3.1.

## Stage boundary

This Stage 2.1A catalog remains the non-executable source-locator record. Stage 2.1B
separately authorizes and implements the bounded equations, factor assembly,
resistance, utilization, benchmark reproduction, and physical-input comparison in
`SINGLE_BOLT_NUMERICAL_ENGINE_SPECIFICATION.md`. The catalog itself remains data-only
and is not imported by production calculation code.
