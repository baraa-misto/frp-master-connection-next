# FRP Master Connection — Stage 3.2-R8 Profile Wall Bolt-Path Geometry Generalization — Engineering Specification RC1

## 1. Status
**Controlled owner engineering correction specification — RC1**

Stage 3.2-R8 generalizes the finite opposing-broad-face / through-thickness bolt-path geometry for the remaining non-flat connected-member profiles exposed during Stage 3.2 visual acceptance.

R7 corrected Angle leg paths. Renewed visual review then showed the same backend rejection for:
- Channel brace using `WEB_OUTER`; and
- Rectangular hollow-section brace using an exterior flat face.

R6 correctly shows these rejected current inputs as `current inputs invalid — showing last valid preview`.

R8 corrects backend/domain profile wall geometry. It does not create a new demand or resistance equation.

## 2. Accepted starting baseline
- `HEAD == origin/main`: `a642cf44a337e7b98f982d34af05182165df2e57`
- subject: `fix: resolve angle leg bolt paths`
- commit count: `52`
- tracked files: `327`
- clean worktree/index
- frontend source tree: `40956420c22c42910a8a2cbe82c74ed2e6a5f407`
- freeze tag: `stage-2.3-interface-geometry-freeze`
- freeze target: `5bc545ab8251f9bd49dedc776962937ed5e822a2`

R7 hosted CI is accepted 4/4 green with 259/259 frontend tests on Ubuntu and Windows.

## 3. Visual-review evidence
Channel form:
- depth `6 in`
- flange width `3 in`
- web thickness `0.5 in`
- flange thickness `0.5 in`
- length `8 in`
- orientation `0°`
- selected surface `WEB_OUTER`
- Interface A `2 x 2`
- pitch/gauge `2 in`
- unloaded end distance shown `1.3 in`

Rectangular hollow-section form:
- depth `6 in`
- width `4 in`
- wall thickness `0.5 in`
- length `8 in`
- orientation `0°`
- selected surface positive Y exterior face
- Interface A `2 x 2`
- pitch/gauge `2 in`
- unloaded end distance shown `1.3 in`

Both are rejected with:
`Each connected-profile bolt path must select one finite opposing broad face.`

## 4. General physical rule
For every supported profile connection surface, a connected-profile bolt path must:
1. start on one finite selected exterior broad face;
2. enter the selected physical wall/leg/flange/web solid;
3. cross exactly the intended material thickness;
4. exit through exactly one finite exposed opposing broad boundary face of that same physical wall/leg/flange/web;
5. have the complete hole footprint contained in both finite broad-face patches;
6. not use internal solid-overlap planes as exposed faces;
7. not exit through a free edge;
8. not silently cross a different wall/member component.

The opposing patch shall be derived from the actual section solid union.

No epsilon, tolerance, or nearest-plane workaround is permitted.

## 5. Flat plate
Existing Flat Plate behavior remains unchanged.

## 6. Angle
R7 behavior remains controlling and unchanged. Do not replace or weaken the R7 Angle resolver.

## 7. Channel profile
A Channel contains one web and two flanges. Web/flange intersection regions are one solid; internal overlap planes are not exposed boundary faces.

### 7.1 WEB_OUTER
A bolt normal to `WEB_OUTER` shall cross exactly the web thickness and exit through the exposed inner web broad face.

The valid inner-web patch is limited to the clear web region between the two flange inner faces. The complete hole footprint must remain inside that exposed patch.

A hole overlapping a flange-junction strip remains invalid for a simple web-only path.

### 7.2 FLANGE_POS_OUTER / FLANGE_NEG_OUTER
A bolt normal to an exterior flange broad face shall cross exactly one flange thickness and exit through the exposed inner flange broad face.

The opposing inner-flange patch excludes the web-intersection strip. A hole overlapping the web intersection remains invalid for a simple flange-only path.

Channel inner faces are open-section accessible faces; R8 adds no access qualification.

## 8. Wide-flange / I profile
Existing accepted W/I behavior must remain unchanged.

Add explicit regression coverage:
- web opposing face limited to clear web between flange inner faces;
- flange opposing face limited to physical overhang regions excluding web intersection;
- a hole overlapping the web/flange intersection is not a simple one-wall path.

If current production already satisfies these rules, do not rewrite it unnecessarily.

## 9. Rectangular hollow section
A rectangular hollow section contains four wall solids around an interior cavity.

R8 supports **single-wall bolting through the selected exterior wall only**. It does not authorize a through-bolt crossing both opposite tube walls.

For each selected exterior face:
- `Y_POS_FACE`
- `Y_NEG_FACE`
- `Z_POS_FACE`
- `Z_NEG_FACE`

the opposing face is the corresponding **inner cavity face of that same wall**, exactly one wall thickness away.

At corners, the opposing cavity face is exposed only over the clear cavity span excluding adjacent-wall intersection strips. The complete hole footprint must lie inside both the finite exterior wall patch and finite inner cavity patch.

A hole overlapping a corner intersection remains invalid.

### 9.1 Internal fastener access
A single-wall hollow-section path requires practical access to the inner side to place/hold the accepted fastener component.

Every RHS single-wall Tee connection shall therefore carry a trace/qualification item equivalent to:

`INTERNAL_FASTENER_ACCESS_REQUIRED`

R8 does not automatically prove access exists.

### 9.2 Not authorized
R8 does not authorize:
- through-bolting across both tube walls;
- spacers/crush sleeves;
- blind fasteners/inserts;
- access-hole design;
- tube-wall flexure/prying resistance.

## 10. Round hollow section
Round hollow section remains unsupported for direct flat Tee-stem contact.

## 11. Exact wall thickness
For every valid path:
`distance(selected outer broad face, opposing exposed broad face) == exact physical wall thickness`

using authoritative exact geometry.

## 12. Full Tee application fixtures
After correction construct backend-valid fixtures.

### Channel
Start from:
- `D=6 in`
- flange width `3 in`
- web thickness `0.5 in`
- flange thickness `0.5 in`
- length `8 in`
- `WEB_OUTER`
- Interface A `2 x 2`
- pitch/gauge `2 in`

Use only the smallest exact end/side-distance adjustments needed by the existing finite-hole containment rule. Report the final valid fixture.

### Rectangular hollow section
Start from:
- depth `6 in`
- width `4 in`
- wall thickness `0.5 in`
- length `8 in`
- positive Y exterior face
- Interface A `2 x 2`
- pitch/gauge `2 in`

Again use only exact layout adjustments required by current finite-hole containment. Report the final valid fixture and internal-access qualification.

## 13. Existing mechanics unchanged
Do not change Tee topology, Interface A/B semantics, Stage 2 demand/resistance, Stage 3.1 material authority, R4 exact unit geometry, R5 fingerprints, R6 preview states, or R7 Angle geometry.

## 14. Fingerprints
No accepted fingerprint transition is authorized. If one changes, STOP and request explicit authority.

## 15. Controlled golden coverage
The companion golden shall cover:
- Channel web valid clear-span path;
- Channel web flange-junction invalid path;
- Channel flange valid overhang path;
- Channel flange web-overlap invalid path;
- W/I regression;
- RHS valid outer-to-inner-wall path;
- RHS corner-overlap invalid path;
- RHS exact wall thickness;
- RHS internal-access qualification.

## 16. Visual behavior
After valid backend preview:
- Channel renders as Channel, not last-valid W/I;
- RHS renders as rectangular tube, not last-valid W/I;
- R6 invalid warning clears;
- Interface A bolts appear on selected physical surface;
- Interface B remains independent.

Invalid junction/corner cases remain fail-closed with R6 stale labeling.

## 17. Acceptance
R8 is acceptable only if:
- Channel and RHS opposing-face geometry is physically correct;
- valid Channel and RHS Tee previews succeed;
- invalid junction/corner cases remain rejected;
- RHS single-wall access requirement is explicit;
- W/I and R7 Angle remain exact;
- no new resistance equation is introduced;
- controlled hashes/fingerprints remain exact;
- full QA and hosted 4/4 CI pass.

**END OF CONTROLLED ENGINEERING SPECIFICATION — RC1**
