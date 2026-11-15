# Verification and measured pilot results

Verified locally on 15 November 2026. This record distinguishes working software, synthetic calibration, and a small real-model pilot.

## Software verification

- All **52 Python tests passed** locally, including the optional embedding test. Core tests cover statistics, ordered decisions, validation, failure persistence, datasets, adapters, metrics, CLI, API, and saved evidence.
- TypeScript checking and the Vite production build pass.
- The release builder produces a wheel with dashboard assets and a complete source archive.
- `scripts/verify_release.py` installs the wheel into an isolated target outside the checkout and verifies actual installed imports, packaged dashboard/JavaScript routes, 320 synthetic generations, and saved high-risk-regression evidence. Dependencies are reused from the verified environment; this is not an independent fresh dependency-resolution test.
- Browser verification exercised the empty workspace, persisted synthetic walkthrough, numerical evidence expansion, studio submission, recorded-output inspection, and a 390px layout with no document-wide horizontal overflow.
- GitHub Actions defines the core test and release checks. Remote CI execution is separate from these local observations.

## Real local-model pilot

Environment: Apple M4; macOS arm64; Python 3.14.8; Ollama 0.40.16. Models: Qwen2.5 0.5B and SmolLM2 360M, with full installed model digests retained in the run manifests. Dataset preparation, attribution, hashes, split selection, and exact sample indices are recorded beside the prepared files; see [MODELS_AND_DATA.md](MODELS_AND_DATA.md).

Each dataset used 30 distinct prompts and five repeats. Qwen baseline seed 42, independent Qwen control seed 1042, SmolLM2 candidate seed 2042. Temperature 0.7; 128 maximum generated tokens; `answer_match`; medium-risk policy. All six runs completed, producing **900 real generations** and four saved comparisons. Raw files, SQLite evidence, and full exported JSON/Markdown stay in local artifact directories rather than Git.

| Dataset | Condition | Baseline answer agreement | Candidate answer agreement | Candidate − baseline | 95% interval | Adjusted p | Verdict |
| --- | --- | ---: | ---: | ---: | --- | ---: | --- |
| GSM8K | Qwen independent-seed control | 0.027 | 0.047 | +0.020 | [−0.013, +0.067] | 0.5037 | Insufficient evidence |
| GSM8K | Qwen → SmolLM2 | 0.027 | 0.027 | +0.000 | [−0.020, +0.040] | 1.0000 | No meaningful drift under this policy |
| BoolQ | Qwen independent-seed control | 0.613 | 0.647 | +0.033 | [−0.060, +0.131] | 0.4263 | Insufficient evidence |
| BoolQ | Qwen → SmolLM2 | 0.613 | 0.567 | −0.047 | [−0.233, +0.133] | 0.3893 | Insufficient evidence |

The procedure uses the same scoring and decision pipeline for both families and datasets. It does not force a drift verdict when data are inconclusive. Holm correction is applied within each saved comparison; the exploratory comparisons across the entire study are not jointly corrected.

## Interpretation

The low math accuracy is a material finding about this configuration. Both models are small, the token cap can truncate mathematical explanations, and extracted-answer agreement does not evaluate reasoning correctness. Equal low accuracy does not mean the models are useful for the task. The equivalence verdict is limited to the selected metric, prompts, and ±0.05 practical margin.

The same-model controls did not produce significant drift, but two controls are insufficient to estimate a reliable false positive rate. Broad intervals on BoolQ show why stronger conclusions would require more independent prompts or a better-powered design. Cross-family comparisons do not isolate an update mechanism; within-family version or quantization changes are a suitable next experiment.

Risk policy values are illustrative rather than empirically established domain safety thresholds. The synthetic stable/regression experiment separately verifies high-risk-regression detection under an injected effect; synthetic evidence must not be presented as a real-model quality result.

## Reproduce and export

```bash
venv/bin/python scripts/prepare_benchmarks.py
ollama pull qwen2.5:0.5b
ollama pull smollm2:360m
venv/bin/python examples/local_model_study.py \
  --models qwen2.5:0.5b smollm2:360m \
  --datasets data/benchmarks/gsm8k.jsonl data/benchmarks/boolq.jsonl \
  --workspace . --repeats 5
venv/bin/python scripts/export_study_report.py data/study/STUDY_FILE.json
```

The current workspace's study summary is `data/study/study-20261115T161203Z.json`, with its review report exported to `dist/study-report.md`. Seeds and files aid reproducibility, but inference can still vary with model/runtime/hardware revisions.
