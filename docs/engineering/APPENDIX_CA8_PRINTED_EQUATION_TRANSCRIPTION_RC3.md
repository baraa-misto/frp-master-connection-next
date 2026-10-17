# Printed Appendix CA8.3.3 transcription

Authority: licensed ASCE/SEI 74-23, PDF pages 112-113 (printed pages 97-98). The source pages were visually inspected before implementation; OCR was not used as sole authority. Source SHA-256: A7127E37572D5D625C5F338FFB9A1D2D53F396897AFB26E0B4698A0131FE65BC. Source images remain private and are excluded from this package.

| Equation | Direction | Bolts across width | PDF/printed page | Exact grouping |
|---|---|---:|---|---|
| CA8-2 | L | 1 | 112/97 | [1 + CL*(Spr - 1.5*((Spr-1)/(Spr+1))*Theta)] / (w/d - 1) |
| CA8-4 | L | 2 or 3 | 113/98 | [1 + CL*(Spr - 1.5*((Spr-1)/(Spr+1))*Theta)] / [w/(n*d) - 1] |
| CA8-7 | T | 1 | 113/98 | [1 + CT*(Spr - 1.5*((Spr-1)/(Spr+1))*Theta)] / (w/d - 1) |
| CA8-9 | T | 2 or 3 | 113/98 | [CT*(Spr - 1.5*((Spr-1)/(Spr+1))*Theta) + 1] / [w/(n*d) - 1] |

Theta is a multiplier immediately following the ratio, inside the coefficient's parentheses. It is not an exponent. Spr=w/d for n=1; Spr=g/d for n=2/3. Theta=1.5-0.5*(spacing/e1) for e1/spacing<=1; otherwise Theta=1. Printed branches overlap at equality, where both give exactly one. The existing deterministic <= branch is retained, using exact physical Decimal comparison without an epsilon.

Registered Erratum 1 (13 January 2026, SHA-256 5B58E842DA9025934D12EB386C416E94CB3B53999B21F59B0606F2B09D9DE550) changes Section 5.2.3.5 terminology and does not amend these Appendix equations. No claim is made that the official publisher site was accessible during this task.

Scope: multiplication correction only. Cop and Kop remain unchanged. The already documented RC2 conservative transverse-plate CT=0.50 policy is retained and exposed in the successor trace; the printed plate value 0.40 was previously documented and is outside this operator-only decision. L plate CL=0.40 and shape coefficients=0.50 remain unchanged. No newly discovered independent open-hole discrepancy was found.
