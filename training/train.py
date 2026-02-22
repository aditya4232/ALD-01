import torch
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer

# ── Config ──────────────────────────────────────────────────────────────────
BASE_MODEL   = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
DATASET_PATH = "data/ald01_dataset.json"
OUTPUT_DIR   = "outputs/ald01-lora"
MAX_SEQ_LEN  = 1024

LORA_R       = 16
LORA_ALPHA   = 32
LORA_DROPOUT = 0.05
TARGET_MODULES = ["q_proj", "v_proj", "k_proj", "o_proj",
                  "gate_proj", "up_proj", "down_proj"]

TRAIN_ARGS = dict(
    num_train_epochs        = 3,
    per_device_train_batch_size = 2,
    gradient_accumulation_steps = 4,
    learning_rate           = 2e-4,
    lr_scheduler_type       = "cosine",
    warmup_ratio            = 0.05,
    logging_steps           = 10,
    save_steps              = 100,
    save_total_limit        = 2,
    fp16                    = not torch.cuda.is_bf16_supported(),
    bf16                    = torch.cuda.is_bf16_supported(),
    gradient_checkpointing  = True,
    optim                   = "paged_adamw_8bit",
    report_to               = "none",
)

# ── BitsAndBytes ─────────────────────────────────────────────────────────────
bnb_config = BitsAndBytesConfig(
    load_in_4bit              = True,
    bnb_4bit_quant_type       = "nf4",
    bnb_4bit_compute_dtype    = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
    bnb_4bit_use_double_quant = True,
)

# ── Model & Tokenizer ────────────────────────────────────────────────────────
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
tokenizer.pad_token = tokenizer.eos_token
tokenizer.padding_side = "right"

model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    quantization_config = bnb_config,
    device_map          = "auto",
    trust_remote_code   = True,
)
model = prepare_model_for_kbit_training(model)

# ── LoRA ─────────────────────────────────────────────────────────────────────
lora_config = LoraConfig(
    r              = LORA_R,
    lora_alpha     = LORA_ALPHA,
    lora_dropout   = LORA_DROPOUT,
    target_modules = TARGET_MODULES,
    bias           = "none",
    task_type      = "CAUSAL_LM",
)
model = get_peft_model(model, lora_config)
model.print_trainable_parameters()

# ── Dataset ──────────────────────────────────────────────────────────────────
dataset = load_dataset("json", data_files=DATASET_PATH, split="train")

def format_prompt(sample):
    instruction = sample["instruction"]
    inp         = sample.get("input", "")
    output      = sample["output"]
    if inp:
        text = f"### Instruction:\n{instruction}\n\n### Input:\n{inp}\n\n### Response:\n{output}"
    else:
        text = f"### Instruction:\n{instruction}\n\n### Response:\n{output}"
    return {"text": text}

dataset = dataset.map(format_prompt)

# ── Trainer ──────────────────────────────────────────────────────────────────
training_arguments = TrainingArguments(output_dir=OUTPUT_DIR, **TRAIN_ARGS)

trainer = SFTTrainer(
    model           = model,
    train_dataset   = dataset,
    tokenizer       = tokenizer,
    args            = training_arguments,
    dataset_text_field = "text",
    max_seq_length  = MAX_SEQ_LEN,
    packing         = False,
)

trainer.train()
# Save only the LoRA adapter (PEFT) — not the full merged model
model.save_pretrained(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)
print(f"LoRA adapter saved to: {OUTPUT_DIR}")
