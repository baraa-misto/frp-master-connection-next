# HYB1 specific RHM decisions required

Six consolidated questions. Independent arithmetic and integration code is executable;
these questions prevent actual Angle-to-W supplemental method adoption. No production
method, material policy, qualification or Route C restriction changes in HYB1.

## Q1 - Angle first-row stress transfer and effective width

Which companion equation gives first-row net-section demand and resistance for the
inclined L4 x 4 x 0.5 leg with an integral heel, 0.563-in holes and submitted true e1=3 in?
Identify effective width, bearing/bypass distribution, any shear-lag or concentration
coefficient and its validated domain. Calcs D87:D112 only provide a beam block interaction;
they do not provide this first-row law. EM2 established the unresolved width/source
interpretation and retained out-of-plane actions. A property-column lookup is insufficient.
Affected: FIRST_ROW:layer-A, both alignments (SUPPORT is staggered in Angle axes).

## Q2 - Independent receiving-W failure paths

Provide the receiving flange first-row and inter-row equations and the two independent
block-release definitions. How do the negative-CW outstand and positive-CW integral-web
side carry the actual oblique load and unknown remote column N/V/M? Identify the true
finite ends needed in SUPPORT; view crops are excluded. Calcs D59:D112 concern the beam;
D149/D168 cover column bearing only. PulTex Vol5 Rev15 Chapter4 p104 shows a coped beam-web
example, not these receiving-W paths. Its example also prints 5000 psi in the final sum
after establishing 5250 psi tensile allowable, so it is not a clean transferred oracle.
Affected: FIRST_ROW:layer-B, INTERROW:layer-B:BOLT_LINE_1 and distinct W LEFT/RIGHT,
both alignments. Required response: source-located equations plus a validated release
and remote-action boundary model, not a statement that column bearing passes.

## Q3 - Net paths, holes and reinforcement engagement

Are Calcs D62/D73/D87/D88/D100/D101 lengths gross, already net or another convention?
Specify each hole/corner ownership and deduction rule and the engagement model that
permits Calcs D144/D161 to add the saved 0.375-in doubler. Establish the reinforcement
material/orientation and adhesive/fastener transfer rule, including active optional
parts. No ASCE hole allowance or second hole deduction is imported. The saved 0.75-in
reference thickness remains explicit; the actual owner geometry gets no doubler credit.
Affected: reference-to-actual local/block mappings and any reinforced assembly, both alignments.

## Q4 - Signed eccentric and 3D demand applicability

What validated demand/contact and FRP stress-transfer model replaces workbook P/n,V/n
for actual C01/C02? The original P, group midpoint G, signed F and all transported M
are retained. Address reversal, compression/contact, bolt stiffness, staggered stations,
prying, Angle heel and W flange/web junction. Equal bolt-force equilibrium alone does
not establish first-row stress capacity. Calcs D43:D80 contain no such model; existing
ASCE supported checks stay unchanged. SUPPORT cannot inherit BRACE row/path/heel N/A.
Affected: both alignments, changed Angle checks and three separately scheduled 3D mechanisms.

## Q5 - Actual product, ASD conditions and supplied action-set policy

Establish the actual product/resin/region/axes and statistical definition of each RHM
listed strength, its own safety factor and approved environment/duration policy. The
workbook Dim & Properties D/E/F columns and SF4 are recorded reference values, not a
replacement for current characteristic MAT1 properties or F593 hardware. Provide
independent complete ASD combination results and their source; no LRFD/1.6 conversion,
combination generator or inherited ASCE adjustment is installed. Unknown ASD conditions
remain unresolved. A source match alone does not establish qualification.
Affected: all actual supplemental numerical evaluations, both alignments.

## Q6 - Storm rule

Confirm the intended joint load/allowable rule and combination domain for Input M31/M32
and Calcs B10. Historical demand x 2/3 disagrees with the stated one-third allowable
increase (which algebraically implies x 3/4). Neither is adopted. The corrected
ordinary reference uses no additional storm adjustment. State how duplicate allowance
with supplied ASD combinations is prevented. A storm variant remains unevaluated.

## Smallest next implementation

No actual missing Direct mechanism has a fully supported MAPPED_CANDIDATE in HYB1.
The executable reference core and paired integration are ready for owner inspection.
Adopt at most one named physical subset after Q1/Q2/Q3/Q4/Q5 supply the applicable
equation, demand treatment and independent validation; retain every other missing mode.
Do not activate SUPPORT calculations or broad hybrid design based on arithmetic tests.
C13 and Section 2.3.2 remain independently open.
