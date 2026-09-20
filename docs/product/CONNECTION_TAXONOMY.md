# Connection Taxonomy

## Purpose

This controlled taxonomy classifies a `JointAssembly` without reducing a complete joint to a single hard-coded template name. Classification supports selection, capability declarations, filtering, reporting, and future template guidance. It never implies that a geometry is calculation-supported.

## Hierarchy

### Level 1 — Design category

Level 1 contains exactly two values:

- **Shear** — user-facing label: **Shear Connections**. This category may include non-moment-resisting brace connections.
- **Moment** — user-facing label: **Moment Connections**. A Moment Connection contains at least one intentionally moment-resisting interface and includes both moment and shear analysis and design.

No third Level-1 category or catch-all value is permitted. A complex joint still receives one of these two classifications; its detailed character is expressed at lower levels.

Stage 3.5A registers **Beam-to-Concrete Wall — Paired FRP Clip Angles** as a
separate Shear connection product type. Its support is a finite concrete wall rather
than a profile surface, its two wall interfaces terminate in explicit external
anchor-design handoffs, and its user action surface contains signed vertical reaction
shear only. This registration does not classify the connection as having evaluated
concrete or anchor capacity.

### Level 2 — Joint family

Describes the connected-member role pattern, without prescribing a proprietary template. Examples include brace-to-column, brace-to-beam, beam-to-column, and beam-and-braces-to-column.

### Level 3 — Assembly topology

Describes the participating member instances, their spatial arrangement, and whether load transfer uses direct interfaces, connecting components, or both. Examples include one angle brace approaching a column flange, an angle connected to the back of a channel beam, and one beam plus two braces sharing a column joint.

### Level 4 — Interface method

Describes each physical load-transfer interface. Controlled concepts include direct member-to-member bolting and member-to-connecting-component bolting. A joint may use both. A directly bolted interface does not receive an artificial connector.

### Level 5 — Optional reinforcement

Describes explicit reinforcement components such as a doubler and its host face, side, geometry, material orientation, layers, attachment classification, and structural-credit classification. Presence of reinforcement does not imply structural credit; the credit method and qualification must be supported.

### Level 6 — Bolt arrangement

Describes bolt groups and ordered bolt stacks using canonical bolt centers, penetrated layers, holes, head/nut/washer arrangement, grip, shear planes, bearing layers, alignment, access, and interference. The arrangement is shared by calculations, holes, 3D, 2D, dimensions, and reports.

## Classification rules

- The taxonomy classifies the joint and its physical topology; a separate capability record states geometry support and calculation support.
- A `JointAssembly` may contain multiple members, directions, inclinations, interfaces, connecting components, reinforcements, and shared regions.
- T-sections are first-class `ConnectingComponent` instances and may be shared by a beam and multiple braces.
- Direct and connector-assisted interfaces may coexist in one assembly.
- Shared connectors and shared supporting-member regions retain explicit identities so combined demand can be evaluated where applicable.
- Combined moment and shear are not modeled as unrelated when interfaces share components or FRP regions.
- A classification is not a code-coverage claim, a material qualification, a validated load path, or an engineering result.

## Baseline examples

| Level 1 | Joint family | Assembly topology | Interface method | Optional reinforcement | Bolt arrangement |
|---|---|---|---|---|---|
| Shear | Brace-to-column | Direct angle brace to W-section column flange | Direct bolted | As defined by approved capability | Explicit bolt group and ordered stacks |
| Shear | Brace-to-beam | Angle-column leg directly connected to the back of a channel beam | Direct bolted | As defined by approved capability | Explicit bolt group and ordered stacks |
| Shear | Beam-and-braces-to-column | One shared T connecting one beam and two braces | Connector-assisted, with direct interfaces permitted elsewhere in the joint | Optional explicit doubler | Interface and shared-component bolt groups with ordered stacks |
| Moment | Beam-to-column | Moment-resisting beam interface with optional braces | Supported direct and/or connector-assisted methods | Optional explicit doubler | Explicit interface and shared-region arrangements |

These examples are roadmap classifiers, not implemented templates or supported calculations. Source mapping, applicability, independent verification, and engineering approval are required before calculation support.
