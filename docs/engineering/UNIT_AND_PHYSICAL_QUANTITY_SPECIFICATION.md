# Unit and Physical Quantity Specification

## Contract

Stage 2.1A uses immutable `Decimal` quantities. Public constructors accept `Decimal`,
integer, or canonical decimal string; reject Boolean and float; reject NaN/infinity;
and normalize negative zero for canonical serialization. The explicitly named geometry
adapter uses `Decimal(str(value))` for existing finite real-valued C3 contracts.

Dimensions and units are:

| Dimension | Units | Canonical unit |
|---|---|---|
| Length | in., mm | mm |
| Area | in2, mm2 | mm2 |
| Force | lbf, kip, N, kN | N |
| Moment | lbf-in., kip-in., N-mm, kN-mm | N-mm |
| Stress | psi, ksi, MPa | MPa |
| Dimensionless | one | one |

Exact approved conversion constants are:

- `1 in. = 25.4 mm`;
- `1 lbf = 4.4482216152605 N`;
- `1 kip = 4.4482216152605 kN`;
- `1 psi = 0.00689475729316836133672267344534689069378138756277512555025110 MPa`;
- `1 ksi = 6.89475729316836133672267344534689069378138756277512555025110 MPa`.

Conversions, same-dimension comparisons, same-dimension addition/subtraction, and
dimensionless scaling are the only general operations. The quantity type is not a
symbolic algebra or resistance-equation engine. No intermediate value is rounded.

## Standard holes

`US_CUSTOMARY_PRINTED` adds exactly 0.063 in.; `SI_PRINTED` adds exactly 1.6 mm. The
definition stores bolt diameter, source basis, printed increment, and authoritative
generated hole diameter. A display conversion acts only on the stored diameter.

- U.S. fixture: 0.500 in. + 0.063 in. = 0.563 in. = 14.3002 mm exactly.
- SI fixture: 12.7 mm + 1.6 mm = 14.3 mm, whose inch display begins
  0.5629921259842519685.

These generated holes are not physically identical, so their engineering fingerprints
remain different.

## Canonical fingerprint form

Canonical decimal strings avoid exponent notation and insignificant trailing zeros.
Every quantity records its dimension, canonical unit, and canonical value. Display
unit and rounding preferences are not calculation input.

## Stage 2.1B equation use

Area support is implemented for nominal bolt body area. Equation evaluation uses one
physical path with local 60-digit Decimal precision and no intermediate rounding.
Every golden U.S. input is converted exactly to a physically equivalent SI input and
evaluated independently; unrounded physical outputs and all dimensionless/status
outputs are identical. Separately printed U.S. and SI standard holes remain different
source representations and are not an equivalence pair.

## Stage 2.2A geometry scalar bridge

One audited application bridge interprets finite canonical geometry scalars in the
assembly's declared unit system and converts them with
`PhysicalQuantity.from_finite_real` and `decimal_from_finite_real`. U.S. geometry is
read as inches and SI geometry as millimetres. The bridge does not quantize, round to
display precision, mutate geometry, or select a separate numerical path. P1 and P2A
US/SI cases retain unrounded physical equality and fingerprint equivalence under the
existing policy; J1 retains the same approved engineering values, directions,
statuses, and governing identity through independently constructed geometry.

## Stage 2.2B decimal-string transport

Every transported physical magnitude is a finite canonical decimal string paired
with an explicit controlled unit. JSON numbers, Boolean values, NaN, and infinities
are rejected before canonical mapping. The API supports U.S. customary and SI request
profiles through one production mapping path and emits decimal strings in the selected
response profile without display quantization.

Existing finite geometry primitives cross through one audited scalar bridge into
`PhysicalQuantity`; no second unit engine or equation path is introduced. The API
therefore preserves Stage 2.2A/2.1B physical equivalence, direction selection,
statuses, governing identity, and fingerprint policy.

## Stage 2.3 case-level unit profiles

The interactive workspace offers only complete U.S. customary and SI request
profiles. It preserves decimal strings and explicit units supplied by the selected J1
input fixture. After any edit, changing the unit system requires confirmation and
replaces the complete case with the other verified profile; no field-by-field browser
conversion or display-rounding mutation occurs. The backend remains the sole quantity
conversion and calculation authority. Visualization positions use the response
`length_unit`, action arrows use response force/moment units, and unit selection does
not alter frame directions or engineering status.
