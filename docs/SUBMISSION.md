# Submission and review guide

## Deliverables

- Source repository with shared Python service, CLI, REST API, dashboard, and tests.
- Installable wheel and source archive from `python scripts/build_release.py`.
- README and maintained architecture reference in `decisions.md`.
- Exported JSON/Markdown evidence, raw artifacts, and a methods/results report.
- Real-model experiments following `EXPERIMENTS.md` before claiming generalizability.

## Five-minute review demonstration

1. Install the release wheel in a Python environment and run `driftlab serve`.
2. Open `/app/`; show an honestly empty workspace or previously recorded evaluations.
3. Click **Run a synthetic walkthrough**. Explain the stable versus injected-regression profiles and synthetic labels. Both runs execute and persist through the same backend as local models.
4. Inspect the comparison: confidence intervals, practical margin, adjusted p-values, sample counts, and high-risk regression.
5. Export JSON and a Markdown report. Reload the application and show persisted comparison history.
6. Open a run to inspect prompt, reference, actual output, metric scores, model and dataset fingerprints.
7. Visit the studio to demonstrate dataset import, arbitrary installed Ollama identifiers, generation parameters, repeat count, and sample-policy preview.
8. Show the Python package example and CLI comparison to establish that the package is the final implementation, shared by the UI.
9. Present separately recorded real-model experiments, if completed, and discuss uncertainty and limitations.

## Verification commands

```bash
venv/bin/python -m pytest tests/
npm run build --prefix frontend
venv/bin/python scripts/build_release.py
```

Install `dist/driftlab-0.1.0-py3-none-any.whl` in a clean environment and verify imports, `driftlab version`, a baseline/candidate comparison, and the `/app/` route outside the source checkout. Keep artifacts out of Git; deliver the wheel/archive and experiment evidence alongside the report.

## Scope compared with the synopsis

| Synopsis promise | Implemented software | Empirical evidence required |
| --- | --- | --- |
| Python evaluation framework | Public DriftLab class, adapter contract, CLI, wheel | Installed-package smoke test |
| Risk-aware repeated evaluation | Validated tasks, repeated execution, tier policies | Domain justification for chosen margins |
| Distinguish variability and change | Prompt-level bootstrap, permutation test, Holm adjustment, noise estimate | Independent same-model controls and power analysis |
| Local reproducible experiments | Ollama adapter, full model metadata, seeds, manifests | Actual local model runs and hardware log |
| Multiple families/datasets | Arbitrary Ollama identifiers and JSON/JSONL datasets; study runner | Complete selected cross-family/dataset experiments |
| Informative final frontend | Integrated studio, history, analytics, plots, evidence and exports | Browser and complete workflow verification |

Do not describe an experiment protocol as completed validation. State the tested conditions, sample sizes, limitations, and remaining experiments clearly in the submission.
