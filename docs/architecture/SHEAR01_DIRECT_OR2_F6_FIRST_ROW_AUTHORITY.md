# Direct F6 first-row authority decision

Controlling order: SHEAR01-DIRECT-OR2-F6; SHA256
4CF48822CCAFC6568659C266DFE2DC466C9C9123AC921ED87C5515DB483AC4C7.

Baseline a197d6630701a641b0846c1942497dac24f412a3. Owner reference uses the saved
authenticated F5 request in the A3-R1 numerical parity fixture.

## Classification

SHEAR01_DIRECT_OR2_F6_FIRST_ROW_UNRESOLVED.

Angle: METHOD REQUIRED - ECCENTRIC DEMAND / STRESS.
W: METHOD REQUIRED - ROW IDENTITY, EFFECTIVE WIDTH, SOURCE APPLICABILITY,
and ECCENTRIC DEMAND / STRESS.

Neither owner first-row check has been calculated or exempted. The final
schedule remains 7 evaluated / 8 unresolved, with two neutral material review
rows. No GREEN or qualification activation follows from this task.

## Source review

Licensed ASCE/SEI 74-23 PDF pages 50-51, 108-113 (printed 35-36, 93-98),
including Figure C8-11 on printed 95, were visually reviewed. The registered
January 2026 erratum does not change these Chapter 8 equations.

The source first-row connection resistance combines bearing Lbr and bypass
1-Lbr contributions. For the source's concentric scalar configuration its
comparison is to total transferred connection force, not a single bolt's
resultant. Table C8-1 supplies FRP/FRP shares 0.50/0.50 and 0.40/0.20/0.40
for two/three rows. These are resistance-model inputs, not the rational
elastic bolt-force solution.

The owner has a real external residual moment about -0.175 kip-in. The
accepted bolt-group solution satisfies action equilibrium but supplies no
source-approved net-section bearing/bypass stress field under this moment.
No P/A+M/S, force sum, maximum bolt force or replacement Lbr is authorized.

Angle native rows at x=5 and 3 in map first/second using the real unloaded x=0
end. Loaded x=8 and unloaded x=0 distances are separate quantities, both
3 in here. The force is longitudinal to the Angle and normal to its row.
Two-row e1,min=2d=1 in; e1,max=2 in excludes the submitted 3 in from the
main-body simplified method.

Angle LEG_1 has a real positive free edge and one perpendicular LEG_2 at its
heel. Figure C8-11b is the relevant longitudinal geometric arrangement; the
heel is not a free edge. Physical free-edge and heel clearances are approximately
1.75 in each; UI 1/1 in is only template geometry. The figure's symmetric
3.5-in construction and the source formula's e2 caps must be reconciled in a
controlled Direct physical-width handoff before activation. This task does
not substitute a computational 2-in width or silently elect a width policy.

W TOP_FLANGE has two flange free edges and an internal web. The transferred
force is 45 degrees to W pultrusion; the bolt-row normal remains the force
direction, but the oblique net-section plane, source first-row identity and
e3/e4 construction do not follow from longitudinal stations or flange width.
Continuous W is not a first-row exemption. Finite longitudinal ends alone do
not close the oblique source mapping. Angle and W each have only one relevant
perpendicular element; neither satisfies the source two-perpendicular-element
exception.

## Bounded software correction

The exact zero-eccentricity control exposed inherited calculation of Direct
FIRST_ROW_SIMPLIFIED with template width 2 in, including e1=3 in outside
the source envelope. The Direct adapter now makes these unproved first-row
plans unavailable before the unchanged handoff/group-mode engines execute.
It changes no mechanical equation or current owner evaluated check.

RC3 remains inactive globally and for Direct. Production has no RC3 call.
A future Direct-specific activation requires all F6 gates, including independent
physical width, row/end direction and demand/stress authority. Main-body routing
must be preferred when fully source-applicable; selecting the larger capacity
is prohibited.

Reports give precise first-row reasons from the authenticated native demand.
The report shim changes no result, demand, resistance, utilization, status,
qualification, applicability, governing logic or snapshot content.

## Review limits

Zero-eccentricity and main-body end-envelope controls are real signed API
designs but remain unresolved at the physical-width/demand adapter boundary.
A source-valid production Appendix nonunit-Theta design and first-row RED design
were not created. RC3's independent coefficient benchmarks establish arithmetic
only and do not qualify physical designs. Plate policy, other connection
families, block shear, W inter-row shear-out and whole-connection qualification
remain outside this task.
