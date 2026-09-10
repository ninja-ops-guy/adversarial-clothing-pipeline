#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from ruthless_pipeline.pattern_genome import extract_genome, load_config, write_genome

def main():
    p=argparse.ArgumentParser(); p.add_argument("--candidate",required=True); p.add_argument("--config",required=True); p.add_argument("--source-commit",required=True); p.add_argument("--runtime-lock",required=True); p.add_argument("--output",required=True); p.add_argument("--source-artifact-ref")
    a=p.parse_args(); data=Path(a.candidate).read_bytes(); sha=hashlib.sha256(data).hexdigest(); lock_sha=hashlib.sha256(Path(a.runtime_lock).read_bytes()).hexdigest(); cfg=load_config(a.config)
    g=extract_genome(data,candidate_sha256=sha,source_artifact_ref=a.source_artifact_ref or a.candidate,source_commit=a.source_commit,runtime_lock_sha256=lock_sha,config=cfg)
    write_genome(a.output,g); print(f"{g.genome_id} {sha}")
if __name__=="__main__": main()
