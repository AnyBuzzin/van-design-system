"""VanDesign Runner - Fusion add-in that executes validated local jobs.

A background thread ONLY watches the queue folder and writes the heartbeat;
it never touches the Fusion API.  When a job is waiting it fires a Fusion
CustomEvent; the handler runs on Fusion's main thread and executes exactly one
job at a time through ``vdrunner.executor.Executor`` + ``FusionBackend``.
"""

import json
import os
import sys
import threading
import time
import traceback

import adsk.core
import adsk.fusion

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
# Fusion keeps imported modules alive across add-in stop/start in the same session.
# Drop ours so an upgraded install is really loaded on restart (found in real use).
for _name in [n for n in sys.modules if n in ("vdrunner", "fusion_backend", "demo_workflow") or n.startswith("vdrunner.")]:
    del sys.modules[_name]

from vdrunner import RUNNER_VERSION  # noqa: E402
from vdrunner.executor import Executor  # noqa: E402
from vdrunner.policy import load_config  # noqa: E402
from vdrunner.queue import DuplicateJob, JobQueue  # noqa: E402
from vdrunner.schema import JobSchemaError, validate_job  # noqa: E402

EVENT_ID = "VanDesignRunner_JobReady_v1"
POLL_S = 0.5
HEARTBEAT_S = 2.0

_app = None
_cfg = None
_queue = None
_event = None
_handlers = []
_stop = threading.Event()
_thread = None
_busy = threading.Lock()
_fired = threading.Event()
_info = {}


def _log(msg):
    line = "[VanDesignRunner %s] %s" % (time.strftime("%H:%M:%S"), msg)
    try:
        _app.log(line)
    except Exception:
        pass
    try:
        with open(_queue.p("runner", "runner.log"), "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception:
        pass


def _process_one():
    """Main thread.  Claim and execute at most one queued job."""
    if not _busy.acquire(blocking=False):
        return
    try:
        _fired.clear()
        for jid in _queue.pending()[:1]:
            try:
                job = _queue.claim(jid)
            except DuplicateJob as e:
                _log("DUPLICATE refused: %s" % e)
                continue
            except FileNotFoundError:
                continue  # cancelled between listing and claiming
            try:
                validate_job(job)
            except JobSchemaError as e:
                _queue.reject(jid, "schema: %s" % e)
                _log("REJECTED %s: %s" % (jid, e))
                continue
            _log("RUN %s (%s)" % (jid, job["command"]))
            from fusion_backend import FusionBackend
            evidence = os.path.join(_queue.result_dir(jid), "evidence")
            try:
                # Re-read the safety policy for every job so allowlist/protection changes
                # (including removals) take effect immediately without a restart.
                cfg = load_config(os.path.join(_HERE, "config.json"))
                if os.path.abspath(cfg["queue_root"]) != os.path.abspath(_cfg["queue_root"]):
                    raise RuntimeError("queue_root changed in config.json; restart the add-in")
                result = Executor(FusionBackend(_app, cfg), cfg, _queue.p("journal")).run(job, evidence)
            except Exception:
                result = {"job_id": jid, "outcome": "FAIL", "error": "runner internal error",
                          "traceback": traceback.format_exc()}
            _queue.finish(jid, result)
            _log("DONE %s outcome=%s elapsed_ms=%s" % (jid, result.get("outcome"), result.get("elapsed_ms")))
    finally:
        _busy.release()


class _JobReadyHandler(adsk.core.CustomEventHandler):
    def notify(self, args):
        try:
            _process_one()
        except Exception:
            _log("handler error:\n" + traceback.format_exc())


def _watch():
    """Background thread: filesystem + heartbeat only.  No Fusion API calls except fireCustomEvent."""
    last_hb = 0.0
    while not _stop.wait(POLL_S):
        try:
            now = time.time()
            if now - last_hb >= HEARTBEAT_S:
                _queue.heartbeat(dict(_info, busy=_busy.locked()))
                last_hb = now
            if not _busy.locked() and not _fired.is_set() and _queue.pending():
                _fired.set()
                _app.fireCustomEvent(EVENT_ID, "")
        except Exception:
            pass


def run(context):
    global _app, _cfg, _queue, _event, _thread
    _app = adsk.core.Application.get()
    try:
        t0 = time.perf_counter()
        _cfg = load_config(os.path.join(_HERE, "config.json"))
        _queue = JobQueue(_cfg["queue_root"]).ensure()
        interrupted = _queue.recover_interrupted()
        _event = _app.registerCustomEvent(EVENT_ID)
        h = _JobReadyHandler()
        _event.add(h)
        _handlers.append(h)
        _info.update(runner_version=RUNNER_VERSION, fusion_version=_app.version, addin_dir=_HERE,
                     g3_script_dir=_cfg["g3_script_dir"], started_utc=time.strftime("%Y-%m-%dT%H:%M:%S"),
                     startup_ms=None)
        _stop.clear()
        _thread = threading.Thread(target=_watch, name="VanDesignRunnerWatch", daemon=True)
        _thread.start()
        _info["startup_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        _queue.heartbeat(dict(_info, busy=False))
        _log("started v%s, queue %s, startup %.1f ms%s" % (
            RUNNER_VERSION, _cfg["queue_root"], _info["startup_ms"],
            ("; INTERRUPTED jobs marked UNKNOWN: %s" % interrupted) if interrupted else ""))
    except Exception:
        msg = traceback.format_exc()
        try:
            _app.log("[VanDesignRunner] failed to start:\n" + msg)
            _app.userInterface.messageBox("VanDesign Runner failed to start:\n\n" + msg)
        except Exception:
            pass


def stop(context):
    try:
        _stop.set()
        if _thread is not None:
            _thread.join(timeout=3)
        if _event is not None:
            for h in _handlers:
                _event.remove(h)
        _handlers.clear()
        if _app is not None:
            _app.unregisterCustomEvent(EVENT_ID)
        if _queue is not None:
            _queue.heartbeat(dict(_info, busy=False, stopped=True))
            _log("stopped")
    except Exception:
        pass
