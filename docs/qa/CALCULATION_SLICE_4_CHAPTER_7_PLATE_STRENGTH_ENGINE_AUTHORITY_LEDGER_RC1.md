# FRP Master Connection — Calculation Slice 4 — ASCE/SEI 74-23 Chapter 7 Pure-Mode FRP Plate Strength Engine — Authority Ledger RC1

## Authority purpose

Calculation Slice 4 supplies the missing shared Chapter 7 plate-strength calculation seam required by the revised Stage 3.6B rational web-splice body method.

It is backend engineering authority, not a product UI stage.

## Normative tension authority

Implement:

- Section 7.5 longitudinal tension using Equation 7-12;
- Section 7.5 transverse tension using Equation 7-13;
- tension resistance factor `phi=0.65`;
- caller-provided time-effect factor.

Effective net area per unit width is supplied by geometry/caller.

No connection-hole geometry is recomputed inside the engine.

## Normative compression authority

Implement:

- Section 7.6 longitudinal material rupture Equation 7-15;
- transverse material rupture Equation 7-16;
- longitudinal orthotropic buckling Equations 7-17 through 7-19;
- governing longitudinal compression as the lower rupture/buckling nominal strength;
- resistance factor `phi=0.70`;
- combined longitudinal/transverse compression buckling Equations 7-20 through 7-22 for `0.3 <= xi_LT <= 1.0`.

No extrapolation outside the Section 7.6.4 xi range.

Pure transverse compression stability is not invented.

## Normative shear authority

Implement:

- Section 7.7 in-plane shear rupture Equation 7-24;
- shear buckling Equations 7-25 through 7-27;
- exact piecewise eta branch;
- governing lower rupture/buckling nominal strength;
- resistance factor `phi=0.70`.

## Section 2.4 boundary

All characteristic strengths/moduli supplied to Slice 4 are already adjusted by the existing property/end-use authority.

Slice 4 shall not apply those adjustments again.

The existing time-effect factor is supplied separately and applied once.

## Buckling boundary provenance

For longitudinal compression:

- normative `k_cr=1.0`;
- commentary narrow/short-plate cautions are recorded as advisories;
- normative equation is not modified.

For in-plane shear:

- normative Equation 7-26 is used;
- commentary `a<b` conservatism is recorded;
- no commentary axis-swap alternative is introduced in RC1.

## Stage 3.6B relation

Stage 3.6B may use Calculation Slice 4 as the source of:

- longitudinal tension design strength;
- longitudinal compression governing design strength;
- in-plane shear governing design strength.

Stage 3.6B's rational combined normal/shear interaction remains a separate project-specific engineering authority.

No Stage 3.6B combined interaction equation is introduced by Slice 4.

## Historical/frozen boundary

Stage 3.6A remains exact.

Stage 3.5 and earlier frozen-family tags/fingerprints remain immutable.

## Reporting

Slice 4 returns equation and property provenance suitable for later report traceability.

It creates no report generator and no frontend presentation.

**END OF CALCULATION SLICE 4 CHAPTER 7 PLATE STRENGTH ENGINE AUTHORITY LEDGER RC1**
