"""Fusion-side backend for the VanDesign runner (the only module here that uses ``adsk``).

It REUSES the verified G3 code instead of re-implementing it:

* measurement: ``vandesign`` from the configured G3 script folder (adapter,
  spec loader, variant builder, ``validate`` and the runner's own report writer);
* cut audit: the configured ``VanDesignCutAuditG3.py`` (``run_audit`` /
  ``render_text``), loaded fresh for every audit.

Existing-design operations never save. G4 reconstruction requires a fresh-fixture
ownership receipt and explicit target allowlisting. The separate demo_workflow
module guards creation, allowlisted builds and first saves of new sessions.
No operation deletes existing designs or exports manufacturing data.
All methods run on Fusion's main thread (called from a CustomEvent handler).
"""

import datetime
import hashlib
import importlib
import importlib.util
import json
import os
import sys

import adsk.core
import adsk.fusion


class BackendError(RuntimeError):
    pass


def _purge_vandesign():
    for name in [n for n in sys.modules if n == "vandesign" or n.startswith("vandesign.")]:
        del sys.modules[name]


class FusionBackend:
    def __init__(self, app, cfg):
        self.app = app
        self.cfg = cfg
        self.g3_dir = cfg["g3_script_dir"]
        self.audit_script = cfg["audit_script"]

    def demo_command(self, command, args, out_dir, job_id):
        from demo_workflow import execute
        return execute(self, command, args, out_dir, job_id)

    # ------------------------------------------------------------ helpers
    def _doc(self):
        doc = self.app.activeDocument
        if doc is None:
            raise BackendError("no active document")
        return doc

    def _design(self):
        design = adsk.fusion.Design.cast(self.app.activeProduct)
        if not design:
            raise BackendError("active product is not a Fusion design")
        return design

    def _g3(self):
        """Import the verified G3 package from its installed folder (fresh, never mixed with G2)."""
        _purge_vandesign()
        sys.path.insert(0, self.g3_dir)
        try:
            mods = {
                "runner": importlib.import_module("vandesign.cad.fusion.runner"),
                "adapter": importlib.import_module("vandesign.cad.fusion.adapter"),
                "design_spec": importlib.import_module("vandesign.schemas.design_spec"),
                "variants": importlib.import_module("vandesign.modules.variants"),
                "validate": importlib.import_module("vandesign.verification.validate"),
            }
        finally:
            try:
                sys.path.remove(self.g3_dir)
            except ValueError:
                pass
        origin = os.path.abspath(mods["runner"].__file__)
        if not origin.startswith(os.path.abspath(self.g3_dir)):
            raise BackendError("vandesign imported from unexpected location %s" % origin)
        return mods

    # ------------------------------------------------------------ identity
    def identity(self):
        out = {"fusion_version": self.app.version, "design_id": None, "document_name": None,
               "is_saved": False, "is_modified": None, "version_number": None}
        doc = self.app.activeDocument
        if doc is None:
            return out
        out["document_name"] = doc.name
        out["is_saved"] = bool(doc.isSaved)
        out["is_modified"] = bool(doc.isModified)
        try:
            df = doc.dataFile
            if df is not None:
                out["design_id"] = df.id
                out["version_number"] = df.versionNumber
                out["data_file_name"] = df.name
        except Exception:
            pass
        return out

    # ------------------------------------------------------------ read-only inspection
    def inspect(self):
        if self.app.activeDocument is None:
            from demo_workflow import destinations, inventory
            if self.app.documents.count != 0:
                raise BackendError('Missing active document with nonempty inventory')
            return {'no_active_design': True, 'cloud_destinations': destinations(self.app),
                    'session': inventory(self.app)}
        design = self._design()
        g3 = self._g3()
        adapter = g3["adapter"].FusionAdapter(design)
        params = []
        ups = design.userParameters
        for i in range(ups.count):
            p = ups.item(i)
            params.append({"name": p.name, "expression": p.expression, "unit": p.unit,
                           "value_mm": p.value * 10.0 if p.unit == "mm" else None})
        stored = adapter.stored_spec_json()
        tl = design.timeline
        src = adapter.geometry_source()
        from demo_workflow import destinations, inventory
        inspection = {
            "cloud_destinations": destinations(self.app),
            "identity": self.identity(),
            "design_type": "parametric" if design.designType == adsk.fusion.DesignTypes.ParametricDesignType else "direct",
            "has_managed_assembly": adapter.has_managed_assembly(),
            "stored_spec_sha256": hashlib.sha256(stored.encode("utf-8")).hexdigest() if stored else None,
            "design_counts": g3["runner"]._design_counts(design),
            "timeline": {"count": tl.count, "marker_position": tl.markerPosition},
            "managed_ids": src.managed_ids(),
            "user_parameters": params,
            "session": inventory(self.app),
        }
        inspection['profile_diagnostics'] = self._profile_diagnostics(design, inspection, g3['adapter'])
        return inspection

    def _profile_diagnostics(self, design, inspection, adapter_module):
        """Property reads only; recognition never grants ownership or edit authority."""
        result = dict(outcome='NOT_RUN', scope='profile feature properties only', components=[])
        expected_ids = {'profile.rounded.001': 1, 'profile.relieved.001': 1}
        params = inspection['user_parameters']
        if (inspection['identity']['is_saved'] is not False or inspection['design_type'] != 'parametric'
                or inspection['managed_ids'] != expected_ids
                or inspection['design_counts'] != dict(user_parameters=1, root_occurrences=2,
                                                       all_components=3, timeline_items=12)
                or inspection['timeline'] != dict(count=12, marker_position=12)
                or len(params) != 1 or params[0]['name'] != 'Profile_Thickness'
                or params[0]['unit'] != 'mm' or params[0]['value_mm'] != 18.0):
            result['reason'] = 'Active document does not match the bounded profile fixture signature'
            return result
        errors = []
        def read(getter, kind, label):
            try:
                value = getter()
                if type(value) is not kind or (kind is int and value < 0):
                    raise ValueError('Missing or invalid property')
                return value
            except Exception as exc:
                errors.append(dict(property=label, error=type(exc).__name__ + ': ' + str(exc)))
                return None
        try:
            from demo_workflow import documents, document_state, unchanged
            doc = self._doc()
            before = dict(app=self.app, existing=[(d, document_state(d)) for d in documents(self.app)])
            if not doc.isValid or not doc.isActive or design.rootComponent.bRepBodies.count or design.rootComponent.sketches.count:
                raise BackendError('Invalid active profile fixture')
            occurrences = adapter_module._find_occurrences(design.rootComponent)
            if {k: len(v) for k, v in occurrences.items()} != expected_ids:
                raise BackendError('Ambiguous profile identity')
            healthy = int(adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState)
            for pid in sorted(expected_ids):
                comp = occurrences[pid][0].component
                observed = dict(stable_id=pid, bodies=[], extrusions=[], sketches=[])
                result['components'].append(observed)
                for key, getter in (('body_count', lambda: comp.bRepBodies.count),
                                    ('feature_count', lambda: comp.features.count),
                                    ('extrusion_count', lambda: comp.features.extrudeFeatures.count),
                                    ('sketch_count', lambda: comp.sketches.count)):
                    observed[key] = read(getter, int, pid + '.' + key)
                for i in range(observed['body_count'] or 0):
                    body = comp.bRepBodies.item(i)
                    observed['bodies'].append(dict(index=i,
                        valid=read(lambda: body.isValid, bool, pid + '.body.valid'),
                        solid=read(lambda: body.isSolid, bool, pid + '.body.solid')))
                for i in range(observed['extrusion_count'] or 0):
                    f = comp.features.extrudeFeatures.item(i)
                    observed['extrusions'].append(dict(index=i,
                        health_state=read(lambda: int(f.healthState), int, pid + '.extrusion.health'),
                        suppressed=read(lambda: f.isSuppressed, bool, pid + '.extrusion.suppressed'),
                        operation=read(lambda: int(f.operation), int, pid + '.extrusion.operation')))
                for i in range(observed['sketch_count'] or 0):
                    s = comp.sketches.item(i)
                    observed['sketches'].append(dict(index=i,
                        profile_count=read(lambda: s.profiles.count, int, pid + '.sketch.profiles'),
                        health_state=read(lambda: int(s.healthState), int, pid + '.sketch.health'),
                        fully_constrained=read(lambda: s.isFullyConstrained, bool, pid + '.sketch.constrained')))
            # OBSERVED means complete property reads, never a geometry qualification.
            unchanged(before)
            if self.app.activeDocument != doc:
                raise BackendError('Active document changed during profile inspection')
            result.update(outcome='UNKNOWN' if errors else 'OBSERVED', healthy_state=healthy)
        except Exception as exc:
            errors.append(dict(property='profile_diagnostics', error=type(exc).__name__ + ': ' + str(exc)))
            result['outcome'] = 'UNKNOWN'
        result['errors'] = errors
        return result

    # ------------------------------------------------------------ measurement (G3 logic, measure path only)
    def measure(self, out_dir, label):
        design = self._design()
        g3 = self._g3()
        R = g3["runner"]
        adapter = g3["adapter"].FusionAdapter(design)
        if not adapter.has_managed_assembly():
            raise BackendError("no managed VanDesign cabinet in this design; the runner NEVER builds")
        stored = adapter.stored_spec_json()
        if not stored:
            raise BackendError("managed components found but no stored spec; cannot measure safely")
        design_spec = g3["design_spec"].load_design_spec(stored)
        raw_before = R._raw_sha256(stored)
        spec = design_spec.resolved_params
        assembly = g3["variants"].build_variant(spec, design_spec.profile)
        report = g3["validate"].validate(assembly, adapter.geometry_source(),
                                         profile_limits=g3["variants"].profile_limits(design_spec.profile),
                                         profile_variant=design_spec.variant)
        raw_after = R._raw_sha256(adapter.stored_spec_json())
        stored_info = {"raw_sha256_before": raw_before, "raw_sha256_after": raw_after,
                       "unchanged": raw_before == raw_after}
        os.makedirs(out_dir, exist_ok=True)
        json_path, txt_path = R._write_report(out_dir, self.app, design, spec, assembly, report, "measure",
                                              design_spec=design_spec, stored=stored_info)
        payload = json.load(open(json_path, encoding="utf-8"))
        checks = payload["validation"]["checks"]
        return {
            "label": label,
            "verdict": payload["validation"]["verdict"],
            "counts": payload["validation"]["counts"],
            "total": len(checks),
            "fail_ids": [c["check_id"] for c in checks if c["status"] == "FAIL"],
            "unknown_ids": [c["check_id"] for c in checks if c["status"] == "UNKNOWN"],
            "params_mm": payload["parameters_mm"],
            "design_counts": payload.get("design_counts"),
            "design_spec_hash": payload.get("design_spec_hash"),
            "variant": "%s@%s" % (payload.get("variant"), payload.get("profile_version")),
            "stored_unchanged": stored_info["unchanged"],
            "document_name": payload.get("document_name"),
            "report_json": os.path.relpath(json_path, out_dir),
            "report_txt": os.path.relpath(txt_path, out_dir),
        }

    # ------------------------------------------------------------ parameters
    def get_parameter(self, name):
        p = self._design().userParameters.itemByName(name)
        if p is None:
            return None
        if p.unit != "mm":
            raise BackendError("%s unit is %r, only mm parameters are supported" % (name, p.unit))
        return {"expression": p.expression, "value_mm": p.value * 10.0}

    def set_parameter_expression(self, name, expression):
        p = self._design().userParameters.itemByName(name)
        if p is None:
            raise BackendError("parameter %s not found" % name)
        p.expression = expression          # Fusion recomputes the parametric timeline
        adsk.doEvents()
        return p.value * 10.0

    # ------------------------------------------------------------ G4: safe width update support
    def g3_modules(self):
        g3 = self._g3()
        g3["expr"] = importlib.import_module("vandesign.core.expr")
        return g3

    def cabinet_state(self):
        """Read-only snapshot used to plan and verify an update."""
        design = self._design()
        g3 = self._g3()
        adapter = g3["adapter"].FusionAdapter(design)
        if not adapter.has_managed_assembly():
            raise BackendError("no managed VanDesign cabinet in this design")
        stored = adapter.stored_spec_json()
        if not stored:
            raise BackendError("managed cabinet has no stored specification")
        live = {}
        ups = design.userParameters
        for i in range(ups.count):
            p = ups.item(i)
            if p.name.startswith("Cab_"):
                live[p.name] = {"expression": p.expression, "unit": p.unit,
                                "value_mm": p.value * 10.0 if p.unit == "mm" else None}
        occs = []
        root = design.rootComponent
        for i in range(root.occurrences.count):
            occ = root.occurrences.item(i)
            attr = occ.component.attributes.itemByName("VanDesign", "stable_id")
            occs.append({"stable_id": attr.value if attr else None, "entity_token": occ.entityToken,
                         "component": occ.component.name, "bodies": occ.component.bRepBodies.count})
        return {"stored_text": stored, "live_params": live, "occurrences": occs,
                "timeline_count": design.timeline.count, "timeline_marker": design.timeline.markerPosition}

    def store_spec_text(self, text):
        """Write the updated spec through the G3 adapter's own attribute writer; return the read-back."""
        design = self._design()
        adapter = self._g3()["adapter"].FusionAdapter(design)
        adapter.store_spec_json(text)
        return adapter.stored_spec_json()

    def shelf_state(self):
        g3 = self._g3()
        adapter = g3["adapter"].FusionAdapter(self._design())
        stored = adapter.stored_spec_json()
        ds = g3["design_spec"].load_design_spec(stored)
        assembly = g3["variants"].build_variant(ds.resolved_params, ds.profile)
        from vandesign.cad.fusion.shelf_regeneration import verified_state
        state = verified_state(adapter, assembly)  # any unavailable read refuses the operation
        return {"stored_text": stored, "live_params": state["live_params"],
                "ownership_verified": True, "inventory": state, "identity": self.identity()}

    def begin_shelf_regeneration(self, new_stored_text):
        g3 = self._g3()
        from vandesign.cad.fusion.shelf_regeneration import Reconstruction, ShelfFixtureAdapter
        adapter = ShelfFixtureAdapter(self._design())
        def assembly(text):
            ds = g3["design_spec"].load_design_spec(text)
            return g3["variants"].build_variant(ds.resolved_params, ds.profile)
        return Reconstruction(adapter, assembly(adapter.stored_spec_json()), assembly(new_stored_text))

    # ------------------------------------------------------------ independent cut audit (G3 audit script)
    def audit(self, out_dir, label):
        design = self._design()
        spec = importlib.util.spec_from_file_location("vandesign_cut_audit_g3_runner", self.audit_script)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        audit = mod.run_audit(design, adsk.fusion.FeatureOperations.CutFeatureOperation)
        doc_name = self._doc().name
        text = mod.render_text(doc_name, audit)
        os.makedirs(out_dir, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        base = os.path.join(out_dir, "cut_audit_g3_%s" % stamp)
        with open(base + ".txt", "w", encoding="utf-8") as fh:
            fh.write(text)
        with open(base + ".json", "w", encoding="utf-8") as fh:
            json.dump({"document_name": doc_name, "fusion_version": self.app.version, **audit}, fh, indent=2)
        results = audit.get("results", [])
        return {
            "label": label,
            "overall": audit.get("overall"),
            "features_passed": sum(1 for r in results if r["status"] == "PASS"),
            "features_total": len(results),
            "operations": {r["operation_id"]: r["status"] for r in results},
            "timeline_restored": audit.get("timeline_restored"),
            "counts_equal": audit.get("counts_before") == audit.get("counts_after"),
            "counts_after": audit.get("counts_after"),
            "report_txt": os.path.basename(base + ".txt"),
            "report_json": os.path.basename(base + ".json"),
        }
