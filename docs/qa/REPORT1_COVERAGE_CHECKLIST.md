# REPORT1 report coverage checklist

The first REPORT1 implementation was published at
`eae3374dd0af26e93e8b1bb02265eafecb68e5ec`. Independent review then
identified the six reporting and evidence defects reproduced in
`REPORT1_AC1_BASELINE.md`. This checklist records the bounded AC1 correction;
it does not change native engineering authority or qualify an incomplete design.

`test_report1_ac1_all_modes.py` exports a real authenticated PDF for each of
the 18 current modes in both U.S. and SI presentation (36 PDFs). It checks
snapshot export, distinct outline target pages with matching section text,
figure/dimension markers, method presence and absence of unavailable executed
factor substitutions. The existing field, provenance, tamper and input-only
tests continue to check the shared snapshot and report contract.

| Current calculation/report mode | Canonical figure and dimension adapter | Worked method / result source | US/SI and navigation audit |
| --- | --- | --- | --- |
| Direct, single bolt | Native local boundary witnesses and through-bolt stack | Single-bolt method traces and all native checks | 2 real PDFs |
| Direct, multi-row | Native plan with end, edge, pitch, gauge, bolt/hole and ply witnesses | Multi-row equation traces and every native check | 2 real PDFs |
| Tee connector | Physical component edges and identified bolt-row interfaces | Native equation methods and check records | 2 real PDFs |
| Single clip angle | Physical component edges and identified bolt-row interfaces | Native equation methods and check records | 2 real PDFs |
| Paired clip angles | Physical component edges and identified bolt-row interfaces | Native equation methods and check records | 2 real PDFs |
| Multi-member Tee | Physical component edges and identified bolt-row interfaces | Native equation methods and check records | 2 real PDFs |
| Beam to concrete paired angles | Physical component edges and identified bolt-row interfaces | Native equation methods and check records | 2 real PDFs |
| Direct side-lap to concrete | Physical component edges and identified bolt-row interfaces | Native equation methods and check records | 2 real PDFs |
| Column base web angles | Physical component edges and identified bolt-row interfaces | Native equation methods and check records | 2 real PDFs |
| Beam web splice | Physical component edges and identified bolt-row interfaces | Native equation methods and check records | 2 real PDFs |
| W/I moment splice | Physical component edges and identified bolt-row interfaces | Native equation methods and check records | 2 real PDFs |
| Channel moment splice | Physical component edges and identified bolt-row interfaces | Native equation methods and check records | 2 real PDFs |
| W/I beam to concrete wall moment | Physical component edges and identified bolt-row interfaces | Native equation methods and check records | 2 real PDFs |
| W/I beam to FRP support moment | Physical component edges, bolt-row interfaces and bolt-axis stack | Native equation methods and local support checks | 2 real PDFs |
| Two-leg angle column moment base | Physical component edges and identified bolt-row interfaces | Native equation methods and check records | 2 real PDFs |
| W/I, RHS, SRS column moment base | Physical component edges and identified bolt-row interfaces | Native equation methods and check records | 2 real PDFs |
| Double-channel truss node, including 3B | Physical component edges, bolt-row interfaces and bolt-axis stack | Native axial/3B response and explicit limits | 2 real PDFs |
| Stair stringer miter analytical design | Actual native polygon-face edge witnesses and physical interfaces | Native analytical, finite-cut and source-limited checks | 2 real PDFs |

The selector has 17 connection options; Direct exposes two calculation modes.
MAT1 wraps supported modes with the selected material and condition record.
SSMC analytical design is distinct from its historical demand-only endpoint.

The drawing adapters use canonical box, polygon, bolt, layer and interface
records. Three physical box edges are witnessed per component; each finite
polygon edge is witnessed when the native face is available. Nested native
multi-row interfaces carry end, side/edge, pitch, gauge and bolt/hole labels.
Every figure states **not to scale**. The report never measures geometry from
rendered pixels. `test_report1_ac1_figures.py` varies native dimensions and
checks the resulting labels. `test_report1_ac1_all_modes.py` checks the
per-family figure branch, including nested interface drawings when present.

`test_report1_ac1_navigation.py` resolves real PDF outline and internal-link
destinations on Letter and A4, checks destination headings on the reached
pages, and guards the W/I contents orphan. `test_report1_ac1_substitutions.py`
checks U.S./SI native parity and worked first-row and block-shear stages.
`test_report1_ac1_adapter_fail_closed.py` proves missing executed operands
stop export. `test_report1_ac1_method_bindings.py` covers the remaining
executed-method registry and varied consumed values. The full native appendix
continues to represent every repeated path and nongoverning result.

Source-required, not-evaluated and external-design states remain visible as
native engineering limitations. A missing REPORT1 adapter is a report defect
and cannot be relabeled as one of those states.
