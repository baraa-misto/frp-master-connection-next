# Appendix RC3 successor artifact register

Independent from all frozen RC2 registers. Status: inactive candidate, operator authority corrected; no family migration or new freeze.

- Engine: backend/src/frp_master_connection/calculation/appendix_rc3.py
- Specification: docs/engineering/CALCULATION_SLICE_2_APPENDIX_ENGINEERING_SPECIFICATION_RC3.md (CS2-APPENDIX-RC3)
- Source transcription: docs/engineering/APPENDIX_CA8_PRINTED_EQUATION_TRANSCRIPTION_RC3.md
- Decision: docs/architecture/SHEAR01_DIRECT_OR2_A3_R1_APPENDIX_AUTHORITY_DECISION.md
- Golden: backend/tests/golden/calculation_slice_2_appendix_golden_benchmarks_rc3.json
- Independent generation/ledger: docs/qa/APPENDIX_RC3_INDEPENDENT_REFERENCE.py and APPENDIX_RC3_INDEPENDENT_LEDGER.md
- Operator/branch tests: backend/tests/calculation/test_appendix_rc3.py
- C3 parity fixture/test: backend/tests/golden/direct_a3_r1_c3_numerical_parity.json and backend/tests/api/test_appendix_rc3_direct_parity.py
- Platform evidence: scripts/generate_appendix_rc3_ci_evidence.py
- Workflow identity normalization: backend/tests/application/test_wi_wall_moment.py (exact new workflow hash; historical assertions retained)
- Call-site inventory: docs/qa/SLICE2_APPENDIX_RC3_CALL_SITE_INVENTORY.csv

Configured counts: backend 8278 (8129 predecessor +149 new); frontend 1259 unchanged. CI still four platform jobs. 100% configured coverage and exact-SHA CI remain publication gates. Engine/spec/golden identity and predecessor linkage are recorded in engine trace and golden metadata.
