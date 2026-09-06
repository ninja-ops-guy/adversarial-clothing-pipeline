import json
import subprocess
import sys
from pathlib import Path


def test_finalize_model_lock_requires_matching_predeclared_model_contract(tmp_path: Path):
    manifest = {
        "models": [
            {
                "id": "a",
                "framework": "fw",
                "model_ref": "ref",
                "role": "heldout",
                "decision_threshold": 0.5,
                "state_dict_sha256": "UNFROZEN",
            }
        ]
    }
    proposal = {
        "generated_from_commit": "abc",
        "models": {
            "a": {
                "framework": "fw",
                "model_ref": "ref",
                "role": "heldout",
                "decision_threshold": 0.5,
                "state_dict_sha256": "1" * 64,
            }
        },
    }
    model_set = {"model_set_id": "X", "status": "LOCK_PENDING"}
    manifest_path = tmp_path / "manifest.json"
    proposal_path = tmp_path / "proposal.json"
    sur_path = tmp_path / "sur.json"
    ho_path = tmp_path / "ho.json"
    manifest_path.write_text(json.dumps(manifest))
    proposal_path.write_text(json.dumps(proposal))
    sur_path.write_text(json.dumps(model_set))
    ho_path.write_text(json.dumps(model_set))

    subprocess.run(
        [
            sys.executable,
            "scripts/finalize_model_lock.py",
            "--proposal",
            str(proposal_path),
            "--manifest",
            str(manifest_path),
            "--surrogate-set",
            str(sur_path),
            "--heldout-set",
            str(ho_path),
        ],
        check=True,
    )
    locked = json.loads(manifest_path.read_text())
    assert locked["models"][0]["state_dict_sha256"] == "1" * 64
    assert locked["lock_status"] == "PREREGISTERED"
