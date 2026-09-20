# Stage 3.7A Stage 3.5 Freeze Successor-Change Record

## Scope

Stage 3.7A is an additive successor to the immutable Stage 3.5 Concrete-Support
Shear Family. It expands the current Column connection from the historical W/I
Single/Double matrix to W/I, RHS, SRS, and Angle columns with Single and Double
base-angle assemblies under strict successor contract `3.7A-RC1`.

The annotated tag `stage-3.5-concrete-support-shear-family-freeze`, its target,
manifest, historical contracts, results, and fingerprints remain unchanged. The
successor does not reinterpret any `3.5C-RC1` or `3.5C-R2-RC1` request.

## Shared symbols changed

- `domain.member_profile` adds one shared exact member-axis reference resolver;
  the existing direct-side-lap centroid helper delegates to the same authority.
- `domain.column_base_web_angles` and `domain.__init__` add the strict successor
  request and the distinct `DOUBLE_BASE_ANGLES` assembly identity while retaining
  the historical symmetric-double identity.
- `application.column_base_web_angle_orchestration` dispatches only the successor
  request to the new profile-matrix orchestration; historical requests keep the
  accepted implementation path.
- Column-base API schemas/mapping and the existing two stateless endpoints accept
  the discriminated successor request without adding a route.
- The existing Column-base workspace, client, benchmark loader, and scene adapter
  expose the additive profile/assembly matrix through one request state.

All engineering geometry, action/reference translation, physical paths, demands,
statuses, handoff records, and fingerprints for Stage 3.7A are backend-authored.
The frontend adds no frame, centroid, path, wrench, or resistance authority.

## Frozen-family proof

- Historical Stage 3.5C/R1/R2 W/I requests, results, geometry, material bases,
  and fingerprints remain exact.
- Every Stage 2.3, Stage 3.2, Stage 3.3, Stage 3.4, Stage 3.5, and Stage 3.6 freeze
  manifest, tag object, and target remains exact.
- Direct, Tee, Single/Paired Clip-Angle, Multi-Member Tee, and W/I Web-Splice
  behavior remains outside this successor's dispatch path.
- Package, lock, dependency-tree, and workflow identities do not change.

## Authorized transition

Only the new `3.7A-RC1` engineering and application fingerprints are introduced.
RHS uses one exterior-head-to-exterior-nut full-through bolt with near wall,
non-material cavity, and far wall; SRS uses one continuous solid material layer.
Angle Double places two connectors on opposite broad faces of the same selected
leg and retains the actual member centroid/reference. A different-leg Angle moment
topology is planned only and was not begun.

No equation, resistance method, concrete/anchor capacity, bolt-axis/prying method,
dependency, workflow, persistence, report, or tag transition is authorized.
