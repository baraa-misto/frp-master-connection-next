# Stage 3.3C1 shared-platform Stage 3.2 freeze change

## Accepted baseline

Stage 3.3C1 starts from accepted clean `main` commit
`cb87761bf4298cd78f6b538e5fe2c84a385fd780`. The immutable
`stage-3.2-tee-connection-freeze` tag remains at
`d16b354732c90bf3bf7847c62be652c230a9f91e`; the historical freeze manifest is
unchanged.

## Exact shared symbols

The shared member-profile module gains only the dormant
`MemberProfileFamily.SOLID_RECTANGULAR_SECTION`,
`SolidRectangularProfileDimensions`, its exact four exterior surfaces, and its adapter
to the existing solid-prism geometry kernel. The shared application adapter gains only
the matching distinct-family dispatch. Domain exports add C1 symbols without changing
existing defaults or accepted request vocabularies.

Historical `resolve_profile_wall_bolt_path` remains unchanged and continues to own the
accepted R8 single-wall RHS behavior, including
`INTERNAL_FASTENER_ACCESS_REQUIRED`. The new C1 full-through target uses a separate
physical-path contract and does not silently supersede historical callers.

## Dormant-extension boundary

No Tee, Direct, single-angle, or paired-angle request schema, API route, production UI
selector, orchestration branch, calculation equation, result aggregation, or canonical
fingerprint payload consumes the new C1 profile or support registry. The physical path
keeps free cavity spans separate from the accepted resistance material-layer list.

Frozen Tee geometry change: `NONE`.

Frozen Tee result change: `NONE`.

Frozen Tee fingerprint change: `NONE`.

Stage 3.3A geometry/result/fingerprint change: `NONE`.

Stage 3.3B geometry/result/fingerprint change: `NONE`.

## Required evidence

Complete backend, frontend, integrated, controlled-hash, dependency, freeze-audit, and
depth-one object-isolated gates must remain green. The active frontend production tree,
package/lock identities, workflows, and both immutable freeze tags must remain exact.
