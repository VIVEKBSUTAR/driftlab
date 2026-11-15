# Selected model and dataset configuration

## Practical first study

Use **Qwen2.5 0.5B Instruct** and **SmolLM2 360M Instruct** through Ollama. Both are small, openly available instruction models from different families with Apache-2.0 upstream model cards. They are suitable for inexpensive local pipeline validation on the available Apple M4. They are deliberately modest models: this study cannot establish state-of-the-art accuracy or general performance across the LLM ecosystem.

- [Qwen official model card](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct), [Ollama model](https://ollama.com/library/qwen2.5:0.5b).
- [SmolLM2 official model card](https://huggingface.co/HuggingFaceTB/SmolLM2-360M-Instruct), [Ollama model](https://ollama.com/library/smollm2:360m).

Use the exact installed tags and full recorded digests. Tags can change; the model snapshot, run manifest, and study context record what was actually used.

## Dataset samples and attribution

| Dataset | Task | Source split | Prepared sample | License |
| --- | --- | --- | --- | --- |
| GSM8K | Grade-school mathematical word problems | Test, 1,319 examples | 30 distinct prompts | MIT, OpenAI 2021 |
| BoolQ | Yes/no reading comprehension using a supplied passage | Development/validation, 3,270 examples | 30 distinct prompts | CC BY-SA 3.0 |

Sources: [OpenAI GSM8K repository](https://github.com/openai/grade-school-math), [Google BoolQ repository](https://github.com/google-research-datasets/boolean-questions), [Google BoolQ mirror](https://huggingface.co/datasets/google/boolq).

GSM8K is pinned to commit `3101c7d5072418e28b9008a6636bde82a006892c`. BoolQ's original public bucket returned HTTP 403 during preparation, so the script falls back to Google's Hugging Face mirror and records the revision and canonical downloaded-row hash. The prepared files record exact sample indices, seed 42, source/prepared SHA-256, original split, transformations, and license in adjacent `.source.json` files. Do not apply the software's MIT license to BoolQ-derived data; retain its source attribution and CC BY-SA terms when sharing it.

The transformation adds output-format instructions and extracts the reference answer; no model outputs are used to select examples. Risk is set to medium to demonstrate policy-based evaluation, not to assert the tasks belong to a sensitive deployment domain.

## Answer scoring

The `answer_match` metric reads each task's `output_spec.answer_type`:

- `numeric`: extract the final number, preferring the text after `####`; remove commas and compare using Decimal. This accepts ordinary number formatting and ignores the explanation's correctness.
- `boolean`: interpret the first yes/no/true/false word and compare it with the reference. Other text formats fail extraction.
- Unspecified: use normalized exact match.

Generation uses temperature 0.7, maximum 128 tokens, and five repeats per prompt. The short token limit keeps the study practical but may truncate mathematical explanations. This affects measured answer accuracy and is explicitly part of the evaluated configuration.

## Reproduce

```bash
venv/bin/python scripts/prepare_benchmarks.py
ollama pull qwen2.5:0.5b
ollama pull smollm2:360m
venv/bin/python examples/local_model_study.py \
  --models qwen2.5:0.5b smollm2:360m \
  --datasets data/benchmarks/gsm8k.jsonl data/benchmarks/boolq.jsonl \
  --workspace . --repeats 5
```

A project-local portable Ollama runtime can be started with `scripts/run_local_ollama.sh` after extracting an official macOS release into `.tools/ollama/`. It uses `.runtime/models` and disables cloud inference. Neither model weights nor the runtime are included in the Python package or committed to Git.

Each dataset has a Qwen baseline (seed 42), an independent Qwen control (seed 1042), and a SmolLM2 candidate (seed 2042). All use the same prepared prompts and metric. Cross-family differences demonstrate framework generality but cannot isolate an update mechanism such as quantization. Within-family version/quantization comparisons are the next research extension.
