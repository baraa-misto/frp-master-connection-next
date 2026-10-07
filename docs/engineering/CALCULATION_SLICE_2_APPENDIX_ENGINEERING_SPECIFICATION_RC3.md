# CS2-APPENDIX-RC3 engineering specification

Status: inactive operator-correction successor, prepared under SHEAR01-DIRECT-OR2-A3-R1. This specification neither freezes nor activates a connection.

Engine identity: `asce74-23-ch8-multirow-appendix-corrected-rc3.dev1`.
Method: `FIRST_ROW_COMMENTARY_FULL_PRINTED_THETA_RC3`.
Golden: `calculation-slice-2-appendix-golden-rc3`.
Predecessor: `asce74-23-ch8-multirow-rc2.dev1` (historical full Appendix primitive and factor assembly).

## Authority and exact change

The owner adopts printed Appendix CA8-2/4/7/9 over the RC2 power transcription. Only the ratio/Theta operation is corrected: r*Theta replaces exp(Theta*ln(r)). Concise visually verified grouping and source hashes appear in APPENDIX_CA8_PRINTED_EQUATION_TRANSCRIPTION.md. Original RC2 source/spec/golden and historical governance remain immutable.

## Inputs, domain and arithmetic

The function accepts typed positive length quantities w,d,dn,t,e1 and g for two/three bolts across width, an existing EndUsePropertyTrace, typed direction/classification, supplied Lbr, and supplied accepted lap/pitch/time factors. It admits exactly two/three longitudinal rows and one/two/three bolts across width. Boolean/noninteger counts, >3 ranges, nonpositive/wrong-dimension quantities, w<=n*d, w<=n*dn, Spr<=1, missing gauge and Lbr outside [0,1] fail explicitly. Source-valid width, physical stress applicability and demands must be established separately by an approved caller. No Direct width, load path or eccentric stress is inferred.

The printed coefficient grouping and exact <= branch are evaluated at the existing 60-digit precision. Kop=1+Cop*(1+(1-1/Spr)^3), A=Knt*w/(nd), B=Kop/(1-n*dn/w), Rn=w*t*Ft/(A*Lbr+B*(1-Lbr)). Existing RC2 factor assembler applies Clap, Cdelta, phi, lambda once. Phi L=0.50, T=0.45. All material/end-use traces and qualification statuses remain supplied historical evidence. The function emits no demand, utilization, governing check or aggregate design status.

No Lbr inference is added. Golden rows use unchanged Table C8-1 values 0.5 (two rows), 0.4 (three rows). Endpoint tests assert unchanged algebra, without activating rational >3-row extensions. Kop/Cop and accepted plate policy stay unchanged. The transverse-plate policy notice is explicit; this successor does not silently claim broader printed-coefficient reconciliation.

## Trace and isolation

AppendixRC3Trace records distinct engine/spec/golden/parent/method IDs, source equation/page, all input quantities, row/bolt counts, branch, Spr/Theta/ratio/product, Knt/Kop/A/B/denominator and existing factor/property trace. It has no ratio_power field. No production module imports this successor. The frozen calculation public exports remain unchanged. Dedicated tests and a CI evidence generator are the only invocations.

## Verification and migration

60 independently calculated geometries cover L/T x n=1/2/3 x rows=2/3 x nonunit/unit/below/exact/above boundaries. Each is executed in U.S./SI, with raw exact parity and the existing 1E-12 ROUND_HALF_EVEN golden serialization. Boundary offsets are test operands, not engineering tolerances. Additional dual-history, plate, endpoint and invalid-input tests require 100% successor coverage. A separate C3 fixture locks all seven current Direct evaluated traces, seven unsupported rows and one qualification-incomplete row; two neutral rows and all 17 scheduled IDs remain.

Generic multi-row full and >3 rational endpoint routes retain RC2 and are SOURCE_CORRECTION_MIGRATION_REQUIRED. Other adapters remain unchanged. F6 must resolve effective width and eccentric stress/demand handoff before any Direct activation. No migration, first-row result, W interrow/block result, qualification relaxation, main merge or tag is authorized here.
