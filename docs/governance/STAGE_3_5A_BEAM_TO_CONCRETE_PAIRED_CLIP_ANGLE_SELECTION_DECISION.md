# FRP Master Connection — Stage 3.5A Beam-to-Concrete Paired Clip-Angle Selection Decision

## Decision

The next controlled shear-connection stage is:

**Stage 3.5A — FRP Beam to Concrete Wall Using Symmetric Paired FRP Clip Angles**

Normal product label:

**Beam connection — Paired clip angles to concrete wall**

This is the first vertical slice of a planned, but not yet fully controlled, concrete-support shear-connection family.

## Physical topology

The controlled physical chain is:

`FRP W/I Beam Web -> Common Through-Bolt Group -> Symmetric Paired FRP Clip Angles -> Two Mirrored Wall-Anchor Groups -> Concrete Wall`

- The beam is horizontal and frames normal to one concrete-wall face.
- One FRP clip angle is placed on each side of the beam web.
- The beam-side group is one physical common through-bolt group.
- Each clip-angle wall leg has its own mirrored anchor group.
- The two clip angles and wall-anchor groups are locked identical and mirrored in RC1.
- The concrete wall is represented as a finite physical support surface.
- The concrete wall, concrete resistance, anchor steel, anchor resistance, and anchorage system are not designed by FRP Master Connection.

## Shear-only classification

Stage 3.5A remains in the Shear Connections category.

The user applies one signed vertical reaction shear only.

The following are not user-applied in RC1:

- member-end moment;
- axial force along the beam;
- horizontal shear along the wall;
- out-of-plane force;
- torsion.

This is not a moment connection.

However, exact moments created by translating the reaction shear from the beam reference point to the wall-anchor reference points shall be retained in the external anchor-design handoff. These are geometry-induced transfer moments, not a user-applied or moment-resisting connection action.

## Equal branch sharing

The accepted Stage 3.3B paired-angle symmetry/action proof remains controlling.

RC1 locks:

- identical clip angles;
- centered W/I beam;
- identical mirrored wall-anchor groups;
- pure vertical reaction shear;
- symmetric material/source identity.

When the proof passes, each clip-angle branch receives exactly one-half of the beam reaction.

No tolerance-based or profile-name-only sharing inference is permitted.

## Concrete and anchor design boundary

FRP Master Connection shall provide an explicit external anchor-design handoff containing:

- wall local frame and sign convention;
- factored combined wall-interface wrench;
- positive and negative anchor-group wrenches at their own centroids;
- anchor coordinates;
- wall-face geometry and geometric edge distances;
- nominal anchor diameter;
- FRP hole diameter;
- user-specified coordination embedment depth;
- clip-angle wall-leg thickness;
- load-case identity;
- units;
- geometry/application fingerprints.

The specialized anchor-design software remains responsible for:

- anchor force distribution verification;
- anchor steel strength;
- concrete breakout;
- pullout;
- pryout;
- side-face blowout where applicable;
- concrete edge and spacing capacity;
- supplementary reinforcement;
- seismic qualification;
- adhesive/post-installed/cast-in-place qualification;
- concrete member adequacy.

No anchor or concrete capacity is issued by Stage 3.5A.

## Connector and beam checks

The existing accepted beam-side paired clip-angle mechanics may execute where their current applicability contracts hold.

Wall-side nominal group demand may be resolved for FRP-side traceability under the accepted rigid-group mechanics, but it is not an anchor-system design result and does not supersede the external anchor software.

## Required limitations

At minimum:

- `PAIRED_CLIP_ANGLE_BODY_RESISTANCE = NOT_EVALUATED`;
- `COMMON_THROUGH_BOLT_DOUBLE_SHEAR_RESISTANCE = NOT_EVALUATED`;
- `PAIRED_CLIP_ANGLE_BRANCH_COMPATIBILITY = NOT_EVALUATED`;
- `PAIRED_FRP_CLIP_ANGLE_QUALIFICATION = NOT_EVALUATED`;
- `CONCRETE_SUBSTRATE_RESISTANCE = EXTERNAL_DESIGN_REQUIRED`;
- `ANCHOR_SYSTEM_RESISTANCE = EXTERNAL_DESIGN_REQUIRED`;
- `ANCHOR_STEEL_RESISTANCE = EXTERNAL_DESIGN_REQUIRED`;
- `ANCHOR_CONCRETE_LIMIT_STATES = EXTERNAL_DESIGN_REQUIRED`;
- `EXTERNAL_ANCHOR_DEMAND_VERIFICATION = REQUIRED`;
- `SIMPLE_CONNECTION_ROTATIONAL_CAPACITY = NOT_EVALUATED`.

Known supported numerical failure retains overall `FAIL` precedence.

Ordinary whole-connection `PASS` is prohibited.

## Source boundary

ASCE/SEI 74-23 treats single or paired clip angles as simple frame connections, proportions simple framing connections for reaction shear only, and requires FRP clip-angle connection qualification under Section 2.3.2. The standard does not provide anchor-system design authority for this product slice. Erratum 1 was reviewed and does not change the relevant Chapter 8 provisions.

## Future planned sequence

Subject to later owner approval:

- Stage 3.5B may add direct side-lap Channel/Angle to concrete wall using the same wall/anchor handoff.
- A later shear-only column-base stage may reuse the same concrete/anchor boundary.
- No moment-resisting concrete connection is authorized.

**END OF STAGE 3.5A BEAM-TO-CONCRETE PAIRED CLIP-ANGLE SELECTION DECISION**
