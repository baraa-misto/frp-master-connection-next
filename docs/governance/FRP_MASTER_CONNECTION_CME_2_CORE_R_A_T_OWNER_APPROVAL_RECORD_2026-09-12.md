# FRP Master Connection
# CME-2 Core C2-R / C2-A / C2-T Owner/EOR Approval Record

**Date:** 2026-09-12

**Status:** APPROVED

## Approved decision

> Approved: use unwelded hot-rolled/extruded ASTM A276/A276M + A484/A484M 316-family shapes as the initial C2-A/C2-T fabrication domain; retain conservative Fy=25 ksi/Fu=70 ksi; exclude formed, laser-fused, welded/built-up and other fabrication routes; adopt the bounded C2-R trusted-response-envelope policy with reuse only of proven material-neutral transport/conservation mechanics; keep angle/Tee torsion and unqualified contact/prying/sharing fail-closed.

## Engineering effect

The approval establishes the following initial C2-core policy:

1. C2-A/C2-T stock is restricted to unwelded hot-rolled/extruded 316-family structural shapes ordered to ASTM A276/A276M plus ASTM A484/A484M.
2. Initial properties remain conservative Fy=25 ksi and Fu=70 ksi with E=28,000 ksi and G=10,800 ksi.
3. A479, cold-finished/strain-hardened, formed, laser-fused, welded/built-up, and cut-Tee routes are excluded from RC1.
4. C2-R is a trusted response-envelope/provenance authority. It may reuse only proven material-neutral transport/conservation, frozen ASCE FRP-steel prescribed row rules, narrowly applicable native response snapshots, locked native symmetry, or qualified external material-specific response.
5. Unknown material-dependent stiffness/contact/prying/sharing fails closed.
6. Angle/Tee torsion fails closed.
7. Frozen C2-M/C2-P1/C2-P2 remain unchanged and isolated.
8. Public family activation remains a later CME-3 decision.

## Additional conservative method carried forward

The frozen C2-P2 project cap is carried into every C2-core AISC 370 Curve-A use:

`Fn_used = min(Fy, Fn_raw)`.

This prevents a numerical strength increase above Fy at the lower Curve-A transition and preserves monotonic behavior.

## Frozen baseline

- Governance: `88961da28de3421722290c2bf78af0c6191b81a1`.
- Count: `130`.
- C2-P2 freeze tag: `cme-2c-c2-p2-freeze`.
- C2-P2 tag object: `7861f351e88fdfa7a65e6166dc941b2476c8e0b8`.
- C2-P2 peeled implementation: `61855bda1f76bbf11a85ae58664ed81bbc8ea419`.

## Approved benchmark authority

- Core golden SHA-256: `E89748C24CB53E25C559A7BAD2C02E442FD8A05A72DE308CA14826698C6C1938`.
- Independent validation SHA-256: `C2EAE5CC55E0EC98DA00724DDF5D2A595BF74CBCF7361EBD42E32B936CE63B95`.

## Scope boundary

This approval authorizes isolated C2-R/C2-A/C2-T implementation only.

It does not authorize:

- public 316SS selection/dispatch;
- family activation;
- frontend changes;
- public source-response ingestion;
- welding;
- C2-R nonlinear contact/stiffness solver invention;
- unsupported Angle/Tee torsion;
- fastener/foundation/FRP-member authority changes;
- whole-connection stainless PASS.
