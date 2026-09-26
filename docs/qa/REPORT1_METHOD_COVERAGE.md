# REPORT1 executed-method coverage

This is a presentation registry for the sealed native response. It does not
add a resistance equation or qualify a source-limited check. The current
18-mode/36-PDF audit is `test_report1_ac1_all_modes.py`; varied-value and
missing-operand tests exercise the adapters independently.

| Executed method group | Report adapter | Numerical evidence |
| --- | --- | --- |
| Direct bolt tension, shear, combined tension/shear, pull-through, pin bearing, net tension, shear-out, cleavage | `reporting.substitutions.single_native_substitutions` and native factor trace | Native consumed operands, factor stages, demand, resistance and result |
| Multi-row pin bearing | `reporting.multirow_substitutions.multirow_native_substitution` | Identified ply thickness, bolt diameter, adjusted property, thread factor and native nominal |
| `FIRST_ROW_SIMPLIFIED` | Same multi-row adapter | `0.2 × width × thickness × adjusted tensile property = native nominal`; native factor stages follow |
| `FIRST_ROW_COMMENTARY_FULL`, `FIRST_ROW_RATIONAL_LOWER_ENVELOPE` | Same multi-row adapter | Native coefficient/denominator or both native envelope endpoints and selected lower design resistance |
| `INTERROW_ASCE_EQ_8_12`, `INTERROW_ASCE_EQ_8_13`, `INTERROW_RATIONAL_EXTENSION_EQ_8_13` | Same multi-row adapter | Native end/hole/pitch, ply and adjusted shear-property operands; native nominal |
| `BLOCK_SHEAR_ASCE_EQ_8_14A`, `BLOCK_SHEAR_ASCE_EQ_8_14B` | Same multi-row adapter | Native net areas, adjusted properties, branch coefficient, shear/tension components and nominal |
| W/I and Channel region resultant decomposition | `reporting.method_substitutions.native_method_substitution` | Native action, region area/centroid/inertia, component force/moment and equilibrium record |
| Channel thin-wall shear center | Same method adapter plus identified source geometry | Native `d`, `b_f`, `t_w`, `t_f`, median dimensions/inertia and resulting offset |
| Balanced flange-face and Channel web-face couple decomposition | Same method adapter | Native physical force lines, signed actions, resulting face forces and residuals |
| Angle connector interface wrench and exact in-plane bolt-group demand | Same method adapter | Native source/target wrenches, exact rational centroid/polar/bolt operands and recovery values |
| Longitudinal plate tension and web-splice body interaction | Same method adapter | Native area, property/stress stages, resistance factors, critical fiber and utilization |
| Clip-angle instep shear and support-side FRP bearing | Same method adapter plus identified connector thickness/bolt geometry | Native adjusted property, physical dimensions, nominal/factor/design stages and utilization |
| DCTN axial symmetric half-share response | Same method adapter | Native row fractions, two side shares, shaft transfers/cuts, plane demand and residual |
| SSMC analytical single-lap orchestration and actual polygon cut | Same method adapter | Native action/reaction, finite cut area/inertia, signed loads and demand-only stresses |

The generic method registry is `reporting.method_records.EXECUTED_METHODS`.
`test_report1_ac1_method_bindings.py` requires an exact binding for every
registered executed method and proves that varied native values change the
report substitution. `test_report1_ac1_adapter_fail_closed.py` removes native
multi-row operands and verifies a clear adapter error. The full native results
appendix retains every repeated component/path/case, including nongoverning
checks. An executed method with no adapter stops export; an unevaluated native
check remains visibly unevaluated.
