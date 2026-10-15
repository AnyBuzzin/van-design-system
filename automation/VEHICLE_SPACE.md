# Simplified vehicle space (runner 0.4.0)

The existing FirstInteriorDemo job accepts optional `vehicle_mm` alongside
`layout_mm`. Omitting it retains previous geometry/parameters. Values are finite
millimetre numbers; unsupported keys, strings and booleans are refused.

| Input | Meaning |
| --- | --- |
| Van_Width / Van_Length / Van_Height | Rectangular envelope, same X/Y/Z datums as earlier demos |
| Arch_Width / Arch_Length / Arch_Height | Shared rectangular intrusion dimensions |
| Arch_Left_Y / Arch_Right_Y | Independent longitudinal positions; arches anchored to the floor top and inner side walls |
| Min_Aisle | Minimum straight clear width to the right of the kitchen over its complete longitudinal footprint |

The shell retains 18 mm floor/sills; usable X is 18..Van_Width-18, rear Y ends
at Van_Length-18, and usable Z begins at 18. These are simplified fixture
construction datums, not measured vehicle dimensions. Bed width, length, height
and kitchen position remain existing layout inputs.

Preflight checks all furniture inside the envelope, occupied furniture overlap,
arch containment and non-overlap, no cabinet occupied-volume/arch intersection,
and no bed deck/support material intersecting arches. Arches can occupy free
space under the bed. Aisle computation accounts for vehicle/furniture intrusions
where their Y ranges intersect the kitchen strip. It does not certify entry,
headroom, turning, wheelchair access, door swing or a route through the rear bed.

Two visible bodies reuse parametric panel generation, IDs van.arch_left.001 and
van.arch_right.001. No boolean cuts were added; existing cabinet joinery and
explicit cut participants remain unchanged. The new profile has 17 panel bodies.
Actual BRep boxes/volumes and interference are measured, and aisle/arch constraints
are independently recomputed from those measured boxes before save.

Example vehicle inputs: Van_Width=2100, Van_Length=4600, Van_Height=2200,
Arch_Width=250, Arch_Length=800, Arch_Height=300, both arch Y=3000, Min_Aisle=600.
Example layout: bed width=1700, length=2000, height=750; kitchen X=100/Y=500.
Expected aisle=782 mm; bed deck underside is 432 mm above arch tops.
Kitchen X=400 instead deliberately fails the 600 mm aisle requirement (482 mm).

Compatibility: earlier default/configured designs retain their existing parameter
sets. Read-only persistence reconstructs configured assemblies from their live
explicit parameters; it never adds missing parameters or migrates an old design.
Runner 0.4.0 validates the vehicle argument and extended geometry evidence.
Previously saved documents are never adopted for builds or overwrites.

Evidence is in evidence/vehicle-usable-space. No real vehicle fit, structural,
road-legal, manufacturing or production approval is claimed.
