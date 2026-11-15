# Real-model evaluation protocol

## Research question

Can repeated, risk-stratified evaluations distinguish model changes from ordinary sampling variation, while separating statistical significance from practical impact?

## Current evidence boundary

The software includes functional tests, simulated statistical calibration, and seeded synthetic runs. These demonstrate implementation behavior. They do **not** demonstrate generalizability across local model families or public benchmarks. No real-model research result should be invented or copied from a synthetic run.

A pilot was completed locally on 15 November 2026 using Qwen2.5 0.5B and SmolLM2 360M, 30 GSM8K prompts and 30 BoolQ prompts, five repeats, same-model controls, and cross-family comparisons: six runs and 900 generations. Three comparisons were inconclusive and one met the configured equivalence margin. Full evidence remains in the local workspace; export it with `scripts/export_study_report.py`. This limited pilot does not establish broad generalizability. See MODELS_AND_DATA.md and VALIDATION.md.

## Preregister the study

1. Select at least two installed local model families. Record exact model names, upstream hashes, quantization, inference backend version, hardware, OS, and available memory. Compare model states within families when attributing change to an update; cross-family differences alone do not isolate an update effect.
2. Select at least two appropriately licensed benchmark datasets or application datasets. Record source, license, version/revision, task selection, held-out split, transformations, and content digest. Retain the source data or a reproducible download/conversion script. The bundled functional suite is not a substitute.
3. Define task categories, risk levels, references, and metrics before observing results. Risk margins in the defaults are illustrative: justify task-specific margins with your guide and application context.
4. Use at least the configured prompt/repeat minimum within every category × metric × risk group. More prompts are preferable to padding a small prompt set with many repeats. Record sample-size/power reasoning.
5. Fix generation settings and planned seeds. Use different seeds for independent baseline/candidate sampling. Keep the dataset constant. Document changes to prompts, quantization, model weights, or configuration separately.

## Experimental conditions

- **Same-model control:** same model state and settings, independent seeds. Repeat controls across several seeds to estimate false positive behavior.
- **Candidate comparison:** a defined change, such as quantization or a version update, against the baseline on the identical dataset.
- **Injected-effect software control:** the clearly labeled synthetic stable/regression profiles verify detection under a known perturbation.
- **Secondary baseline:** report the deliberately naive unclustered comparison only as a methodological comparator, separately from the production decision path.

Start Ollama and pull your selected models before running:

```bash
python examples/local_model_study.py \
  --models BASELINE_MODEL CANDIDATE_MODEL \
  --datasets datasets/benchmark-a.jsonl datasets/benchmark-b.jsonl \
  --workspace study-workspace --repeats 5
```

The runner performs an independent same-model control for each dataset, then candidate comparisons. It saves every run and comparison plus `study-results.json`. Re-run with preregistered seeds/conditions as needed; the script currently fixes control/candidate seeds for a reproducible starting protocol.

## Report each condition

Report group sample sizes, repeat counts, score distributions, effect direction and size, tier-specific intervals, raw and Holm-adjusted p-values, noise-floor source, practical margin, verdict, and inference latency. Retain inconclusive and insufficient-data results. Do not select only significant effects.

Summarize agreement/disagreement with known perturbations, empirical false positive behavior in controls, limitations of exact-match/JSON metrics, model runtime costs, and threats to validity. Keep synthetic and real-model tables separate.

## Statistical assumptions and limits

The prompt-level BCa interval describes sampling variation across the evaluated prompt set. Constant prompt differences yield a point interval; it reflects the empirical sample, not certainty about all future outputs. Permutation testing relabels repeated scores within each prompt and assumes their exchangeability under the null. Correlated outputs, reused seeds, or changing runtime conditions can violate this interpretation.

The automatic noise estimate resamples observed baseline repeats. It is conditional on the available outputs and may underestimate unseen variation. Independent repeated same-model runs provide stronger calibration evidence. Holm adjustment controls the test family within each comparison, not the entire set of exploratory comparisons conducted throughout a study.

The framework can establish measurable differences in chosen metrics. It cannot establish general semantic safety, clinical correctness, or deployment fitness from those scores alone.
