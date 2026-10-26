"""Manufacturing profiles for the existing modules at their default specs."""
from __future__ import annotations

from dataclasses import replace

from ..core.tab_slot import RECEIVER, UPRIGHT
from ..modules.bed_platform import build_bed_platform
from ..modules.cabinet import build_cabinet
from ..modules.rounded_panel import build_rounded_panel
from ..modules.storage_box import build_storage_box
from ..modules.tab_slot import build_tab_slot
from ..schemas.bed_platform_spec import BedPlatformSpec
from ..schemas.cabinet_spec import CabinetSpec
from ..schemas.rounded_panel_spec import RoundedPanelSpec
from ..schemas.storage_box_spec import StorageBoxSpec
from ..schemas.tab_slot_spec import TabSlotSpec
from .assembly import assembly_profiles

MODULES = ("cabinet", "bed", "storage-box", "rounded-panel", "tab-slot-coupon")


def tab_slot_profiles(spec=None, *, tool_diameter=None):
    """E1.2 coupon: slot (with the model's own relief) and upright tab notches.

    Relief uses the coupon's tool diameter unless overridden. The upright's
    tab-root inside corners also receive dog-bones: without them a round tool
    leaves root fillets that stop the shoulders seating on the receiver.
    """
    coupon = build_tab_slot(spec or TabSlotSpec())
    g = coupon.geometry()
    d = tool_diameter or g.tool_diameter
    cuts = [(UPRIGHT, s) for s in g.shoulders] + [(RECEIVER, g.slot)]
    out = []
    for p in assembly_profiles(coupon.blanks, tool_diameter=d, extra_cuts=cuts):
        if p.panel_id == RECEIVER and d == g.tool_diameter:
            # The E1.2 model already contains these four relief circles.
            p = replace(p, notes=("slot relief identical to the E1.2 CAD relief circles",))
        out.append(p)
    return tuple(out)


def module_profiles(name, *, tool_diameter, relief=True):
    if name == "cabinet":
        asm = build_cabinet(CabinetSpec())
    elif name == "bed":
        asm = build_bed_platform(BedPlatformSpec())
    elif name == "storage-box":
        asm = build_storage_box(StorageBoxSpec())
    elif name == "rounded-panel":
        asm = build_rounded_panel(RoundedPanelSpec())
    elif name == "tab-slot-coupon":
        if not relief:
            raise ValueError("The tab-slot coupon is only manufacturable with relief")
        return tab_slot_profiles(tool_diameter=tool_diameter)
    else:
        raise ValueError("Unknown module %r; choose from %s" % (name, ", ".join(MODULES)))
    return assembly_profiles(asm, tool_diameter=tool_diameter, relief=relief)
