# F8 Section 2.3.2 statistical authority

Licensed ASCE/SEI 74-23 Sections 2.3.2, 2.3.1, 2.4.1–2.4.4, 1.7 and C2.3.2
were reinspected privately. Source PDF SHA-256:
`A7127E37572D5D625C5F338FFB9A1D2D53F396897AFB26E0B4698A0131FE65BC`.
The A4 audit package SHA-256 is
`8835F881B7B0AE54BB1846637D834378832455CFD72AC6C71E18412242279A77`.
Licensed pages are not redistributed.

N is derived from accepted raw specimens, at least 10. Duplicate IDs, nonfinite,
nonpositive or nonforce strengths, mixed population scope/protocol/fixture,
unapproved exclusions and inconsistent laboratory statistics block eligibility.
Mixed force units use the existing exact quantity converter.

Ro is the arithmetic mean; supported estimator is SAMPLE_SD_N_MINUS_1:
s = sqrt(sum((Ri-Ro)^2)/(N-1)); VR=s/Ro. ASCE states COV without independently
specifying this estimator; its use requires the lab/RDP-approved protocol.
Laboratory mean/SD/COV and declared decimal precision remain separate. Decimal
power-of-ten precision is reconciled using ROUND_HALF_EVEN, never an engineering
tolerance. Missing precision requires exact equality. No client aggregates enter
the derivation.

Connection t uses SciPy 1.18.1 `scipy.stats.t.ppf(.999, N-1)`; its finite positive
IEEE754 binary64 result is retained by round-trip Decimal conversion. All other
statistics and phi arithmetic use 80-digit Decimal, ROUND_HALF_EVEN:

```
phi_p = exp(-t_(N-1,.999) * VR * sqrt(1 + 1/N))
Rn = Ro * applicable existing MAT1 end-use factors
Rd_q = current lambda * phi_p * Rn
```

Independent quantiles for N=10,11,20,30,50,100,500 were generated outside the
product with mpmath 1.3.0 at 90 decimal digits by bracketed incomplete-beta CDF
inversion (500 bisections). This QA tool is not a production dependency and never
calls SciPy. The quantile-only numerical acceptance is four IEEE754 binary64
ULPs against these high-precision references, reflecting inverse-CDF numerical
representation. It is not an action/scope, engineering strength or gravity
tolerance. Each platform retains full production t/phi without decision rounding.
N=10, VR=.15 produces phi_p approximately .50866, consistent with the commentary
example rounded to .51. This example is QA, not qualification evidence.

Primary library references:
[pinned release](https://pypi.org/project/scipy/1.18.1/),
[Student-t implementation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.t.html),
[NIST Student-t distribution](https://www.itl.nist.gov/div898/handbook/eda/section3/eda3664.htm).

Only SciPy 1.18.1 is added directly; NumPy 2.5.3 is its sole newly added
transitive package. Hash locks retain all preceding versions and bytes after
removing those two exact blocks. See the F8 dependency successor manifest and
historical freeze guard, which restore exact prior dependency/workflow identities.
