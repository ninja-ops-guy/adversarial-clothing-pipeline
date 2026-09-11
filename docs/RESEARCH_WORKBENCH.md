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

The public GitHub Pages deployment remains useful for Pattern Lab, Product Studio, Production Mapper, Capture Lab previews/offline export, current program-state viewing, and published evidence/release browsing.

When opened from GitHub Pages, Research Console automatically enters **STATIC / READ-ONLY MODE**. Execution buttons remain disabled. A physical P1 run requires the local Workbench because the browser must obtain the frozen trial schedule from the runtime and stage the sealed capture privately.

## Platform execution catalog

The runtime exposes only named, allowlisted jobs. It does not expose an arbitrary shell command endpoint.

| Job | Existing RAC implementation |
| --- | --- |
| Repository integrity | `scripts/check_stale_artifacts.py` |
| Full software tests | `pytest` |
| P1 no-spend readiness | `tools/p1_no_spend_readiness_gate.py` |
| Generate calibration target | `scripts/generate_calibration_target.py` |
| Validate measured calibration | `scripts/validate_calibration_profile.py` / `p1_calibration_binding.py` |
| Validate sealed capture | `scripts/validate_capture_session.py` |
| Frozen detector analysis | `scripts/analyze_capture_session.py` |
| P1 inference ingestion/statistics | `scripts/ingest_capture_inference.py` |
| Refresh Research OS dashboard | `scripts/export_dashboard_data.py` |

New governed research operations should be added to the allowlist explicitly rather than exposing arbitrary command execution.

## Physical P1 from the platform

The platform is now the P1 operator flow rather than a wrapper around a terminal procedure.

1. Start the local Workbench and open **Capture Lab**.
2. Select **PHYSICAL GARMENT / P1**.
3. Click **Load Next Frozen P1 Trial**. The runtime derives the authoritative 144-trial schedule, reads the cumulative local trial store, chooses the next incomplete `RAC-P1-T-####`, and binds the session to the frozen schedule SHA-256.
4. Capture Lab locks the trial ID, distance, yaw, pitch, pose, lighting variant, and randomized first-arm order. Those fields cannot be improvised for the P1 session.
5. Load the measured **pre-capture `PrintCameraProfile` JSON**. The profile must contain exactly 48 measured patches, at least two scale observations, and the four frozen fiducials. Camera and lighting IDs must match the session. Capture Lab previews the frozen acceptance criteria: mean ΔE2000 ≤ 6.0, scale error ≤ 2.0%, and registration error ≤ 3.0 mm.
6. Only an accepted pre-capture calibration unlocks session freeze and garment capture. The exact source JSON text and its SHA-256 are retained; the browser result is not treated as final evidence.
7. Capture the matched pair in the frozen first-arm order. Capture outcomes remain blinded.
8. Freeze the detector-analysis contract after the pair is complete.
9. Run the measured **post-capture calibration**. It must be a distinct profile/source, pass the same frozen criteria, and have a later timestamp than the pre profile.
10. Only accepted pre + post calibration permits a physical P1 session to seal. The sealed session stores the exact source bytes/hashes for both brackets.
11. When the runtime is connected, Capture Lab automatically stages the sealed session and raw `control/` / `candidate/` files under `.rac-runtime/workspace/sessions/<session-id>/`.
12. Open **Research Console**. The workflow controls are fail-closed: **Validate session → Run frozen analysis → Ingest into P1 trial store**. Analyze remains disabled until validation succeeds; ingest remains disabled until validation and analysis both succeed for the current paths.
13. `validate_capture_session.py` independently re-parses and re-evaluates the exact calibration JSON sources, verifies the frozen schedule binding/first-arm order, and verifies capture hashes. Browser calculations are therefore operator feedback, not the evidence authority.
14. Ingestion preserves the frozen `RAC-P1-T-####` identity in the cumulative trial store. The next Capture Lab session then advances to the next incomplete frozen trial.
15. Continue until the preregistered stopping rule permits closure or the 144-trial maximum is reached.

Raw capture bytes and local trial-store data remain under `.rac-runtime/workspace` unless deliberately exported.

## Measured calibration input boundary

The platform consumes a measured `PrintCameraProfile` JSON because the values originate from the physical calibration procedure/instrumentation. RAC does not fabricate Lab, scale, or registration measurements from a browser image and does not classify synthetic values as physical evidence.

The platform controls profile validation, hashing, bracketing, session binding, and evidence admission. The physical act of printing the target, imaging/measuring it, and the physical garment itself remain real-world experimental operations.

## Results stay in the platform

The Research Console includes a local workspace browser. Inference JSON, statistics, calibration outputs, P1 session artifacts, and other generated research files can be opened from the Workbench instead of navigating the host filesystem. Job logs and status are streamed into the same surface.

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
- P1 session validation requires the frozen schedule plus accepted measured pre/post calibration;
- failed jobs do not promote evidence;
- GitHub Pages/browser heuristics are not detector evidence.

## Extending the platform

The long-term model is that every governed research operation becomes a platform job with a stable job ID, explicit parameter schema, fixed executable implementation, workspace-bounded inputs/outputs, scientific precondition checks, visible logs/status, and deterministic evidence/report outputs where applicable.

This lets future D2/P1/P2/M1/M2 work appear in the same Research Console without turning the platform into an unrestricted shell.
