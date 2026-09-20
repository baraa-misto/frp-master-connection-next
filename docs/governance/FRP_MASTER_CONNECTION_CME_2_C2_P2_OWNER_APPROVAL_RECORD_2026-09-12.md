# FRP Master Connection
# CME-2 C2-P2 Owner/EOR Approval Record

**Date:** 2026-09-12  
**Status:** APPROVED

## Approved decision

> Approved: C2-P2 bounded clear-plate E3/F9/H2 method policy with Cb=1.0 default and fail-closed E4/shear/torsion boundaries.

## Lock closed

`SL-C2P2-BOUNDED-METHOD-POLICY = CLOSED_OWNER_EOR_APPROVED_2026_09_12`

## Approved engineering meaning

The approval adopts all of the following as the initial bounded C2-P2 project method:

1. a qualified hole-free clear strip through an unwelded A240 stainless plate may be evaluated geometrically as a solid rectangular cross-section for ANSI/AISC 370-25 F9 in-plane flexure while retaining A240/A480 product provenance;
2. compression uses ANSI/AISC 370-25 E3 Curve A for both principal flexural-buckling axes only when trusted stability authority explicitly qualifies E4 torsional/flexural-torsional buckling as not controlling;
3. ANSI/AISC 370-25 H2 is used in lieu of H1 for the initial axial-force plus in-plane-flexure interaction;
4. `Cb = 1.0` is the automatic conservative value unless a trusted F1 moment profile qualifies a larger source-derived value, not exceeding the approved F1 limit;
5. Appendix 2 Continuous Strength Method / strain-hardening strength enhancement is excluded;
6. E4-required or unresolved compression, torsion, biaxial flexure, out-of-plane flexure, and combined normal-plus-shear requests fail closed;
7. C2-P2 consumes already-resolved factored resultants and never creates an authoritative moment from a raw eccentricity;
8. public family stainless activation remains prohibited.

## Authority boundary

This approval permits promotion of the C2-P2 RC1 Candidate artifacts to **approved RC1 implementation authority for an isolated internal C2-P2 provider**.

It does not authorize:

- activation of 316 Stainless Steel in existing connection families;
- C2-R material-dependent response redistribution;
- common-fastener response, prying, or contact;
- C2-A angle resistance;
- C2-T Tee resistance;
- welding/fabricated-shape methods;
- fastener, anchor, concrete, support, or FRP-member authority changes;
- whole-connection stainless PASS;
- CME-3 family activation.

## Frozen baseline carried forward

- repository governance baseline: `20fabefa90247dd3470d4698edda1b22d017e7c6`;
- commit count: `128`;
- frozen C2-M/C2-P1 implementation: `7ef49bdbf8b9704af3d314735963069ddf7259f3`;
- freeze tag: `cme-2b-c2-m-c2-p1-freeze`;
- freeze tag object: `2c585478586b4abc56bf393e77d46f38097b3df4`.

The frozen C2-M/C2-P1 implementation shall not be modified by the C2-P2 implementation stage.
