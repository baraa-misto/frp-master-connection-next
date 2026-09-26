# REPORT1 reporting coverage checklist

Baseline: `1c9405c0feb4ced8222f4ba9458455ff63d420d9` in the separate
`frp-master-connection-next` repository. This inventory records the actual
connection selectors and native families. Every row has a real Windows PDF
generated through its native route. The shared path includes submitted and
server-default inputs, native material/condition/load/geometry schedules,
executed method records, numerical results, and explicit source limits.
Hosted Ubuntu and exact-SHA CI remain release gates.

| Selector / method | Native family ID | Actual Windows PDF smoke | Release gate |
| --- | --- | --- | --- |
| Direct, single bolt | `single-bolt` | Yes | Hosted CI pending |
| Direct, multi-row | `multi-row` | Yes | Hosted CI pending |
| Tee connector | `tee-connector` | Yes | Hosted CI pending |
| Single clip angle | `clip-angle` | Yes | Hosted CI pending |
| Symmetric paired clip angles | `paired-clip-angle` | Yes | Hosted CI pending |
| Multi-member Tee | `multi-member-tee` | Yes | Hosted CI pending |
| Paired clip angles to concrete wall | `beam-concrete-paired-angle` | Yes | Hosted CI pending |
| Direct side-lap to concrete wall | `direct-side-lap-concrete` | Yes | Hosted CI pending |
| Column base web angles | `column-base-web-angles` | Yes | Hosted CI pending |
| Symmetric double web splice | `beam-web-splice` | Yes | Hosted CI pending |
| W/I moment splice | `wi-major-axis-moment-splice` | Yes | Hosted CI pending |
| Channel moment splice | `channel-major-axis-moment-splice` | Yes | Hosted CI pending |
| W/I beam to concrete wall moment | `wi-beam-concrete-wall-moment` | Yes | Hosted CI pending |
| W/I beam to FRP support moment | `wi-beam-frp-support-moment` | Yes | Hosted CI pending |
| Two-leg angle column moment base | `angle-column-two-leg-moment-base` | Yes | Hosted CI pending |
| W/I, RHS, SRS column moment base | `wi-rhs-srs-column-moment-base` | Yes | Hosted CI pending |
| Double-channel truss node, including 3B | `double-channel-truss-node` | Yes | Hosted CI pending |
| Stair stringer miter, including analytical design | `stair-stringer-miter` | Yes | Hosted CI pending |

The selector has 17 connection options; Direct exposes two calculation modes.
MAT1 supplies a separate material/condition design wrapper for supported families.
SSMC analytical design is distinct from its historical demand-only endpoint.
These variants require method-level coverage within their rows.

Existing engineering limitations are report content. Missing REPORT1 adapters for
executed checks are implementation defects and cannot be labeled source-required.

The actual Windows tests cover all 18 modes, multi-row two/three/four-row
methods, conditional stainless, DCTN-3B transverse response, MAT1 custom
session material, SSMC analytical design, and rejected/unrun input-only cases.
Every executed native check retains its path and exact native values in the
complete appendix. Recognized methods receive reviewed equation records; a
missing adapter for an executed method fails export explicitly. Worked records
include W/I and Channel resultants, flange and web force-line decomposition,
plate tension, web-panel interaction, connector instep, in-plane wrench,
support-side bearing, DCTN axial and 3B action transport, and SSMC finite cuts.

All 934 pages of five representative Windows PDFs were rasterized and checked
for blank pages, out-of-bounds text origins, and page-edge contact. Contact
sheets for every page were inspected. The W/I support sample is 559 pages;
its searchable complete native appendix is long. Focused backend coverage,
Ubuntu generation, and hosted exact-SHA CI must be recorded before acceptance.

## Renderer decision

Use one server-side ReportLab 5.0.1 pipeline for controlled vector figures,
searchable text, schedules, bookmarks, and Letter/A4 pagination. The official
distribution supports Python 3.14 and carries a BSD license. This avoids a
browser binary in the calculation service. It does not by itself prove equation
or input coverage; adapters and page inspection remain required.
