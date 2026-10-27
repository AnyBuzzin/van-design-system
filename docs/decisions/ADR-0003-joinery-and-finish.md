# ADR-0003: Traditional CNC joinery, no visible hardware, exposed ply edges

Status: Accepted by the owner, 2026-10-26

## Decision
Furniture is held together mainly by **traditional joinery cut on a flat-bed 3-axis CNC**. Glue makes the joints permanent. Hardware adds strength only where it is needed and is **never visible from outside** a finished piece. The finish is premium: clean outer faces and **exposed, sanded plywood edges** (no edge banding or lipping).

## Joinery set (flat-bed machinable; face operations only)
| Joint | Use |
| --- | --- |
| Tab-and-slot, **blind** on visible faces (through only where hidden) | Main carcass joint: sides, tops, bottoms, dividers |
| Dado, **stopped** short of visible edges | Shelves |
| Rabbet | Backs set into sides, so no back edge shows |
| Finger (box) joint | Drawer and storage boxes |
| Half-lap | Dividers, frames, slat grids |
| Hidden connector (Lamello Cabineo, from inside faces) | Extra strength and clamping; **subject to the CNC shop confirming it can mill the pockets**. Fallback: blind tabs and glue only |

Not planned: dovetail, mitre, bridle, scarf, tongue and groove, biscuit and dowel joints, because each needs edge or angled machining or hand tools. Butt and pocket-screw joints and visible confirmat heads are excluded for appearance.

## Consequences
- Blind slots become pockets on the receiving panel's inner face. Each slot leaves a skin on the outer face, and the tab length leaves an end gap equal to the face clearance. Dog-bone relief stays hidden inside the joint.
- Exposed edges are part of the design. Visible edges need good-faced ply (for example birch, B/BB). Panel sizes have no banding allowance. The grain and face-quality direction become panel data (M4).
- **Overhead cabinets:** screw from inside the cabinet, through a fixing rail at the top and back, through the lining and into the timber battens behind it. Fixings go only where `EnvelopeSpec` mounting data shows a batten; a layout whose fixing misses a batten is refused. The fixings are hidden by the cabinet back or a cover strip. Screw size, spacing and capacity stay **unqualified** until the M7 structural review ([ADR-0002](ADR-0002-lined-interior-envelope.md): the lining is not assumed to carry crash loads).
- Physical fit and appearance are proven only in M7. Until then they are virtual: exact clearances, zero assembled overlap and DXF re-read.
