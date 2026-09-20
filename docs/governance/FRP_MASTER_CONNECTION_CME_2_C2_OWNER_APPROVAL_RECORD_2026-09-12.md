# FRP Master Connection
# CME-2 C2 Owner Engineering Decision Record — 2026-09-12

**Status:** External project engineering decision record. Not a Codex implementation order and not a repository mutation.

## Approved decisions

The owner approved the following C2-M/C2-P1 engineering decisions on 2026-09-12:

1. **Stainless code-basis bridge**
   - ANSI/AISC 370-25 is adopted as the stainless connector-body component design basis for the bounded CME-2 stainless provider work.
   - ASCE/SEI 74-23 remains authoritative for FRP members, FRP interfaces, FRP connection applicability, and all frozen native FRP behavior.
   - AISC 360-22 remains a comparison/reference bridge and is not the stainless numerical body provider.
   - This project decision does not replace any project-specific EOR adoption required for issued engineering work.

2. **Conservative 316SS project material snapshot**
   - User-facing material remains `316 Stainless Steel`, accepting common client terminology including `316SS`, `316`, `316L`, and `316/316L`.
   - Initial C2-P1 design properties are project-controlled U.S.-source values `Fy = 25 ksi` and `Fu = 70 ksi`.
   - Exact certified grade/dual certification remains provenance.
   - No higher S31600 minimum, MTR overstrength, cold-work strength enhancement, or strain-hardening credit is taken in C2-P1.
   - The software must identify these values as a project-controlled conservative engineering snapshot and must not claim they were directly extracted from the final ASTM A240/A240M-26 table.

## Not approved / still open

The owner did **not** waive the final ANSI/AISC 370-25 detailed-text reconciliation. `SL-370-25-FINAL` remains open. The RC1 candidate package is therefore not yet Codex implementation authority.

## Hardware boundary

Bolts, nuts, and washers remain the project's independent 316 stainless hardware system. Their existing fastener authority shall not be replaced by connector-body `Fy`/`Fu` values.
