# Direct MC1 materials and project conditions

Scope: new Direct inputs only, following the original MC1 order and owner engineering
clarification R1, Option B. Candidate predecessor: 44faac5c4ccf7f46f1a8ff739114916047889a40.
This is an input/reporting candidate for owner review; it does not accept or freeze Direct.

## Compact screen

The ordinary Direct surface provides the selected FRP material, its resolved resin,
one Design Temperature and display unit, a read-only required Tg, Dry / Sustained
moisture, None / Custom chemical adjustment, the conditional strength factor and
the seven explicit load classifications. Help uses keyboard-operable native details.
Two columns collapse to one at narrow widths. Advanced details start collapsed and
retain catalog properties, provenance, digests, assignments, factor inspection,
useful session editing and imported extraordinary exposure evidence.

## Explicit new-input policy

Only an explicit SHEAR01-DIRECT-MC1 DTO marker on a Direct finalization request
activates this policy. The backend requires one finite Design Temperature to be
physically equal to both existing sustained and maximum wire temperatures, then
canonicalizes all three using the existing exact Fahrenheit and decimal contracts.
Other family calculation routes reject this marker. The original base dataclass and
legacy serialized DTO fields are unchanged for unmarked historical requests.
New MC1 submissions require the shared default policy and matching canonical
component conditions. Legacy or conflicting overrides cannot bypass the compact
inputs or cause reports to describe factors different from those consumed.

Design Temperature is highest expected service temperature, conservatively assumed
sustained for resistance adjustment, and used for required Tg. It is not measured
product Tg. Required Tg remains max(180°F, T_design + 40°F); product conformance is
project procurement QA. Existing Table 2-2 boundaries and source authority remain:
90°F is the reference boundary; 140°F uses the approved endpoint; above 140°F
requires a test-based factor and no adjusted resistance is invented.

For new MC1 inputs above 140°F or an editable session resin with no established
temperature model, a Direct backend source-availability projection
marks dependent FRP checks SOURCE_DATA_PENDING / NOT_EVALUATED and removes their
definitive resistances and utilizations. Independent bolt checks retain their
actual results, including numerical failure. Signed field changes preserve every
original value and reconstruct the complete raw engine output exactly, verified
against its digest. Unchanged native evidence is retained once in the technical
audit; the original fingerprints are diagnostic only, not design passes. The frozen engines and F9 reducer
are unchanged. Historical unmarked requests keep their original diagnostic behavior.

| Input policy | Sustained / maximum | Polyester strength CT | Required Tg |
|---|---|---|---|
| Historical signed control | 70°F / 100°F | 1.00 | 180°F |
| New Direct MC1 | 100°F / 100°F | 0.90 | 180°F |
| New Direct MC1 | 104°F / 104°F = 40°C / 40°C | 0.86 | 180°F |
| New Direct MC1 | 140°F / 140°F | 0.50 | 180°F |
| New Direct MC1 | >140°F | test-based source required | max(180°F, T+40°F) |

A new UI state adopts the higher physical prior temperature, discloses that
adoption and invalidates current engineering/report authority. Imported original
values remain in legacy state; signed historical reports are never rewritten.
Temperature display-unit changes retain the stored physical value until edited.
Sparse exact decimal comparison prevents cancellation or exponent-size expansion
in the UI adoption comparison; all engineering factors remain backend-owned.

## Moisture and chemical scope

Dry maps to REFERENCE (strength CM=1, modulus CM=1). Sustained moisture maps to
SUSTAINED_MOISTURE (strength CM=.75, modulus CM=.90). Unknown legacy selections
remain unknown and require an explicit new selection.

None maps to NONE_DECLARED, CCH=1.00. Custom requires an exact finite decimal
string with 0 < CCH <= 1.00. Both UI and backend reject invalid, nonfinite, Boolean,
zero, negative or >1 inputs. No document upload, certificate or justification is
required for this engineer-specified factor; it is not certified chemical test data.
Applicable strength candidates consume CM × CT × CCH exactly once. Native end-use
factors remain neutralized by the existing MAT1 transport; bolt strength and actions
are unaffected.

Owner Option B forbids applying strength CCH to tensile, compressive or shear
modulus. Established moisture/temperature modulus adjustments are retained as an
explicit independent candidate; CCH and definitive chemical-adjusted modulus are
unevaluated. The native adapter marks these modulus entries ineligible for definitive
Chapter 8 equation use. Current supported Direct strength checks do not consume
these moduli; analytically independent checks can run. The unresolved material gate
continues to prevent GREEN. The signed ledger retains the independent candidate,
factor origin and applicability limitation; reports read this evidence without
changing engineering results.

## Removed controls and retained evidence

No new Direct UV, freeze-thaw, protective-system, exposure-note or provenance-text
form is required. Routine ASCE catalog durability remains a product-specification
requirement, distinct from actual extraordinary service exposure. Unknown stored
declarations are not converted to NONE_DECLARED, and are not invisible form-completion
gates solely because those controls were removed. Known SPECIFIED exposure, protective
measures, exposure notes and fatigue declarations retain their engineering-review
issues and read-only legacy evidence. This does not qualify a connection or give
unknown chemical-modulus behavior a unity factor.

## Classification and report authority

| Existing category | Resistance time-effect λ |
|---|---|
| DEAD_ONLY | .40 |
| IMPACT | 1.00 |
| STORAGE | .60 |
| LONG_TERM_OPERATING | .40 |
| OTHER_LIVE | .80 |
| SNOW_RAIN_FLOOD_ATMOSPHERIC_ICE | .75 |
| WIND_TORNADO_SEISMIC | 1.00 |

Selection is explicit and never inferred from actions or names. Long-term operating
visibly declares full operating amplitude for more than one year and sets that
existing duration witness. Lambda is a resistance factor, not a load multiplier.
The editable combination-name field is removed; DIRECT-FACTORED-ACTION replaces a
blank/generic UI identifier deterministically. Imported nonempty names are retained
as provenance. Signed historical requests keep their original names.

Backend F9 precedence and Section 2.3.2 authority remain unchanged. The historical
owner control retains eight evaluated checks, six unresolved items, bounded Angle
heel N/A and two neutral material records. Chemistry cannot activate qualification
or close the six unresolved engineering/qualification requirements. Actual numerical
RED remains higher priority than incomplete YELLOW. All 53 protected engineering
identities, historical goldens, engines, material catalogs, F593 values, dependencies,
main and protected tags are unchanged. No Angle first-row or Supporting W method
is introduced.

New signed Engineer Reports and Full Technical Audits disclose temperature policy,
exact strength factor origin, independent modulus candidate and chemical limitation.
Exhaustive native evidence stays in the Technical Audit. Engineering edits invalidate
calculation/report currency; camera and display-only unit actions do not calculate
new engineering results. The additive governed CI step generates seven controls in
both modes on Windows 2025 and Ubuntu 24.04 while retaining every previous PDF gate.
