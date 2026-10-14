"""Fusion-side backend for the VanDesign runner (the only module here that uses ``adsk``).

It REUSES the verified G3 code instead of re-implementing it:

* measurement: ``vandesign`` from the configured G3 script folder (adapter,
  spec loader, variant builder, ``validate`` and the runner's own report writer);
* cut audit: the configured ``VanDesignCutAuditG3.py`` (``run_audit`` /
  ``render_text``), loaded fresh for every audit.

It never builds a cabinet, never saves, never deletes and never exports.
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
        return {
            "identity": self.identity(),
            "design_type": "parametric" if design.designType == adsk.fusion.DesignTypes.ParametricDesignType else "direct",
            "has_managed_assembly": adapter.has_managed_assembly(),
            "stored_spec_sha256": hashlib.sha256(stored.encode("utf-8")).hexdigest() if stored else None,
            "design_counts": g3["runner"]._design_counts(design),
            "timeline": {"count": tl.count, "marker_position": tl.markerPosition},
            "managed_ids": src.managed_ids(),
            "user_parameters": params,
        }

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
