# RAC Research Workbench

**Status:** Implemented on `main`  
**Purpose:** Run RAC research through the web platform while keeping heavy compute and raw capture data local.

## Why this exists

GitHub Pages is a static hosting surface. It can run browser-side design/capture code, but it cannot safely execute the repository's Python, PyTorch, FFmpeg, detector, statistics, or evidence-ingestion stack.

The Research Workbench preserves the web platform as the operator control plane while adding a loopback-only local execution runtime.

```text
Browser UI (Research Console / Capture Lab)
                |
                | same-origin localhost API
                v
      RAC Research Runtime
       127.0.0.1 only
                |
                +--> existing Python tools
                +--> PyTorch / detector models
                +--> FFmpeg motion analysis
                +--> statistics / lineage
                +--> deterministic reports
                |
                v
      .rac-runtime/workspace
      (ignored by git)
```

Raw physical captures remain local unless the operator explicitly moves them elsewhere.

## Start the Workbench

After the project is installed:

```bash
rac-platform --open
```

Equivalent repository launchers:

- Windows: double-click `run-rac-platform.bat`
- Unix/macOS shell: `./run-rac-platform.sh`

Default URL:

```text
http://127.0.0.1:8765/research_console/
```

The runtime refuses non-loopback binding by design.

## GitHub Pages behavior

The public GitHub Pages deployment remains useful for:

- Pattern Lab;
- Product Studio;
- Production Mapper;
- Capture Lab previews / offline capture export;
- current program-state viewing;
- published evidence/release browsing.

When opened from GitHub Pages, Research Console automatically enters **STATIC / READ-ONLY MODE**. Execution buttons remain disabled.

## Platform execution catalog

The runtime exposes only named, allowlisted jobs. It does not expose an arbitrary shell command endpoint.

Current jobs:

| Job | Existing RAC implementation |
| --- | --- |
| Repository integrity | `scripts/check_stale_artifacts.py` |
| Full software tests | `pytest` |
| P1 no-spend readiness | `tools/p1_no_spend_readiness_gate.py` |
| Generate calibration target | `scripts/generate_calibration_target.py` |
| Validate sealed capture | `scripts/validate_capture_session.py` |
| Frozen detector analysis | `scripts/analyze_capture_session.py` |
| P1 inference ingestion/statistics | `scripts/ingest_capture_inference.py` |
| Refresh Research OS dashboard | `scripts/export_dashboard_data.py` |

New governed research operations should be added to the allowlist explicitly rather than exposing arbitrary command execution.

## Physical P1 from the platform

With the runtime connected:

1. Open **Capture Lab**.
2. Create/freeze the experiment/session manifest.
3. Complete calibration.
4. Capture matched CONTROL and CANDIDATE observations.
5. Freeze the ensemble analysis contract.
6. Seal the session.
7. Capture Lab automatically stages the sealed session and its raw files into:
   `.rac-runtime/workspace/sessions/<session-id>/`.
8. Open **Research Console**.
9. Run **Validate session**.
10. Run **Run frozen analysis**.
11. Inspect the completed job/log.
12. Run **Ingest into P1 trial store** only when the session is real `physical_garment_p1` evidence and calibration passed.
13. Continue the frozen schedule until the preregistered stopping rule closes the experiment.

The Research Console remembers only local workspace paths in browser local storage. Raw capture bytes remain in `.rac-runtime/workspace`.

## Security boundaries

The runtime is intentionally constrained:

- binds only to `127.0.0.1`, `localhost`, or `::1`;
- rejects non-local browser origins on API routes;
- uses `subprocess` with `shell=False`;
- exposes only predefined jobs;
- rejects `..` and absolute workspace paths;
- constrains runtime file uploads to `.rac-runtime/workspace`;
- caps individual browser uploads at 512 MiB;
- `.rac-runtime/` is ignored by git;
- does not accept provider credentials or GitHub tokens through the platform;
- does not weaken scientific promotion gates in the underlying scripts.

## Scientific boundaries

The Workbench is an execution/control layer, not a new evidence class.

Existing rules still apply:

- held-out data stays held-out;
- frozen protocols and candidate hashes remain immutable;
- control-undetected physical conditions remain invalid;
- raw video frames remain nested observations, not independent trials;
- only accepted `physical_garment_p1` sessions can enter the P1 cumulative store;
- failed jobs do not promote evidence;
- GitHub Pages/browser heuristics are not detector evidence.

## Extending the platform

The long-term model is that every governed research operation becomes a platform job with:

1. a stable job ID;
2. an explicit parameter schema;
3. a fixed executable implementation;
4. workspace-bounded file inputs/outputs;
5. scientific precondition checks inside the underlying tool;
6. visible runtime logs/status;
7. deterministic evidence/report outputs where applicable.

This lets future D2/P1/P2/M1/M2 work appear in the same Research Console without turning the platform into an unrestricted shell.
