# Frontend

Stage 2.3 provides a private React/TypeScript engineering development workspace with
exactly two primary category controls. Shear Connections opens the verified
single-bolt/single-row workflow; Moment Connections remains visibly not implemented.
The Shear workspace provides J1 U.S./SI input loaders, supported member/bolt/load/
factor inputs, explicit and member-end demand modes, a typed same-origin API client,
server-authoritative results, and canonical Three.js visualization in 3D, Front, Top,
and Side views.

The workspace is session-only and implements no project persistence, report,
authentication, entitlement, billing, analytics, approved bolt-demand distribution,
multirow equations, block shear, generated prying, or frontend engineering formula.
J1 remains whole-connection qualification-required; ICE and F593 source limits remain
visible.

From the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\frontend-bootstrap.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\frontend-check.ps1
```

From `frontend/`:

```powershell
npm run dev
npm run build
npm run preview -- --host 127.0.0.1
```

The Vite development proxy targets `http://127.0.0.1:8000` by default. A loopback
backend on another port may be selected for local smoke work before `npm run dev`:

```powershell
$env:FRP_MASTER_API_PROXY_TARGET = "http://127.0.0.1:8001"
```

This setting affects only the development proxy; the browser client retains the
same-origin `/api/v1` contract.

The development runtime is provisionally fixed to Node 24.18.0 and npm 11.16.0. The
package is private and intentionally has no independent version. Backend response
metadata supplies authoritative engine, rule-set, contract, status, and fingerprint
information. This frontend is an untrusted client and is not a validated whole-
connection design tool.

`package-lock.json` is the authoritative exact resolved dependency tree and `npm ci`
is the controlling install/reproducibility command. Stage 2.3 adds exact `three`
0.185.1, `@react-three/fiber` 9.7.0, and `@types/three` 0.185.3 only. It adds no Drei,
CSS framework, state library, decimal package, router, API-client framework, or CAD/
geometry library.

The Stage 2.3 frontend suite contains 48 tests and passes 100% statements (335/335),
branches (188/188), functions (155/155), and lines (276/276) for the configured
executable boundary. ESLint, strict
TypeScript, production build, exact dependency-tree validation, full/runtime audits,
integrated repository QA, and a loopback browser smoke are controlled completion
gates. WebGL is mocked in tests while the pure scene model is fully covered and the
Canvas adapter is build/type/lint verified. This evidence does not establish
commercial engineering validation. Real-browser screen-reader, automated contrast,
browser zoom, and real-device accessibility validation remain future controlled work.
