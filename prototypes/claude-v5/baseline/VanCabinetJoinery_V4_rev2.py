"""Van Cabinet Generator V4 - PARAMETRIC DADO JOINERY (revision 2).

Autodesk Fusion (Python API).

Creates a NEW parametric cabinet made of individual components, with one or
more shelves that slide into matching open-front dado grooves cut into the
left and right side panels.

WHAT CHANGED FROM THE FIRST V4
  * Every derived joint dimension is now a visible Fusion USER PARAMETER
    (Cab_Shelf_Length, Cab_Shelf_X, Cab_Slot_Height, Cab_Shelf1_Z, ...).
    Shelf size/position and groove size/position both reference the SAME
    parameters, so they cannot drift apart. You can read each value in
    Modify > Change Parameters.
  * Re-running this script inside a design that already contains the cabinet
    does NOT rebuild anything. It MEASURES the existing model (bounding boxes,
    body volumes, interference) and reports PASS/FAIL. This is the validation
    tool for Tests A-D after you edit parameters.
  * The same measurement report is shown right after a fresh build.
  * Input sanity checks run before anything is created.

IMPORTANT
  * Run in a NEW, EMPTY design with design history ON (parametric mode).
  * This is 3D joinery geometry only - no CAM toolpaths or G-code.
  * Number of shelves/doors is fixed at generation time (see SHELF_COUNT).
    Changing the count means regenerating; Fusion's timeline cannot add or
    remove components from a parameter value.
  * Fusion Personal licences are non-commercial.

COORDINATES (local = world, all components sit at the origin)
  X = cabinet width (left outer face X=0)
  Y = front-to-back (door front Y=0, side panels start at Y=Cab_Ply)
  Z = height (cabinet base Z=0)
"""

import adsk.core
import adsk.fusion
import traceback

SHELF_COUNT = 1              # 0-4, fixed on generation
DOOR_COUNT = 2               # 1 or 2

# Base parameters - edit afterwards in Modify > Change Parameters.
SETTINGS = {
    'Cab_Width':          '1200 mm',
    'Cab_Height':         '850 mm',
    'Cab_Depth':          '550 mm',
    'Cab_Ply':            '18 mm',
    'Cab_Back':           '6 mm',
    'Cab_Gap':            '3 mm',
    'Cab_Dado_Depth':     '6 mm',     # Groove penetrates each side panel
    'Cab_Slot_Clearance': '0.5 mm',   # Groove is this much taller than shelf
    'Cab_End_Clearance':  '0.3 mm',   # Gap at EACH shelf end, bottom of groove
}

PARAM_COMMENT = 'Van Cabinet Joinery V4'
TOL_MM = 0.01                # Verification tolerance


# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------

def derived_settings():
    """Ordered (name, expression) pairs. Order matters: a parameter may only
    reference parameters created before it."""
    n = SHELF_COUNT
    items = [
        ('Cab_Inner_Depth',  'Cab_Depth - Cab_Back'),
        ('Cab_Slot_Height',  'Cab_Ply + Cab_Slot_Clearance'),
        ('Cab_Shelf_X',      'Cab_Ply - Cab_Dado_Depth + Cab_End_Clearance'),
        ('Cab_Shelf_Length',
         'Cab_Width - 2 * Cab_Ply + 2 * Cab_Dado_Depth - 2 * Cab_End_Clearance'),
        ('Cab_Compartment',
         '(Cab_Height - {} * Cab_Ply) / {}'.format(2 + n, n + 1)),
    ]
    for k in range(1, n + 1):
        items.append((
            'Cab_Shelf{}_Z'.format(k),
            'Cab_Ply + {} * Cab_Compartment + {} * Cab_Ply'.format(k, k - 1)
        ))
        items.append((
            'Cab_Slot{}_Z'.format(k),
            'Cab_Shelf{}_Z - Cab_Slot_Clearance / 2'.format(k)
        ))
    return items


def validate_inputs(design):
    """Check the base settings before creating anything."""
    um = design.unitsManager
    v = {k: um.evaluateExpression(e, 'mm') * 10.0   # cm -> mm
         for k, e in SETTINGS.items()}
    problems = []
    if not 0 < v['Cab_Dado_Depth'] < v['Cab_Ply']:
        problems.append('Cab_Dado_Depth must be > 0 and < Cab_Ply.')
    if not 0 <= v['Cab_End_Clearance'] < v['Cab_Dado_Depth']:
        problems.append('Cab_End_Clearance must be >= 0 and < Cab_Dado_Depth.')
    if v['Cab_Slot_Clearance'] < 0:
        problems.append('Cab_Slot_Clearance must be >= 0.')
    if v['Cab_Back'] <= 0 or v['Cab_Back'] >= v['Cab_Depth']:
        problems.append('Cab_Back must be > 0 and < Cab_Depth.')
    if v['Cab_Height'] <= (2 + SHELF_COUNT) * v['Cab_Ply']:
        problems.append('Cab_Height is too small for the panels and shelves.')
    if v['Cab_Width'] <= 2 * v['Cab_Ply']:
        problems.append('Cab_Width is too small for the side panels.')
    if problems:
        raise ValueError('Invalid settings:\n- ' + '\n- '.join(problems))


def make_parameters(design):
    params = design.userParameters
    all_items = list(SETTINGS.items()) + derived_settings()
    for name, expression in all_items:
        if params.itemByName(name):
            raise ValueError('Parameter already exists: ' + name)
    for name, expression in all_items:
        p = params.add(
            name,
            adsk.core.ValueInput.createByString(expression),
            'mm',
            PARAM_COMMENT
        )
        p.isFavorite = True


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def rectangle_profile(design, component, name, x, y, width, depth):
    """Create a dimension-driven rectangle on the local XY plane.

    Expressions x/y locate its bottom-left corner relative to the origin;
    expressions width/depth determine its size. All stay editable in Fusion.
    """
    um = design.unitsManager

    def get_cm(expr):
        return um.evaluateExpression(expr, 'mm')

    px, py = get_cm(x), get_cm(y)
    pw, pd = get_cm(width), get_cm(depth)

    if min(pw, pd) <= 0:
        raise ValueError('Invalid profile for {}: {} x {}'.format(
            name, width, depth))

    sketch = component.sketches.add(component.xYConstructionPlane)
    sketch.name = name + ' - parametric profile'
    lines = sketch.sketchCurves.sketchLines.addTwoPointRectangle(
        adsk.core.Point3D.create(px, py, 0),
        adsk.core.Point3D.create(px + pw, py + pd, 0)
    )

    cons = sketch.geometricConstraints
    for index in (0, 2):
        cons.addHorizontal(lines.item(index))
    for index in (1, 3):
        cons.addVertical(lines.item(index))

    bottom = lines.item(0)
    right = lines.item(1)
    corner = bottom.startSketchPoint
    origin = sketch.originPoint
    dims = sketch.sketchDimensions
    H = adsk.fusion.DimensionOrientations.HorizontalDimensionOrientation
    V = adsk.fusion.DimensionOrientations.VerticalDimensionOrientation

    if abs(px) < 1e-7 and abs(py) < 1e-7:
        cons.addCoincident(corner, origin)
    else:
        if abs(px) < 1e-7:
            cons.addVerticalPoints(origin, corner)
        else:
            dim = dims.addDistanceDimension(
                origin, corner, H,
                adsk.core.Point3D.create(px / 2, py - 2, 0)
            )
            dim.parameter.expression = x
        if abs(py) < 1e-7:
            cons.addHorizontalPoints(origin, corner)
        else:
            dim = dims.addDistanceDimension(
                origin, corner, V,
                adsk.core.Point3D.create(px - 2, py / 2, 0)
            )
            dim.parameter.expression = y

    wd = dims.addDistanceDimension(
        bottom.startSketchPoint, bottom.endSketchPoint, H,
        adsk.core.Point3D.create(px + pw / 2, py - 2, 0)
    )
    wd.parameter.expression = width

    dd = dims.addDistanceDimension(
        right.startSketchPoint, right.endSketchPoint, V,
        adsk.core.Point3D.create(px + pw + 2, py + pd / 2, 0)
    )
    dd.parameter.expression = depth

    return sketch


def extrude_sketch(component, sketch, name, z, height, operation,
                   participants=None):
    """Extrude from an expression-defined Z offset and distance.

    participants: for CUT operations, the bodies the cut may affect. This is
    essential: without it a cut also removes material from bodies in OTHER
    components (it trimmed the shelf ends flush with the side panels).
    """
    features = component.features.extrudeFeatures
    inp = features.createInput(sketch.profiles.item(0), operation)
    if participants:
        inp.participantBodies = participants
    inp.setOneSideExtent(
        adsk.fusion.DistanceExtentDefinition.create(
            adsk.core.ValueInput.createByString(height)
        ),
        adsk.fusion.ExtentDirections.PositiveExtentDirection
    )
    # The default start plane is already Z=0; only add an offset
    # when the design calls for one.
    if z.strip() != '0 mm':
        inp.startExtent = adsk.fusion.OffsetStartDefinition.create(
            adsk.core.ValueInput.createByString(z)
        )
    feature = features.add(inp)
    feature.name = name
    sketch.isVisible = False
    return feature


def make_panel(design, root, name, x, y, z, w, d, h):
    occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    part = occ.component
    part.name = name
    sketch = rectangle_profile(design, part, name, x, y, w, d)
    extrude = extrude_sketch(
        part, sketch, name + ' - solid', z, h,
        adsk.fusion.FeatureOperations.NewBodyFeatureOperation
    )
    extrude.bodies.item(0).name = name
    return part


def cut_dado(design, side_component, name, x, y, z, width, depth,
             slot_height):
    """Remove material from one side panel using a parametric cut feature."""
    sketch = rectangle_profile(
        design, side_component, name, x, y, width, depth
    )
    # Only the side panel's own body may be cut - never the shelf.
    return extrude_sketch(
        side_component, sketch, name, z, slot_height,
        adsk.fusion.FeatureOperations.CutFeatureOperation,
        participants=[side_component.bRepBodies.item(0)]
    )


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build(design):
    validate_inputs(design)
    make_parameters(design)
    root = design.rootComponent

    W, H, D = 'Cab_Width', 'Cab_Height', 'Cab_Depth'
    T, B, G = 'Cab_Ply', 'Cab_Back', 'Cab_Gap'
    GD = 'Cab_Dado_Depth'
    Z0 = '0 mm'

    # Main body starts behind the front doors (door thickness = plywood).
    FRONT = T
    INNER_W = f'({W} - 2 * {T})'
    INNER_D = 'Cab_Inner_Depth'

    left = make_panel(design, root, '01 Left Side', Z0, FRONT, Z0, T, D, H)
    right = make_panel(design, root, '02 Right Side',
                       f'({W} - {T})', FRONT, Z0, T, D, H)
    make_panel(design, root, '03 Bottom', T, FRONT, Z0,
               INNER_W, INNER_D, T)
    make_panel(design, root, '04 Top', T, FRONT,
               f'({H} - {T})', INNER_W, INNER_D, T)
    make_panel(design, root, '05 Back', T,
               f'({FRONT} + {D} - {B})', T,
               INNER_W, B, f'({H} - 2 * {T})')

    for k in range(1, SHELF_COUNT + 1):
        shelf_z = 'Cab_Shelf{}_Z'.format(k)
        slot_z = 'Cab_Slot{}_Z'.format(k)

        # The shelf and both grooves are driven by the SAME derived
        # parameters, so size and position cannot disagree.
        make_panel(design, root, '06 Shelf {}'.format(k),
                   'Cab_Shelf_X', FRONT, shelf_z,
                   'Cab_Shelf_Length', INNER_D, T)

        # Left groove: from (inside face - depth) to the inside face.
        cut_dado(design, left, 'Dado {} - LEFT'.format(k),
                 f'({T} - {GD})', FRONT, slot_z,
                 GD, INNER_D, 'Cab_Slot_Height')
        # Right groove: from the inside face outward by the groove depth.
        cut_dado(design, right, 'Dado {} - RIGHT'.format(k),
                 f'({W} - {T})', FRONT, slot_z,
                 GD, INNER_D, 'Cab_Slot_Height')

    door_width = f'(({W} - ({DOOR_COUNT} + 1) * {G}) / {DOOR_COUNT})'
    door_height = f'({H} - 2 * {G})'
    for i in range(DOOR_COUNT):
        door_x = f'(({i + 1}) * {G} + {i} * {door_width})'
        make_panel(design, root, f'07 Door {i + 1}',
                   door_x, Z0, G, door_width, T, door_height)


# ---------------------------------------------------------------------------
# Verification (measures the live model; safe to run after any parameter edit)
# ---------------------------------------------------------------------------

def occurrences_named(root, prefix):
    found = []
    for i in range(root.occurrences.count):
        occ = root.occurrences.item(i)
        if occ.component.name.startswith(prefix):
            found.append(occ)
    return found


def verify(design):
    """Return (report_text, failure_count)."""
    root = design.rootComponent
    up = design.userParameters

    def val(name):
        p = up.itemByName(name)
        if not p:
            raise ValueError('Missing user parameter: ' + name)
        return p.value                      # internal cm

    def body_of(occ):
        if occ.bRepBodies.count != 1:
            raise ValueError('{} should hold exactly 1 body, has {}'.format(
                occ.component.name, occ.bRepBodies.count))
        return occ.bRepBodies.item(0)       # assembly-context proxy

    left_occ = occurrences_named(root, '01 Left')
    right_occ = occurrences_named(root, '02 Right')
    back_occ = occurrences_named(root, '05 Back')
    shelf_occs = sorted(occurrences_named(root, '06 Shelf'),
                        key=lambda o: o.component.name)
    if not (left_occ and right_occ and back_occ):
        raise ValueError('Cabinet components not found in this design.')

    left, right, back = (body_of(left_occ[0]), body_of(right_occ[0]),
                         body_of(back_occ[0]))
    lb, rb, bb = left.boundingBox, right.boundingBox, back.boundingBox

    T, GD = val('Cab_Ply'), val('Cab_Dado_Depth')
    EC, SC = val('Cab_End_Clearance'), val('Cab_Slot_Clearance')
    W, H, D = val('Cab_Width'), val('Cab_Height'), val('Cab_Depth')
    INNER_D = val('Cab_Inner_Depth')

    lines = []
    state = {'fail': 0}

    def check(label, actual_cm, expected_cm):
        a, e = actual_cm * 10.0, expected_cm * 10.0
        ok = abs(a - e) <= TOL_MM
        if not ok:
            state['fail'] += 1
        lines.append('  {} {}: {:.3f} mm (expected {:.3f})'.format(
            'PASS' if ok else 'FAIL', label, a, e))

    lines.append('Cab_Width={:.2f}  Cab_Ply={:.2f}  Cab_Dado_Depth={:.2f}  '
                 'Cab_End_Clearance={:.2f}  (mm)'.format(
                     W * 10, T * 10, GD * 10, EC * 10))
    lines.append('Shelves found: {}'.format(len(shelf_occs)))

    for idx, occ in enumerate(shelf_occs, start=1):
        shelf = body_of(occ)
        sb = shelf.boundingBox
        lines.append('')
        lines.append('Shelf {}'.format(idx))
        check('length', sb.maxPoint.x - sb.minPoint.x, val('Cab_Shelf_Length'))
        check('insertion into LEFT groove',
              lb.maxPoint.x - sb.minPoint.x, GD - EC)
        check('insertion into RIGHT groove',
              sb.maxPoint.x - rb.minPoint.x, GD - EC)
        check('shelf left end X', sb.minPoint.x, T - GD + EC)
        check('shelf right end X', sb.maxPoint.x, W - T + GD - EC)
        slot_z = val('Cab_Slot{}_Z'.format(idx))
        check('gap below shelf in groove', sb.minPoint.z - slot_z, SC / 2)
        check('gap above shelf in groove',
              (slot_z + T + SC) - sb.maxPoint.z, SC / 2)
        check('shelf thickness', sb.maxPoint.z - sb.minPoint.z, T)
        check('shelf front aligned to side-panel front',
              sb.minPoint.y, lb.minPoint.y)
        check('shelf rear meets back panel', sb.maxPoint.y, bb.minPoint.y)
        check('shelf depth', sb.maxPoint.y - sb.minPoint.y, INNER_D)

    # Genuine-cut check: panel volume must equal blank minus all grooves.
    n = len(shelf_occs)
    groove_vol = n * GD * INNER_D * (T + SC)
    expected_vol = T * D * H - groove_vol
    lines.append('')
    lines.append('Side-panel volumes (proves grooves are real 3D cuts)')
    for label, body in (('left', left), ('right', right)):
        a, e = body.volume, expected_vol
        ok = abs(a - e) <= max(1e-6, 1e-6 * e)
        if not ok:
            state['fail'] += 1
        lines.append('  {} {}: {:.3f} cm3 (expected {:.3f})'.format(
            'PASS' if ok else 'FAIL', label, a, e))

    # Interference between the shelves and the side panels.
    lines.append('')
    if n:
        try:
            coll = adsk.core.ObjectCollection.create()
            coll.add(left)
            coll.add(right)
            for occ in shelf_occs:
                coll.add(body_of(occ))
            result = design.analyzeInterference(
                design.createInterferenceInput(coll))
            ok = result.count == 0
            if not ok:
                state['fail'] += 1
            lines.append('Interference (sides vs shelves): {} ({} found)'.format(
                'PASS' if ok else 'FAIL', result.count))
        except Exception:
            lines.append('Interference check could not run:\n' +
                         traceback.format_exc())
    else:
        lines.append('No shelves - interference check skipped.')

    lines.append('')
    lines.append('RESULT: {}'.format(
        'ALL CHECKS PASSED' if state['fail'] == 0
        else '{} CHECK(S) FAILED'.format(state['fail'])))
    return '\n'.join(lines), state['fail']


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run(context):
    app = adsk.core.Application.get()
    ui = app.userInterface
    try:
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            ui.messageBox('Open a Fusion design first.')
            return
        if design.designType != adsk.fusion.DesignTypes.ParametricDesignType:
            ui.messageBox('Enable design history (parametric mode) first.')
            return

        root = design.rootComponent
        if root.occurrences.count > 0:
            if occurrences_named(root, '01 Left'):
                report, _ = verify(design)
                app.log(report)
                ui.messageBox('EXISTING CABINET - MEASUREMENT REPORT\n\n' + report)
            else:
                ui.messageBox('This design already has other components. '
                              'Use a NEW, EMPTY design for V4.')
            return

        if SHELF_COUNT not in range(5) or DOOR_COUNT not in (1, 2):
            ui.messageBox('Choose 0-4 shelves and 1 or 2 doors in the script.')
            return

        build(design)
        report, _ = verify(design)
        app.log(report)
        ui.messageBox(
            'V4 cabinet created.\n\n' + report +
            '\n\nNow try Modify > Change Parameters (e.g. Cab_Dado_Depth = '
            '10 mm, Cab_Width = 1000 mm), then run this script again in the '
            'same design to re-measure.'
        )
    except Exception:
        error = traceback.format_exc()
        app.log(error)
        ui.messageBox('V4 script error:\n\n' + error)
