from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import subprocess
import sys
import threading
import time
import uuid
import webbrowser
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = REPO_ROOT / ".rac-runtime"
WORKSPACE_ROOT = RUNTIME_ROOT / "workspace"
RUNS_ROOT = RUNTIME_ROOT / "runs"
MAX_UPLOAD_BYTES = 512 * 1024 * 1024

_RUNS: dict[str, dict[str, Any]] = {}
_RUNS_LOCK = threading.Lock()

JOB_CATALOG: dict[str, dict[str, Any]] = {
    "repo_integrity": {
        "title": "Repository integrity",
        "description": "Run the deterministic stale-artifact/integrity audit.",
        "params": {},
    },
    "repo_tests": {
        "title": "Full software test suite",
        "description": "Run pytest against the current working tree.",
        "params": {},
    },
    "p1_readiness": {
        "title": "P1 no-spend readiness",
        "description": "Run the fail-closed P1 readiness gate.",
        "params": {},
    },
    "generate_calibration_target": {
        "title": "Generate P1 calibration target",
        "description": "Generate RAC-CALT-P1-0001 into the local runtime workspace.",
        "params": {"output_dir": {"type": "path", "default": "calibration/RAC-CALT-P1-0001"}},
    },
    "validate_capture": {
        "title": "Validate sealed Capture Lab session",
        "description": "Verify the exported session schema, frozen schedule binding, hashes, and local capture files.",
        "params": {"session": {"type": "path", "required": True}},
    },
    "analyze_capture": {
        "title": "Run frozen detector analysis",
        "description": "Run the authorized frozen person-detection ensemble on a sealed session.",
        "params": {
            "session": {"type": "path", "required": True},
            "output": {"type": "path", "default": "results/inference.json"},
            "include_motion": {"type": "bool", "default": True},
        },
    },
    "ingest_capture": {
        "title": "Ingest P1 trial",
        "description": "Convert sealed inference into cumulative P1 statistics and lineage.",
        "params": {
            "session": {"type": "path", "required": True},
            "inference": {"type": "path", "required": True},
            "source": {"type": "enum", "values": ["still", "motion"], "default": "motion"},
            "output_dir": {"type": "path", "default": "results/p1"},
            "trial_store": {"type": "path", "default": "research/p1/trials.jsonl"},
        },
    },
    "refresh_dashboard": {
        "title": "Refresh Research OS dashboard",
        "description": "Regenerate the deterministic dashboard artifact from repository state.",
        "params": {},
    },
}


def _workspace_path(value: str, *, require_exists: bool = False) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("workspace path must be a non-empty string")
    rel = Path(value.replace("\\", "/"))
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError("workspace path must stay within the runtime workspace")
    path = (WORKSPACE_ROOT / rel).resolve()
    root = WORKSPACE_ROOT.resolve()
    if path != root and root not in path.parents:
        raise ValueError("workspace path escaped the runtime workspace")
    if require_exists and not path.exists():
        raise ValueError(f"workspace input does not exist: {value}")
    return path


def _bool_param(params: dict[str, Any], name: str, default: bool) -> bool:
    value = params.get(name, default)
    if isinstance(value, bool):
        return value
    raise ValueError(f"{name} must be a boolean")


def _enum_param(params: dict[str, Any], name: str, values: tuple[str, ...], default: str) -> str:
    value = params.get(name, default)
    if value not in values:
        raise ValueError(f"{name} must be one of {values}")
    return str(value)


def build_job_command(job_id: str, params: dict[str, Any] | None = None) -> list[str]:
    params = params or {}
    py = sys.executable
    if job_id == "repo_integrity":
        return [py, "scripts/check_stale_artifacts.py"]
    if job_id == "repo_tests":
        return [py, "-m", "pytest"]
    if job_id == "p1_readiness":
        return [py, "tools/p1_no_spend_readiness_gate.py"]
    if job_id == "generate_calibration_target":
        out = _workspace_path(str(params.get("output_dir", "calibration/RAC-CALT-P1-0001")))
        out.mkdir(parents=True, exist_ok=True)
        return [py, "scripts/generate_calibration_target.py", "--output-dir", str(out)]
    if job_id == "validate_capture":
        session = _workspace_path(str(params.get("session", "")), require_exists=True)
        return [py, "scripts/validate_capture_session.py", str(session), "--verify-files"]
    if job_id == "analyze_capture":
        session = _workspace_path(str(params.get("session", "")), require_exists=True)
        output = _workspace_path(str(params.get("output", "results/inference.json")))
        output.parent.mkdir(parents=True, exist_ok=True)
        command = [py, "scripts/analyze_capture_session.py", str(session), "--output", str(output)]
        if _bool_param(params, "include_motion", True):
            command.append("--include-motion")
        return command
    if job_id == "ingest_capture":
        session = _workspace_path(str(params.get("session", "")), require_exists=True)
        inference = _workspace_path(str(params.get("inference", "")), require_exists=True)
        source = _enum_param(params, "source", ("still", "motion"), "motion")
        output_dir = _workspace_path(str(params.get("output_dir", "results/p1")))
        trial_store = _workspace_path(str(params.get("trial_store", "research/p1/trials.jsonl")))
        output_dir.mkdir(parents=True, exist_ok=True)
        trial_store.parent.mkdir(parents=True, exist_ok=True)
        return [
            py,
            "scripts/ingest_capture_inference.py",
            str(session),
            str(inference),
            "--source",
            source,
            "--trial-store",
            str(trial_store),
            "--output-dir",
            str(output_dir),
        ]
    if job_id == "refresh_dashboard":
        return [py, "scripts/export_dashboard_data.py"]
    raise ValueError(f"unknown research job: {job_id}")


def _write_status(run_id: str) -> None:
    record = _RUNS[run_id]
    run_dir = RUNS_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    public = {k: v for k, v in record.items() if k != "command"}
    (run_dir / "status.json").write_text(json.dumps(public, indent=2, sort_keys=True) + "\n")


def _execute_run(run_id: str) -> None:
    with _RUNS_LOCK:
        record = _RUNS[run_id]
        record["status"] = "running"
        record["started_at"] = time.time()
        _write_status(run_id)
        command = list(record["command"])
    run_dir = RUNS_ROOT / run_id
    log_path = run_dir / "run.log"
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    try:
        with log_path.open("w", encoding="utf-8", errors="replace") as log:
            process = subprocess.Popen(
                command,
                cwd=REPO_ROOT,
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
                shell=False,
            )
            return_code = process.wait()
        with _RUNS_LOCK:
            record = _RUNS[run_id]
            record["return_code"] = return_code
            record["status"] = "succeeded" if return_code == 0 else "failed"
            record["finished_at"] = time.time()
            _write_status(run_id)
    except Exception as exc:  # pragma: no cover
        with log_path.open("a", encoding="utf-8", errors="replace") as log:
            log.write(f"\nRAC platform runtime error: {exc}\n")
        with _RUNS_LOCK:
            record = _RUNS[run_id]
            record["return_code"] = None
            record["status"] = "failed"
            record["error"] = str(exc)
            record["finished_at"] = time.time()
            _write_status(run_id)


def launch_job(job_id: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    command = build_job_command(job_id, params)
    run_id = uuid.uuid4().hex[:12]
    with _RUNS_LOCK:
        _RUNS[run_id] = {
            "run_id": run_id,
            "job_id": job_id,
            "title": JOB_CATALOG[job_id]["title"],
            "status": "queued",
            "created_at": time.time(),
            "started_at": None,
            "finished_at": None,
            "return_code": None,
            "params": params or {},
            "command": command,
        }
        _write_status(run_id)
    threading.Thread(target=_execute_run, args=(run_id,), daemon=True).start()
    return {k: v for k, v in _RUNS[run_id].items() if k != "command"}


def get_run(run_id: str) -> dict[str, Any] | None:
    with _RUNS_LOCK:
        record = _RUNS.get(run_id)
        if not record:
            return None
        payload = {k: v for k, v in record.items() if k != "command"}
    log_path = RUNS_ROOT / run_id / "run.log"
    payload["log_tail"] = (
        log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-200:]
        if log_path.exists()
        else []
    )
    return payload


def list_workspace(prefix: str = "") -> list[dict[str, Any]]:
    base = _workspace_path(prefix) if prefix else WORKSPACE_ROOT
    if not base.exists():
        return []
    candidates = [base] if base.is_file() else sorted(
        (p for p in base.rglob("*") if p.is_file()), key=lambda p: str(p)
    )[:1000]
    return [
        {
            "path": str(path.relative_to(WORKSPACE_ROOT)).replace("\\", "/"),
            "bytes": path.stat().st_size,
            "modified": path.stat().st_mtime,
        }
        for path in candidates
    ]


def p1_schedule_progress(trial_store: str = "research/p1/trials.jsonl") -> dict[str, Any]:
    from ruthless_pipeline.certification import p1_pairing_schedule as ps

    schedule = ps.derive_schedule()
    completed: set[str] = set()
    store_path = _workspace_path(trial_store)
    if store_path.exists():
        from scripts.ingest_capture_inference import load_trial_store

        completed = {str(record["trial"]["trial_id"]) for record in load_trial_store(store_path)}
    next_trial = next((entry for entry in schedule if entry["trial_id"] not in completed), None)
    return {
        "contract_id": ps.CONTRACT_ID,
        "schedule_sha256": ps.schedule_sha256(schedule),
        "planned_trials": ps.EXPECTED_TRIALS,
        "completed_trials": len(completed),
        "remaining_trials": ps.EXPECTED_TRIALS - len(completed),
        "completed_trial_ids": sorted(completed),
        "next_trial": next_trial,
        "schedule": schedule,
        "trial_store": trial_store,
    }


class RuntimeHandler(SimpleHTTPRequestHandler):
    server_version = "RACResearchRuntime/1.2"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(REPO_ROOT), **kwargs)

    def _origin_allowed(self) -> bool:
        origin = self.headers.get("Origin")
        if not origin:
            return True
        try:
            parsed = urlparse(origin)
        except ValueError:
            return False
        return parsed.hostname in {"127.0.0.1", "localhost", "::1"}

    def _json(self, payload: Any, status: int = HTTPStatus.OK) -> None:
        body = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 2 * 1024 * 1024:
            raise ValueError("invalid JSON request size")
        payload = json.loads(self.rfile.read(length))
        if not isinstance(payload, dict):
            raise ValueError("JSON body must be an object")
        return payload

    def _send_workspace_file(self, rel: str) -> None:
        try:
            path = _workspace_path(rel, require_exists=True)
        except ValueError as exc:
            self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        if not path.is_file():
            self._json({"error": "workspace path is not a file"}, HTTPStatus.BAD_REQUEST)
            return
        body = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/runtime/") and not self._origin_allowed():
            self._json({"error": "origin refused"}, HTTPStatus.FORBIDDEN)
            return
        if parsed.path == "/api/runtime/status":
            self._json(
                {
                    "connected": True,
                    "runtime_version": "1.2",
                    "python": sys.version.split()[0],
                    "workspace": str(WORKSPACE_ROOT),
                    "repo_root": str(REPO_ROOT),
                    "running": sum(1 for r in _RUNS.values() if r["status"] in {"queued", "running"}),
                }
            )
            return
        if parsed.path == "/api/runtime/catalog":
            self._json({"jobs": JOB_CATALOG})
            return
        if parsed.path == "/api/runtime/p1/schedule":
            trial_store = parse_qs(parsed.query).get("trial_store", ["research/p1/trials.jsonl"])[0]
            try:
                self._json(p1_schedule_progress(trial_store))
            except (ValueError, json.JSONDecodeError) as exc:
                self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        if parsed.path == "/api/runtime/workspace":
            prefix = parse_qs(parsed.query).get("prefix", [""])[0]
            try:
                self._json({"files": list_workspace(prefix)})
            except ValueError as exc:
                self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        workspace_prefix = "/api/runtime/workspace/"
        if parsed.path.startswith(workspace_prefix):
            self._send_workspace_file(unquote(parsed.path[len(workspace_prefix):]))
            return
        if parsed.path == "/api/runtime/runs":
            with _RUNS_LOCK:
                runs = [{k: v for k, v in record.items() if k != "command"} for record in _RUNS.values()]
            runs.sort(key=lambda record: record["created_at"], reverse=True)
            self._json({"runs": runs})
            return
        if parsed.path.startswith("/api/runtime/runs/"):
            run_id = parsed.path.rsplit("/", 1)[-1]
            payload = get_run(run_id)
            self._json(payload if payload else {"error": "run not found"}, HTTPStatus.OK if payload else HTTPStatus.NOT_FOUND)
            return
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        if not self._origin_allowed():
            self._json({"error": "origin refused"}, HTTPStatus.FORBIDDEN)
            return
        if urlparse(self.path).path != "/api/runtime/run":
            self._json({"error": "unknown API route"}, HTTPStatus.NOT_FOUND)
            return
        try:
            payload = self._read_json()
            job_id = str(payload.get("job_id", ""))
            params = payload.get("params") or {}
            if not isinstance(params, dict):
                raise ValueError("params must be an object")
            self._json(launch_job(job_id, params), HTTPStatus.ACCEPTED)
        except (ValueError, json.JSONDecodeError) as exc:
            self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def do_PUT(self) -> None:  # noqa: N802
        if not self._origin_allowed():
            self._json({"error": "origin refused"}, HTTPStatus.FORBIDDEN)
            return
        parsed = urlparse(self.path)
        prefix = "/api/runtime/workspace/"
        if not parsed.path.startswith(prefix):
            self._json({"error": "unknown API route"}, HTTPStatus.NOT_FOUND)
            return
        try:
            destination = _workspace_path(unquote(parsed.path[len(prefix):]))
            length = int(self.headers.get("Content-Length", "0"))
            if length < 0 or length > MAX_UPLOAD_BYTES:
                raise ValueError("upload exceeds runtime limit")
            destination.parent.mkdir(parents=True, exist_ok=True)
            digest = hashlib.sha256()
            remaining = length
            with destination.open("wb") as handle:
                while remaining:
                    chunk = self.rfile.read(min(1024 * 1024, remaining))
                    if not chunk:
                        raise ValueError("upload ended before Content-Length bytes were received")
                    handle.write(chunk)
                    digest.update(chunk)
                    remaining -= len(chunk)
            self._json(
                {
                    "path": str(destination.relative_to(WORKSPACE_ROOT)).replace("\\", "/"),
                    "bytes": length,
                    "sha256": digest.hexdigest(),
                },
                HTTPStatus.CREATED,
            )
        except ValueError as exc:
            self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("[RAC runtime] " + fmt % args + "\n")


def serve(host: str = "127.0.0.1", port: int = 8765, *, open_browser: bool = False) -> None:
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("RAC research runtime is loopback-only by design")
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
    RUNS_ROOT.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((host, port), RuntimeHandler)
    url = f"http://127.0.0.1:{port}/research_console/"
    print(f"RAC Research Workbench: {url}")
    print(f"Local workspace: {WORKSPACE_ROOT}")
    if open_browser:
        threading.Timer(0.35, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Serve the RAC web platform with a loopback-only research execution runtime.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--open", action="store_true", dest="open_browser")
    args = parser.parse_args(argv)
    serve(args.host, args.port, open_browser=args.open_browser)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
