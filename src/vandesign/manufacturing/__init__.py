"""Manufacturing geometry: flat panel profiles, CNC relief and DXF output.

CAD-neutral and millimetre-only. A ``PanelProfile`` is the finished 2D shape
of one plywood part (outline, through-cuts, pockets, holes) plus its
thickness. It is manufacturing geometry, NOT a toolpath: tool-radius offset,
lead-ins, tabs and nesting stay with downstream CAM/nesting software.
"""
