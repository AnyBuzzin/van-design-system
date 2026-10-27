"""Profile sketches: accepted fixed XY path and offline oriented-width helpers.

Uses existing Fusion extrusion/ownership machinery. No document lifecycle API.
The bounded native-width path is an offline candidate; its CAD behaviour is
UNKNOWN until separately authorised live qualification.
"""
import math
from dataclasses import replace
from types import SimpleNamespace

import adsk.core
import adsk.fusion

from .adapter import FusionAdapter, FusionGeometrySource, ATTR_GROUP, ATTR_ID, ATTR_GEN, GENERATOR_ID, _find_occurrences
from .runner import _design_counts
from .test_envelope import affected_body_check
from ...core.expr import Mm
from ...modules.profile_fixture import (PARAMETERS, PARAMETER, THICKNESS, feature_loop, feature_depth,
                                       feature_start, feature_id, inventory, validate_panels)
from ...verification.profile_panel import measure_profiles, probes, world_probes
from ...manufacturing.profile import Line, PanelFrame


class ProfileAdapter(FusionAdapter):
    def compile_oriented(self, plan, guard, records):
        from ...manufacturing.placement import arrangement_profiles
        from ...arrangement_job import preview_values
        asm = plan.arrangement.assembly
        bindings = plan.profile_bindings
        if not bindings:
            raise ValueError('Reviewed native profile bindings required')
        preview = preview_values(plan.arrangement, plan.envelope, {}, bindings)
        if preview['outcome'] != 'PASS':
            raise ValueError(preview['reason'])
        profiles, _ = arrangement_profiles(plan.arrangement, tool_diameter=plan.tool_diameter_mm)
        env = asm.parameters.resolve()
        parameter = next(iter(bindings.values())).parameter
        ends = tuple(asm.parameters.resolve({parameter: w}) for w in next(iter(bindings.values())).interval)
        for at in ends:
            preview = preview_values(plan.arrangement, plan.envelope, {parameter:at[parameter]}, bindings)
            if preview['outcome'] != 'PASS':
                raise ValueError('Native interval preflight refused: ' + preview['reason'])
        prepared = {}
        for p in profiles:
            b = bindings[p.panel_id]
            offset = tuple(sum((e*k for e, k in zip(b.frame_origin, axis)), Mm(0)) for axis in b.frame_axes)
            for loop in [b.outline] + [f.loop for f in b.features]:
                self._bound_loop_data(loop, offset[:2], env, ends)
            world_probes(p)  # Unsupported material-side sampling refuses before writes.
            prepared[p.panel_id] = (p, b, offset)
        guard()
        if (self.root.occurrences.count or self.root.bRepBodies.count or self.root.sketches.count
                or self.design.userParameters.count or self.design.timeline.count):
            raise RuntimeError('Empty design required')
        self._native = (prepared, env, ends, guard)
        try:
            # All furniture is the one bound cabinet; reference boxes retain the
            # existing compiler. Profile features replace the old box dado list.
            super().compile(replace(asm, operations=()))
            occurrences = _find_occurrences(self.root)
            ids = {p.stable_id for p in asm.panels}
            if set(occurrences) != ids or any(len(v) != 1 for v in occurrences.values()):
                raise RuntimeError('Ambiguous native cut owners')
            components = {pid: occ[0].component for pid, occ in occurrences.items()}
            if any(c.bRepBodies.count != 1 for c in components.values()):
                raise RuntimeError('Ambiguous native target body')
            def volumes():
                return {pid: c.bRepBodies.item(0).volume*1000 for pid, c in components.items()}
            for p, b, offset in prepared.values():
                comp = components[p.panel_id]
                for f in b.features:
                    guard()
                    before = volumes()
                    depth = b.thickness if f.kind == 'through' else f.depth
                    start = offset[2] + (b.thickness-depth if f.face == 'top' else Mm(0))
                    sketch = self._bound_loop_sketch(comp, f.feature_id, f.loop, offset[:2], env, ends, guard)
                    cut = self._extrude(comp, sketch, f.feature_id, start.render(), depth.render(),
                                        adsk.fusion.FeatureOperations.CutFeatureOperation,
                                        participants=[comp.bRepBodies.item(0)])
                    cut.attributes.add(ATTR_GROUP, ATTR_ID, f.feature_id)
                    after = volumes()
                    expected = f.loop.resolve(env).area * depth.eval(env)
                    ownership = affected_body_check(cut, SimpleNamespace(operation_id=f.feature_id,
                                                                         target_panel_id=p.panel_id))
                    ok = (all(math.isfinite(v) and v > 0 for v in (*before.values(), *after.values()))
                          and abs(before[p.panel_id]-after[p.panel_id]-expected) <= max(1, expected*1e-6)
                          and all(abs(before[pid]-after[pid]) <= 1e-6 for pid in ids if pid != p.panel_id)
                          and ownership['status'] == 'PASS')
                    records.append(dict(cut_id=f.feature_id, owner=p.panel_id, before_mm3=before, after_mm3=after,
                                        expected_removed_mm3=expected, ownership=ownership,
                                        outcome='PASS' if ok else 'FAIL'))
                    if not ok:
                        raise RuntimeError('Native cut changed unexpected material; no rollback')
            guard()
        finally:
            self._native = None

    def _make_panel(self, panel):
        native = getattr(self, '_native', None)
        if not native:
            return super()._make_panel(panel)
        prepared, env, ends, guard = native
        guard()
        if panel.stable_id not in prepared:
            return super()._make_panel(panel)
        profile, binding, offset = prepared[panel.stable_id]
        comp = self._oriented_component(profile, guard)
        sketch = self._bound_loop_sketch(comp, profile.panel_id, binding.outline, offset[:2], env, ends, guard)
        feature = self._extrude(comp, sketch, profile.panel_id+' - solid', offset[2].render(),
                                binding.thickness.render(), adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        if feature.bodies.count != 1:
            raise RuntimeError('Native profile did not create one body')
        feature.bodies.item(0).name = profile.display_name
        return comp

    def _oriented_component(self, profile, guard):
        """Rotate component axes only; origin offsets stay in sketch/extrude space.

        This leaves room for native Expr-driven placement without changing an
        occurrence transform after creation. Existing fixed-XY builds bypass it.
        """
        frame = profile.frame
        if type(frame) is not PanelFrame:
            raise ValueError('Oriented profile requires a validated PanelFrame')
        matrix = adsk.core.Matrix3D.create()
        axes = [adsk.core.Vector3D.create(*axis) for axis in (frame.u, frame.v, frame.w)]
        if matrix.setWithCoordinateSystem(adsk.core.Point3D.create(0, 0, 0), *axes) is not True:
            raise RuntimeError('Cannot establish profile coordinate system')
        guard()
        occurrence = self.root.occurrences.addNewComponent(matrix)
        if occurrence is None:
            raise RuntimeError('Oriented component creation failed')
        comp = occurrence.component
        comp.name = profile.display_name
        comp.attributes.add(ATTR_GROUP, ATTR_ID, profile.panel_id)
        comp.attributes.add(ATTR_GROUP, ATTR_GEN, GENERATOR_ID)
        return comp

    @staticmethod
    def _frame_offset(frame):
        """World origin projected into the rotated component's local axes (mm)."""
        if type(frame) is not PanelFrame:
            raise ValueError('Validated PanelFrame required')
        return tuple(sum(a*b for a, b in zip(frame.origin, axis))
                     for axis in (frame.u, frame.v, frame.w))

    def _bound_loop_sketch(self, comp, name, binding, offset, env, interval_envs, guard):
        """Native dimensions from reviewed affine bindings; never freeze moving geometry.

        Bounded #95 loops have a line between each pair of arcs. Arc endpoints
        are shared with their neighbouring lines, avoiding duplicate endpoint
        constraints. A constant construction datum below every coordinate makes
        driving distances positive even for negative local/world placement.
        No lifecycle operations or recovery are performed here.
        """
        loops, sources, at, datum = self._bound_loop_data(binding, offset, env, interval_envs)
        guard()
        sketch = comp.sketches.add(comp.xYConstructionPlane)
        sketch.name = name + ' - native profile'
        def point(x, y):
            return adsk.core.Point3D.create(x / 10, y / 10, 0)
        anchor = sketch.sketchPoints.add(point(datum, datum))
        if anchor is None:
            raise RuntimeError('Construction datum creation failed')
        anchor.isFixed = True  # Constant reference only; never a profile point.
        if anchor.isFullyConstrained is not True:
            raise RuntimeError('Construction datum is not constrained')
        dims, constraints = sketch.sketchDimensions, sketch.geometricConstraints
        orientations = (adsk.fusion.DimensionOrientations.HorizontalDimensionOrientation,
                        adsk.fusion.DimensionOrientations.VerticalDimensionOrientation)
        def coordinate(p, xy, context):
            for axis, e, orientation in zip(('X', 'Y'), xy, orientations):
                try:
                    d = dims.addDistanceDimension(anchor, p, orientation, point(datum - 10, datum - 10))
                    if d is None:
                        raise RuntimeError('Native coordinate dimension failed')
                    d.parameter.expression = (e - Mm(datum)).render()
                except Exception as exc:
                    raise RuntimeError(f'{name}: {context} {axis} coordinate: {exc}') from exc

        # Each loop junction has exactly one SketchPoint. Arcs own their two
        # endpoint junctions; lines reuse those API objects directly.
        junctions = {}
        for i, (s, segment) in enumerate(zip(sources, loops[0].segments)):
            if s[0] != 'arc':
                continue
            guard()
            center = at(s[1]); cx, cy = (e.eval(env) for e in center)
            ox, oy = (e.eval(env) for e in offset)
            # Bind an explicit point before it belongs to a curve. The API
            # accepts SketchPoint centres; do not dimension an implicit centre
            # after arc creation or silently skip a rejected driving constraint.
            center_point = sketch.sketchPoints.add(point(cx, cy))
            if center_point is None:
                raise RuntimeError(f'{name}: arc {i} centre creation failed')
            coordinate(center_point, center, f'arc {i} centre')
            arc = sketch.sketchCurves.sketchArcs.addByCenterStartSweep(
                center_point, point(segment.start[0] + ox, segment.start[1] + oy), segment.sweep)
            if arc is None:
                raise RuntimeError('Native arc creation failed')
            def check_center(p, driven=False):
                g = p.geometry
                xyz = (g.x * 10, g.y * 10, g.z * 10)
                if (p.isValid is not True or p.isFixed is not False
                        or (driven and p.isFullyConstrained is not True)
                        or not all(math.isfinite(v) for v in xyz)
                        or math.dist(xyz, (cx, cy, 0)) > 1e-6):
                    raise RuntimeError('Native arc centre state/readback differs')
            try:
                check_center(center_point, driven=True)
                actual_center = arc.centerSketchPoint
                check_center(actual_center)
                if actual_center != center_point:
                    # SketchPoint.merge redirects the input's curve references
                    # into this already Expr-driven point; never fix or redrive.
                    if center_point.merge(actual_center) is not True:
                        raise RuntimeError('Native arc centre merge failed')
                if arc.centerSketchPoint != center_point:
                    raise RuntimeError('Native arc centre identity differs after merge')
                check_center(arc.centerSketchPoint, driven=True)
            except Exception as exc:
                raise RuntimeError(f'{name}: arc {i} centre binding: {exc}') from exc
            # Fusion normalises negative sweeps to CCW, reversing API endpoints:
            # fusion_SketchArcs_addByCenterStartSweep.htm in Autodesk's API docs.
            start, end = arc.startSketchPoint, arc.endSketchPoint
            if segment.sweep < 0:
                start, end = end, start
            for p, expected in ((start, segment.start), (end, segment.end)):
                g = p.geometry
                actual = (g.x * 10, g.y * 10, g.z * 10)
                target = (expected[0] + ox, expected[1] + oy, 0)
                if not all(math.isfinite(v) for v in actual) or math.dist(actual, target) > 1e-6:
                    raise RuntimeError('Native arc endpoint/sweep readback differs')
            radial = dims.addRadialDimension(arc, point(cx + segment.radius, cy + segment.radius))
            if radial is None:
                raise RuntimeError('Native radius dimension failed')
            radial.parameter.expression = Mm(segment.radius).render()
            for endpoint, angle in ((start, segment.start_angle),
                                    (end, segment.start_angle + segment.sweep)):
                ray = sketch.sketchCurves.sketchLines.addByTwoPoints(arc.centerSketchPoint, endpoint)
                reference = sketch.sketchCurves.sketchLines.addByTwoPoints(
                    point(datum, datum), point(datum + 10 * math.cos(angle), datum + 10 * math.sin(angle)))
                if ray is None or reference is None:
                    raise RuntimeError('Native arc direction construction failed')
                ray.isConstruction = reference.isConstruction = True
                reference.isFixed = True  # Constant direction, independent of width.
                for p in (reference.startSketchPoint, reference.endSketchPoint):
                    if p.isFullyConstrained is False:
                        p.isFixed = True
                    if p.isFullyConstrained is not True:
                        raise RuntimeError('Arc direction reference is not constrained')
                if constraints.addParallel(ray, reference) is None:
                    raise RuntimeError('Native arc direction constraint failed')
            junctions[i] = start
            junctions[(i + 1) % len(sources)] = end
        for i, s in enumerate(sources):
            if s[0] != 'line':
                continue
            guard()
            points = []
            for j, src in ((i, s[1]), ((i + 1) % len(sources), s[2])):
                if j not in junctions:
                    xy = at(src)
                    p = sketch.sketchPoints.add(point(*(e.eval(env) for e in xy)))
                    if p is None:
                        raise RuntimeError('Native endpoint creation failed')
                    coordinate(p, xy, f'junction {j}')
                    junctions[j] = p
                points.append(junctions[j])
            if sketch.sketchCurves.sketchLines.addByTwoPoints(*points) is None:
                raise RuntimeError('Native line creation failed')
        if sketch.profiles.count != 1 or sketch.isFullyConstrained is not True:
            raise RuntimeError('Native loop must be one fully constrained profile')
        guard()
        return sketch

    @staticmethod
    def _bound_loop_data(binding, offset, env, interval_envs):
        """Pure preparation, also run for every loop before the first CAD write."""
        if len(interval_envs) != 2:
            raise ValueError('Both reviewed interval endpoints are required')
        loops = [binding.resolve(e) for e in (env, *interval_envs)]
        sources = binding.sources
        if not sources or any(s[0] not in ('line', 'arc') for s in sources):
            raise ValueError('Unsupported native loop binding')
        if any(a[0] == b[0] == 'arc' for a, b in zip(sources, sources[1:] + sources[:1])):
            raise ValueError('Adjacent bound arcs are not supported')

        def at(source):
            i, delta = source
            return tuple(binding.vertices[i][j] + Mm(delta[j]) + offset[j] for j in range(2))

        coords = [at(s[1]) for s in sources]
        coords += [at(s[2]) for s in sources if s[0] == 'line']
        values = [e.eval(v) for xy in coords for e in xy for v in (env, *interval_envs)]
        if not values or not all(math.isfinite(v) for v in values):
            raise ValueError('Incomplete native coordinate observations')
        datum = min(values) - 100.0
        if not math.isfinite(datum) or any(v - datum <= 0 for v in values):
            raise ValueError('No positive native dimension datum')
        # Source topology must remain closed throughout the reviewed interval.
        for loop in loops:
            if len(loop.segments) != len(sources) or any(
                    math.dist(a.end, b.start) > 1e-7
                    for a, b in zip(loop.segments, loop.segments[1:] + loop.segments[:1])):
                raise ValueError('Bound loop is not closed')
        return loops, sources, at, datum

    def _loop_sketch(self, comp, name, loop, origin):
        sketch=comp.sketches.add(comp.xYConstructionPlane);sketch.name=name+' - profile'
        def point(xy):return adsk.core.Point3D.create((xy[0]+origin[0])/10,(xy[1]+origin[1])/10,0)
        for seg in loop.segments:
            if isinstance(seg,Line):
                curve=sketch.sketchCurves.sketchLines.addByTwoPoints(point(seg.start),point(seg.end))
            else:
                curve=sketch.sketchCurves.sketchArcs.addByCenterStartSweep(point(seg.center),point(seg.start),seg.sweep)
            if curve is None:raise RuntimeError('Profile curve creation failed')
            # Resolved XY geometry is explicitly fixed, never advertised as shape-parametric.
            curve.isFixed=True
        if sketch.profiles.count!=1:raise RuntimeError('Profile must produce one closed region')
        # Fixed curves do not establish that every sketch point is constrained.
        # Only these fresh fixed-XY loops use this path; thickness stays an Expr.
        for i in range(sketch.sketchPoints.count):
            point=sketch.sketchPoints.item(i)
            constrained=point.isFullyConstrained
            if type(constrained) is not bool:raise RuntimeError('Point constraint state unavailable')
            if not constrained:
                point.isFixed=True
                if point.isFullyConstrained is not True:
                    raise RuntimeError('Profile point remains unconstrained')
        if sketch.isFullyConstrained is not True:
            raise RuntimeError('Profile sketch remains unconstrained')
        return sketch

    def compile_profiles(self, panels, guard, records):
        validate_panels(panels)
        for p in panels:
            probes(p)  # Refuse unsupported/narrow probe geometry before any CAD write.
            if p.profile.thickness!=18:raise ValueError('Initial fixture thickness must be 18 mm')
        guard()
        if (self.root.occurrences.count or self.root.bRepBodies.count or self.root.sketches.count
                or self.design.userParameters.count or self.design.timeline.count):
            raise RuntimeError('Empty design required')
        for p in PARAMETERS.params:
            self.design.userParameters.add(p.name,adsk.core.ValueInput.createByString(Mm(p.value_mm).render()),'mm',p.comment)
        components={}
        for item in panels:
            guard();p=item.profile;comp=self.root.occurrences.addNewComponent(adsk.core.Matrix3D.create()).component
            comp.name=p.display_name;comp.attributes.add(ATTR_GROUP,ATTR_ID,p.panel_id)
            comp.attributes.add(ATTR_GROUP,ATTR_GEN,GENERATOR_ID)
            sketch=self._loop_sketch(comp,p.panel_id,p.outline,item.origin)
            feature=self._extrude(comp,sketch,p.panel_id+' - solid',Mm(item.origin[2]).render(),THICKNESS.render(),
                                  adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
            feature.bodies.item(0).name=p.display_name;components[p.panel_id]=comp
        # All owners resolve before the first cut, including future feature targets.
        if any(c.bRepBodies.count!=1 for c in components.values()):raise RuntimeError('Ambiguous profile owner')
        for item in panels:
            p=item.profile;comp=components[p.panel_id]
            for index,f in enumerate(p.features):
                guard();cid=feature_id(p,index)
                before={pid:c.bRepBodies.item(0).volume*1000 for pid,c in components.items()}
                sketch=self._loop_sketch(comp,cid,feature_loop(f),item.origin)
                start=Mm(item.origin[2])+feature_start(f)
                cut=self._extrude(comp,sketch,cid,start.render(),feature_depth(f).render(),
                                  adsk.fusion.FeatureOperations.CutFeatureOperation,participants=[comp.bRepBodies.item(0)])
                cut.attributes.add(ATTR_GROUP,ATTR_ID,cid)
                after={pid:c.bRepBodies.item(0).volume*1000 for pid,c in components.items()}
                expected=feature_loop(f).area*feature_depth(f).eval({PARAMETER:p.thickness})
                ok=(all(math.isfinite(v) for v in (*before.values(),*after.values()))
                    and abs(before[p.panel_id]-after[p.panel_id]-expected)<=max(1,expected*1e-6)
                    and all(abs(before[pid]-after[pid])<=1e-6 for pid in components if pid!=p.panel_id))
                ownership=affected_body_check(cut,SimpleNamespace(operation_id=cid,target_panel_id=p.panel_id))
                ok=ok and ownership['status']=='PASS'
                records.append(dict(cut_id=cid,owner=p.panel_id,before_mm3=before,after_mm3=after,
                                    expected_removed_mm3=expected,ownership=ownership,outcome='PASS' if ok else 'FAIL'))
                if not ok:raise RuntimeError('Profile cut changed unexpected material; stop without rollback')
        guard()


def measure_profile_design(design,panels,guard,thickness):
    guard();source=FusionGeometrySource(design)
    report=measure_profiles(source,{PARAMETER:thickness});checks=report['checks'];counts=_design_counts(design)
    def check(cid,ok,**data):checks.append(dict(check_id=cid,status='PASS' if ok else 'FAIL',**data))
    root=design.rootComponent
    check('profiles.inventory',counts==inventory(panels) and root.bRepBodies.count==0 and root.sketches.count==0
          and design.timeline.markerPosition==design.timeline.count,observed=counts)
    occ=_find_occurrences(root)
    if set(occ)!={p.profile.panel_id for p in panels} or any(len(v)!=1 for v in occ.values()):
        raise RuntimeError('Ambiguous profile occurrence')
    healthy=adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState
    for item in panels:
        p=item.profile;comp=occ[p.panel_id][0].component;n=1+len(p.features)
        observed=dict(expected_count=n,body_count=comp.bRepBodies.count,
                      body_valid=comp.bRepBodies.item(0).isValid if comp.bRepBodies.count else None,
                      body_solid=comp.bRepBodies.item(0).isSolid if comp.bRepBodies.count else None,
                      feature_count=comp.features.count,extrusion_count=comp.features.extrudeFeatures.count,
                      sketch_count=comp.sketches.count,extrusions=[],sketches=[])
        ok=(comp.bRepBodies.count==1 and comp.bRepBodies.item(0).isValid and comp.bRepBodies.item(0).isSolid
            and comp.features.count==n and comp.features.extrudeFeatures.count==n and comp.sketches.count==n)
        cuts={}
        for i in range(comp.features.extrudeFeatures.count):
            f=comp.features.extrudeFeatures.item(i)
            observed['extrusions'].append(dict(index=i,health_state=int(f.healthState),
                healthy=f.healthState==healthy,suppressed=f.isSuppressed,operation=int(f.operation)))
            ok=ok and f.healthState==healthy and not f.isSuppressed
            if f.operation==adsk.fusion.FeatureOperations.CutFeatureOperation:
                attr=f.attributes.itemByName(ATTR_GROUP,ATTR_ID);cid=attr.value if attr else None
                if cid in cuts:raise RuntimeError('Duplicate profile cut identity')
                cuts[cid]=f
            elif f.operation!=adsk.fusion.FeatureOperations.NewBodyFeatureOperation:ok=False
        for i in range(comp.sketches.count):
            s=comp.sketches.item(i)
            observed['sketches'].append(dict(index=i,profile_count=s.profiles.count,health_state=int(s.healthState),
                healthy=s.healthState==healthy,fully_constrained=s.isFullyConstrained))
            ok=ok and s.profiles.count==1 and s.healthState==healthy and s.isFullyConstrained
        check(p.panel_id+'.features',ok,observed=observed)
        expected={feature_id(p,i) for i in range(len(p.features))}
        if set(cuts)!=expected:raise RuntimeError('Unexpected profile cut identities')
        for cid in sorted(cuts):
            checks.append(affected_body_check(cuts[cid],SimpleNamespace(operation_id=cid,target_panel_id=p.panel_id)))
    guard();report.update(counts=counts,outcome='PASS' if all(c['status']=='PASS' for c in checks) else 'FAIL')
    return report


def measure_oriented_design(design, plan, guard):
    from ...verification.profile_panel import measure_oriented, oriented_targets
    from ...arrangement_job import expected_inventory
    guard()
    report = measure_oriented(FusionGeometrySource(design), plan)
    if report['outcome'] != 'PASS':
        return report
    asm = plan.arrangement.assembly
    values = {p.name: report['parameters_mm'][p.name] for p in asm.parameters.base()}
    _, profiles, targets = oriented_targets(plan, values)
    by_id = {p.panel_id:p for p in profiles}
    occurrences = _find_occurrences(design.rootComponent)
    checks = report['checks']
    def check(cid, ok, **data):
        checks.append(dict(check_id=cid, status='PASS' if ok else 'FAIL', **data))
    if set(occurrences) != set(targets) or any(len(v) != 1 for v in occurrences.values()):
        raise RuntimeError('Ambiguous measured profile occurrences')
    counts = _design_counts(design)
    check('inventory', counts == expected_inventory(asm, profiles)
          and design.rootComponent.bRepBodies.count == 0 and design.rootComponent.sketches.count == 0
          and design.timeline.markerPosition == design.timeline.count, observed=counts)
    report.update(counts=counts, frames={})
    healthy = adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState
    for pid, items in occurrences.items():
        guard()
        occ, profile = items[0], by_id.get(pid)
        comp = occ.component
        expected_cuts = {feature_id(profile,i) for i in range(len(profile.features))} if profile else set()
        n = 1+len(expected_cuts)
        ok = (comp.bRepBodies.count == 1 and comp.bRepBodies.item(0).isValid and comp.bRepBodies.item(0).isSolid
              and comp.features.count == n and comp.features.extrudeFeatures.count == n and comp.sketches.count == n)
        found, features, sketches = {}, [], []
        for i in range(comp.features.extrudeFeatures.count):
            f = comp.features.extrudeFeatures.item(i)
            features.append(dict(healthy=f.healthState == healthy, suppressed=f.isSuppressed, operation=int(f.operation)))
            ok = ok and f.healthState == healthy and not f.isSuppressed
            if f.operation == adsk.fusion.FeatureOperations.CutFeatureOperation:
                attr = f.attributes.itemByName(ATTR_GROUP, ATTR_ID)
                cid = attr.value if attr else None
                if cid in found:
                    raise RuntimeError('Duplicate profile cut identity')
                found[cid] = f
            elif f.operation != adsk.fusion.FeatureOperations.NewBodyFeatureOperation:
                ok = False
        for i in range(comp.sketches.count):
            s = comp.sketches.item(i)
            sketches.append(dict(healthy=s.healthState == healthy, profiles=s.profiles.count,
                                 fully_constrained=s.isFullyConstrained))
            ok = ok and s.healthState == healthy and s.profiles.count == 1
            if profile:
                ok = ok and s.isFullyConstrained is True
        check(pid+'.features', ok and set(found) == expected_cuts,
              observed=dict(features=features, sketches=sketches, cut_ids=sorted(str(k) for k in found)))
        for cid in sorted(expected_cuts):
            if cid not in found:
                check(cid+'.affected_body_ownership', False)
            else:
                checks.append(affected_body_check(found[cid], SimpleNamespace(operation_id=cid, target_panel_id=pid)))
        if profile:
            # Component origin is deliberately zero; native sketch/extrude
            # expressions supply the profile origin, verified by world BReps.
            origin = adsk.core.Point3D.create(0, 0, 0)
            axes = [adsk.core.Vector3D.create(*a) for a in ((1,0,0),(0,1,0),(0,0,1))]
            transformed = [v.transformBy(occ.transform2) for v in [origin]+axes]
            observed = dict(origin_mm=[origin.x*10, origin.y*10, origin.z*10],
                            axes=[[v.x,v.y,v.z] for v in axes])
            report['frames'][pid] = observed
            actual = observed['origin_mm'] + sum(observed['axes'], [])
            wanted = [0,0,0] + list(profile.frame.u + profile.frame.v + profile.frame.w)
            check(pid+'.frame', all(v is True for v in transformed)
                  and all(math.isfinite(a) and abs(a-b) <= 1e-9 for a,b in zip(actual,wanted)))
    guard()
    report['outcome'] = 'PASS' if all(c['status']=='PASS' for c in checks) else 'FAIL'
    return report
