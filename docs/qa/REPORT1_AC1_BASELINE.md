# REPORT1-AC1 published baseline reproduction

Baseline: `eae3374dd0af26e93e8b1bb02265eafecb68e5ec`.

This record separates post-publication reporting defects from native engineering states.

1. **Navigation:** pypdf resolved all 105 outlines and 106 internal links in the five supplied PDFs to page 1, including sections whose headings begin on later pages. The numbered replay canvas registers anchors during its first pass, before final pages are emitted.
2. **Figures:** Direct orthographic views show only overall projected extent; the multi-row plan and elevation show boundary coordinates but no pitch, gauge, end/edge, bolt/hole, or thickness dimension witnesses. The current drawing functions contain no such witnesses.
3. **Substitutions:** The executed `FIRST_ROW_SIMPLIFIED`, `INTERROW_ASCE_EQ_8_12`, and `BLOCK_SHEAR_ASCE_EQ_8_14A` examples display `Native factor-stage substitution unavailable`. The renderer looks for `nominal_resistance`, `phi`, etc. at the top level while the native multi-row factor trace names `equation_nominal_resistance`, `resistance_factor_phi`, etc.; formula inputs are present in `equation_trace` but no worked formula is formatted.
4. **Units:** The published U.S. multi-row PDF places `2.5 kip` demand and N-valued resistance in the same engineer-facing check detail. `_quantity` formats each native quantity without applying the selected display unit; equivalents are appended separately.
5. **Evidence:** The supplied review ZIP contains PDFs of 67, 51, 559, 217, and 25 pages = 919 pages. It omits the existing 40-page `report1-mat1-custom-synthetic.pdf` (SHA-256 `24ED096CCEA20BEC9374028A75261073BD9A67223983961BC0BF8CF1CA34469E`) that produced the stated 934-page total.
6. **Pagination:** The 559-page W/I support PDF has only `Calculation identity` and footer on page 3. Individual contents paragraphs split after page 2, immediately followed by a forced page break.

All six were reproduced read-only against published bytes before correction.
