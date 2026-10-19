"""Fixed visual fixture, not measured vehicle geometry or a new layout system."""
from dataclasses import replace
import hashlib
import math
from ..core.expr import Param
from ..core.geometry import Box, BoxExpr
from .storage_box import build_storage_scene, envelope, preview_storage
from .test_envelope import preview_fit, ARCHES, REFERENCE


def build_dimensioned_cutaway():
    scene = build_storage_scene()
    panels = tuple(replace(p, display_name="TEST ONLY - UNMEASURED right wall",
        box=BoxExpr(p.box.origin, p.box.size[:2]+(Param('Test_Height'),)))
        if p.stable_id == 'reference.right' else p for p in scene.panels)
    return replace(scene, assembly_id='test.dimensioned_cutaway.001', panels=panels,
        spec_hash=hashlib.sha256((scene.spec_hash+'full-height-right-wall-v1').encode()).hexdigest())


def dimension_labels(assembly, report):
    """Static measured snapshot labels; never present specification alone as measured."""
    if report.get('outcome') != 'PASS': raise ValueError('Verified live report required')
    env = report['parameters_mm']
    boxes = {k:Box(tuple(v['min']),tuple(v['max'])) for k,v in report['bodies'].items()}
    # Both guards require the complete finite object set, not just the displayed subset.
    fit = preview_fit(assembly,env,boxes)
    gaps = preview_storage(assembly,env,boxes)
    for panel in assembly.panels:
        actual, expected = boxes[panel.stable_id], panel.box.resolve(env)
        if any(abs(a-b)>0.01 for a,b in zip(actual.lo+actual.hi,expected.lo+expected.hi)):
            raise ValueError('Label source bounds contradict specification')
        volume=report['bodies'][panel.stable_id]['volume_mm3']
        if type(volume) not in (int,float) or not math.isfinite(volume) or volume<=0:
            raise ValueError('Missing finite measured volume')
    def size(prefix): return envelope([b for k,b in boxes.items() if k.startswith(prefix)]).size
    def dims(values): return ' x '.join(f'{v:.3f}'.rstrip('0').rstrip('.') for v in values)+' mm'
    return [
        'TEST ONLY / UNMEASURED - rectangular interior',
        'Clear L x W x H (spec): '+dims([env['Test_Length'],env['Test_Width'],env['Test_Height']]),
        'Origin: left rear floor; Y forward. Open left / rear / roof.',
        'MEASURED SNAPSHOT - not live-updating dimensions',
        'Bed W x L x H: '+dims(size('bed.001.')),
        'Cabinet W x occupied D x H: '+dims(size('cabinet.001.')),
        'Cabinet nominal D: '+dims([env['Cab_Depth']])+'; front projection included above',
        'Storage W x L x H: '+dims(size('storage.001.')),
        'ASSUMED arches (each W x L x H): '+dims(boxes[ARCHES[0]].size),
        'ASSUMED arch Y: '+dims([boxes[ARCHES[0]].lo[1]]),
        'Measured deck / arch: '+dims([fit['deck_to_arch_mm']]),
        'Measured cabinet right strip: '+dims([fit['nominal_right_strip_mm']]),
        'Measured box / deck: '+dims([gaps['top_to_deck_mm']]),
        'Measured box / arch left / right: '+dims([gaps['left_arch_gap_mm'],gaps['right_arch_gap_mm']]),
        'No vehicle-fit, load, access or manufacturing qualification.'
    ]
