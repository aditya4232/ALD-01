ALD-01 — Quick Usage

Version: v1.0.0 (ALD-01)

This repository contains ALD-01 LLM (v1.0.0) — a small instruction-tuned bilingual model (English/Hindi) produced by QLoRA + LoRA adapter merge. The merged HF model is available after running the merge step at `outputs/ald01-merged`.

- Pull latest repo:

  ```bash
  git pull origin main
  ```

- Install (Colab):

  ```bash
  pip install -r requirements.txt
  # If you need a specific PyTorch wheel, follow https://pytorch.org/get-started/locally/
  ```

- Verify GPU in Colab:

  ```bash
  !nvidia-smi
  python -c "import torch; print(torch.cuda.is_available(), torch.cuda.device_count(), torch.cuda.is_bf16_supported())"
  ```

- Train (QLoRA) — run in the repo root:

  ```bash
  python training/train.py 2>&1 | tee training_run.log
  ```

  - If you get OOM, reduce `per_device_train_batch_size` or increase `gradient_accumulation_steps` in `training/train.py`.

- After training, adapter is saved to `outputs/ald01-lora`.

- Merge LoRA adapter to a full HF model:

  ```bash
  python scripts/merge_lora.py 2>&1 | tee merge_run.log
  ```

  - Merged model saved to `outputs/ald01-merged`.

- Quick local inference (Python):

  ```python
  from transformers import AutoTokenizer, AutoModelForCausalLM
  import torch

  model_path = "outputs/ald01-merged"
  tokenizer = AutoTokenizer.from_pretrained(model_path)
  model = AutoModelForCausalLM.from_pretrained(model_path, torch_dtype=torch.float16, device_map="auto")

  prompt = "Write a short, polite office email in Hinglish asking for a meeting tomorrow."
  inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
  out = model.generate(**inputs, max_new_tokens=200)
  print(tokenizer.decode(out[0], skip_special_tokens=True))
  ```

- Convert to GGUF (high-level):
  1. Use the merged HF model in `outputs/ald01-merged`.
  2. Follow `scripts/convert_gguf.md` for llama.cpp conversion and quantization steps.

Security notes:
- `trust_remote_code=True` is used in scripts — only use trusted model sources and pin model versions.
- Keep logs (`training_run.log`, `merge_run.log`, `eval_run.log`) and back them up to Drive.

Contact:
- If you want, I can also create a Colab inference notebook or push these docs to the repo for you.
