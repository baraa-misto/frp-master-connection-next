# Stage 2.3 Interface and Geometry Foundation Freeze

## Freeze identity

| Control | Recorded value |
|---|---|
| Freeze name | Stage 2.3 interface and geometry foundation freeze |
| Approval | Approved by Baraa Misto after Stage 2.3R8 implementation and visual review |
| Frozen implementation commit | `5bc545ab8251f9bd49dedc776962937ed5e822a2` |
| Annotated Git tag | `stage-2.3-interface-geometry-freeze` |
| Hosted CI | Success: 4/4 Ubuntu 24.04 and Windows 2025 backend/frontend jobs passed in 2 minutes 23 seconds; 123 frontend tests passed on each hosted platform; no artifacts were shown |
| Calculation engine | `0.1.0.dev1` |
| Engineering rule set | `asce74-23-ch8-single-bolt-rc2.dev1` |
| RC2 golden SHA-256 | `39051EDD6D345803AD7275EB33A26786B7094248E76B1B1A44B2FA82B70E6392` |

The annotated tag identifies the accepted implementation baseline. It points to the
hosted-CI-green Stage 2.3R8 commit above, not to the later documentation-only commit
that records this decision.

## Scope and effect

This is a scope-specific freeze of the Stage 2.3 user-interface foundation,
canonical visualization architecture, live-preview/design-check interaction model,
current brace-to-column geometry controls, frame/material-axis/action-visualization
conventions, viewport navigation, applied-action label/editing behavior,
engineering-geometry versus view-extent separation, and current single-bolt
workspace presentation contracts.

This freeze does not freeze the whole FRP Master Connection product and is not a
production or commercial release. The project remains in development. It does not
freeze future equation development, multi-bolt or multirow calculations,
bolt-demand distribution, additional connection families, Moment Connections,
material-library or custom-manufacturer editing, persistence, authentication,
authorization, entitlement, billing, reporting, or generalization required by newly
approved engineering scope.

Compatible extensions may proceed under controlled development when they preserve
every frozen invariant below.

## Frozen invariants

### A. Workspace and product shell

1. Exactly two primary categories remain: Shear Connections and Moment Connections.
2. The implemented interactive workspace remains the verified Shear Connections,
   direct brace-to-column-flange, single-bolt/single-row slice.
3. Moment Connections remains deferred in the current workspace.
4. The connection-first desktop foundation retains a compact engineering sidebar,
   persistent connection viewer, Model/Geometry Status, separate Design Results,
   and advanced diagnostics/inspectors.
5. The workspace remains session-only; inputs and results are not persisted.

### B. Backend authority

6. The backend remains authoritative for canonical geometry, frames,
   surfaces/interfaces, bolt path, interference, material axes, applied-action
   directions, and engineering calculations.
7. The frontend remains presentation-oriented and untrusted.
8. The frontend must not become a second engineering geometry or resistance engine.

### C. Live preview and design

9. Engineering sidebar changes use automatic canonical backend preview.
10. Preview may resolve geometry, contact/interface, bolt path, interference,
    material relationship, frames/axes, action arrows, and the visualization snapshot.
11. Preview executes zero resistance equations.
12. Resistance and utilization run only through explicit `Run Design Check`.
13. Geometry/model status remains separate from design status.
14. Invalid geometry appears before design calculation.
15. Design results become stale after design-affecting engineering edits.
16. Presentation-only interactions do not stale design results.

### D. Engineering end geometry and view extents

17. The connected brace end plane is authoritative engineering geometry.
18. Bolt-to-brace-end distance `e1` is separate authoritative engineering geometry.
19. The J1 default is `e1 = 2.000 in = 50.8 mm`.
20. The calculation engine receives `e1` by re-deriving it from canonical geometry.
21. User-entered `e1` is not passed directly into a resistance equation.
22. Brace view length and column view extents below and above the connection are
    preview-only extents.
23. View extents may update preview visualization, but do not alter engineering end
    planes, `e1`, capacities, fingerprint, or current-design staleness.

### E. Brace and column orientation

24. Current W-column member-local positive x is global positive Z.
25. Current column START is lower and END is upper.
26. Brace-to-column geometry angle is directed in the verified vertical plane.
27. The valid directed range is `0 degrees < theta_g < 180 degrees`.
28. Current out-of-plane/plan angle remains fixed at 0 degrees.
29. Lateral brace approach side remains stable through geometry greater than 90 degrees.
30. Connection side, connected leg, and outstanding-leg controls remain explicit and
    independent.

### F. FRP material axis

31. The material-axis relationship remains sign-independent.
32. The backend resolves the material relationship.
33. Material angle remains the acute, sign-independent axis relationship.
34. Frozen examples are 120-degree geometry to 60-degree material angle,
    150 degrees to 30 degrees, and 175 degrees to 5 degrees.
35. The frontend must not independently choose LW/CW properties.

### G. Connection side and angle clocking

36. W Column Flange connection face supports Exterior face and Interior/web-side face.
37. Connected angle leg supports Leg 1 and Leg 2.
38. Outstanding-leg orientation remains an explicit interface-side choice.
39. The backend owns angle-section clocking.
40. Invalid orientation is not silently auto-flipped.
41. Invalid physical interference fails closed.

### H. Interference and bolt path

42. Unintended angle/W positive-volume interpenetration is invalid.
43. Intended connected-leg boundary contact is allowed.
44. A web-side configuration must not penetrate the W web.
45. The valid current bolt path remains through Angle Connected Leg and W Column
    Flange.
46. The W web does not enter the current direct-flange bolt path.

### I. Units

47. U.S. customary and SI remain supported.
48. One physical engineering calculation path remains authoritative.
49. Display units and rounding remain presentation-only.

### J. Viewport and axes

50. The 3D viewport supports presentation-only left-drag orbit, right-drag pan,
    wheel zoom, Fit Connection, Reset View, Front, Top, and Side.
51. Members are not drag-edited geometrically.
52. The corner global orientation triad remains the normal global orientation aid.
53. The corner triad uses X red, Y green, and Z blue, with text labels.
54. Full global axes through the joint remain optional diagnostics.
55. Selected-member local axes remain the normal default.
56. All-member local axes remain diagnostic.
57. Material axes remain explicitly labeled LW, CW, and TT.
58. Axis meaning does not rely on color alone.

### K. Action visualization and editing

59. Member-end actions remain actions applied by member to joint.
60. The six supported action components remain `Fx`, `Fy`, `Fz`, `Mx`, `My`, and
    `Mz`.
61. Positive sign-convention arrows remain separate from applied signed actions.
62. Positive convention labels remain nonnumeric and noneditable.
63. Applied-action directions come from backend canonical data.
64. Applied-action values are displayed beside their corresponding arrows or arcs.
65. All applied force components support visible values when shown.
66. All applied moment components support visible values when shown.
67. Applied-action display uses an explicit sign and two decimal places.
68. Applied-action label background remains approximately 80% transparent and 20%
    opaque.
69. Moment arrowheads remain visually attached to their arcs.
70. Clicking an applied-action value edits the same engineering input state as the
    sidebar.
71. Action editing updates the sidebar, marks design stale, triggers live preview,
    and does not automatically run design.
72. Zero-action visibility follows overlay policy.

### L. Demand source

73. Member-end action and explicit resolved Bolt 1 demand remain distinct.
74. Current software does not derive resolved Bolt 1 demand from member-end action.
75. The verified resistance slice requires independently resolved bolt demand where
    applicable.
76. Bolt-demand distribution remains unimplemented.

### M. Result presentation

77. Normal result presentation uses concise engineer-facing formatting.
78. Raw server precision remains available in the detailed trace.
79. Presentation rounding never controls PASS/FAIL, governing result, utilization
    logic, or fingerprint.
80. Section 2.3.2 qualification remains separate from numerical PASS/FAIL.
81. J1 must not show an ordinary whole-joint PASS.

### N. Current engineering boundary

82. Executable scope remains the verified single-bolt/single-row calculation slice.
83. Stage 2.1B remains the resistance-equation authority.
84. Stage 2.2A remains the design-orchestration authority.
85. Stage 2.2B remains the stateless design-API authority.
86. Stage 2.3 preview does not replace design orchestration.
87. Multirow equations, block shear, demand distribution, and prying generation
    remain future work.

## Controlled freeze-change procedure

Any future change to a frozen invariant must:

1. Identify the requested change.
2. Identify every affected freeze invariant.
3. Describe the old behavior.
4. Describe the proposed behavior.
5. Explain the engineering or product reason.
6. Analyze backward compatibility.
7. Define regression against this frozen baseline.
8. Obtain Baraa Misto approval when engineering meaning or approved workflow changes.
9. Implement under a new controlled stage.
10. Leave the original freeze tag unmoved, undeleted, and unrewritten.

## Known limitations preserved by this freeze

- Engineering coverage remains single-bolt/single-row.
- Bolt-demand distribution and multirow equations are not implemented.
- Block shear and general prying generation remain future work.
- Current unsupported cleavage boundaries remain.
- J1 Section 2.3.2 qualification remains required.
- ICE material remains development-only and engineering-review-required.
- ASTM F593 `Fnt` remains source-pending.
- Persistence, reports, authentication, authorization, and entitlement are not
  implemented in this workspace.
- Moment Connections is not implemented.
- Custom manufacturer material editing remains future work.

This record contains no licensed standards text and does not broaden the approved
engineering scope.
