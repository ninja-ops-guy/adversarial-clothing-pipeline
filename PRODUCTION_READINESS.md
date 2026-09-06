# Production Readiness Gates

| Gate | Status | Evidence / next action |
|---|---|---|
| Core package imports | PASS | `compileall` + tests |
| Unit tests | PASS | 5/5 |
| Standalone deliverables | PASS | all four entrypoints executed |
| Deterministic CI backend | PASS | procedural texture + synthetic deformation fixtures |
| Query budget enforcement | PASS | tested at hard max query count |
| Differentiable deformation | PASS | learned field + differentiable warp |
| Differentiable native cloth baseline | PASS | finite states + texture gradients |
| Held-out benchmark harness | PASS | surrogate/heldout reporting + transform sweep |
| Repository hygiene | PASS | private-by-default policy, CI, Dependabot, security guidance, generated-artifact ignores |
| Real Stable Diffusion prior | READY TO INTEGRATE | optional adapter present; dependency/model not installed here |
| Real CLIP aesthetic guidance | READY TO INTEGRATE | optional adapter present; dependency/model not installed here |
| Real detector ensemble | BLOCKED ON MODEL MANIFEST/WEIGHTS | add frozen open-model adapters and exact versions |
| Real multi-view deformation capture | BLOCKED ON CALIBRATED DATA | capture + correspondence preprocessing required |
| HOOD/DiffCloth high-fidelity backend | NOT YET | native baseline is functional; high-fidelity solver must be validated separately |
| ICC/fabric print calibration | NOT YET | replace approximate NPS palette with measured printer/fabric profile |
| Physical validation | NOT YET | pre-registered owned/authorized camera protocol |
| Product efficacy claim | NOT YET | requires held-out physical evidence + confidence intervals |

## Release criterion

Do not label the research system "product validated" until every external gate from detector manifest through physical validation is complete. The v3 package is production-hardened **software infrastructure**, not evidence that a garment will evade an arbitrary real-world surveillance system.
