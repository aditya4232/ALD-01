# ALD-01 — Indian Bilingual LLM

Lightweight, instruction-tuned LLM based on **TinyLlama 1.1B** with QLoRA fine-tuning.  
Supports English + Hindi (Hinglish) for office work, coding, and reasoning.

---

## Project Structure

```
ALD-01-LLM/
+-- training/
¦   +-- train.py              # QLoRA fine-tuning script
+-- data/
¦   +-- ald01_dataset.json    # 50 instruction fine-tuning samples
+-- scripts/
¦   +-- merge_lora.py         # Merge LoRA adapter into base model
¦   +-- evaluate.py           # Evaluation on 4 test cases
¦   +-- convert_gguf.md       # GGUF conversion guide (llama.cpp)
+-- notebooks/
¦   +-- ALD01_Colab.ipynb     # End-to-end Colab notebook
+-- ollama/
¦   +-- Modelfile             # Ollama deployment config
+-- outputs/                  # Generated during training (gitignored)
    +-- ald01-lora/           # LoRA adapter weights
    +-- ald01-merged/         # Merged HuggingFace model
    +-- ald01-Q4_K_M.gguf    # Quantized GGUF model
```

---

## Quick Start

### 1. Install dependencies
```bash
pip install torch transformers datasets peft bitsandbytes trl accelerate sentencepiece
```

### 2. Fine-tune (local / Colab)
```bash
python training/train.py
```

### 3. Merge LoRA adapter
```bash
python scripts/merge_lora.py
```

### 4. Convert to GGUF
See scripts/convert_gguf.md

### 5. Run with Ollama
```bash
cd ollama
ollama create ald01 -f Modelfile
ollama run ald01
```

---

## Model Config

| Parameter     | Value                               |
|---------------|-------------------------------------|
| Base Model    | TinyLlama/TinyLlama-1.1B-Chat-v1.0  |
| Quantization  | 4-bit NF4 (QLoRA)                   |
| LoRA r        | 16                                  |
| LoRA alpha    | 32                                  |
| Max seq len   | 1024                                |
| Languages     | English, Hindi, Hinglish            |

---

## Execution Flow

`Install ? Dataset ? Train ? Merge ? Quantize (GGUF) ? Deploy (Ollama)`
