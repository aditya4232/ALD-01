Model: ALD-01 v1.0.0

Summary
-------
ALD-01 v1.0.0 is a small bilingual instruction-tuned language model (English + Hindi) based on TinyLlama (1.1B) using QLoRA training and a LoRA adapter merged to produce a full HF model.

Contents
--------
- `outputs/ald01-merged/` — merged HuggingFace model (config.json, model.safetensors, tokenizer files)
- Training artifacts (adapter) are in `outputs/ald01-lora/` when produced by training.

Intended Use
------------
- Development, prototyping, and low-cost inference experiments for bilingual office/coding prompts.
- Not recommended for production or sensitive domains without further data, validation, and safety review.

Limitations & Risks
-------------------
- v1.0.0 was trained on a small demo dataset; outputs may be low-quality and unreliable.
- `trust_remote_code=True` was used when loading the base model; only use models from trusted sources.

How to reproduce
----------------
Follow `USAGE.md` to install dependencies, run training (optional), merge the LoRA adapter, and perform inference.

License & Attribution
---------------------
- Check licensing of the base model and any third-party data used for training before redistribution.

Contact
-------
For help, provide logs (`training_run.log`, `merge_run.log`, `eval_run.log`) and a short description of the issue.