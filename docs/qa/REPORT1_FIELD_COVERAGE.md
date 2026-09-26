# REPORT1 field presentation map (candidate)

This map describes what the current candidate prints from the signed backend
response. It is not a claim that REPORT1 is accepted. The reporting code does
not invoke engineering equations or assign qualification.

| Native record | Printed location | Representation |
| --- | --- | --- |
| Validated calculation request body | Submitted engineering inputs | Every leaf path; exact native values, with quantity value/unit and canonical value/unit in one row |
| Server-accepted request defaults | Input provenance schedule | Pydantic-validated body compared with the submitted JSON after the same calculation route; omitted fields and server-created list entries are named separately |
| Backend-resolved values | Complete native result appendix and method sections | Resolved geometry, factors, materials, load assignments, traces and results retain their native paths and values |
| Calculation query options | Submitted engineering inputs under `_calculation_query_parameters` | All non-report query values, including connector body selection |
| MAT1 assignment and condition request | Submitted engineering inputs | Original selected material and condition records, including session custom values |
| Canonical visualization snapshot | Canonical figures and complete native result appendix | Native boxes/faces/bolts and their source coordinates; projections are display only |
| Native geometry outside visualization | Complete native result appendix | Every geometry leaf retained; nested designs under a preview remain present |
| Native load, action, bolt and layer records | Load assignment, worked examples and complete native schedule | Signed native components, identifiers and exact-rational numerator/denominator where exposed |
| Native result/check/trace/factor records | Method sections and complete native schedule | Executed template where mapped, status, factors, numerical values and source text; identical subrecords link to their first printed path |
| Native source/blocker/qualification state | Summary, limitation section and complete native schedule | Actual statuses and memberships; no missing-to-zero conversion |
| HTTP 422 calculation validation result | Input-only report | Original request, server validation issues, `INPUT_VALIDATION_FAILED`; no valid geometry drawing or design result |
| Unrun or locally invalid client draft | Distinct input-only report | Server-sealed submitted draft and current family MAT1 selection/conditions where active; `INPUT_NOT_EVALUATED`, no native geometry or design result |
| User metadata | Cover/footer/calculation identity | Identification only; it has no engineering authority |

`tests/test_report1_field_coverage.py` enumerates actual request leaves from all
18 native family fixtures and verifies that each has a printed or aliased path.
It also guards nested geometry, visualization and design records. Repeated
geometry and preview tables were removed; their original paths appear once in
the complete native appendix. `tests/test_report1_provenance.py` verifies
server defaults, including nested defaults and server-created list entries.

The submitted-value label means only that a field was present in the JSON sent
to the server. If the UI initialized that field before submission, the report
cannot distinguish the initial UI value from a value the user edited. Native
quantity rows retain the original value and unit; alternate display units are
supplied for supported physical quantities without changing the calculation.
An unavailable conversion remains in its native unit. These provenance and
display limits are stated in the PDF.
