import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

BASE_MODEL   = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
LORA_ADAPTER = "outputs/ald01-lora"
MERGED_DIR   = "outputs/ald01-merged"

print("Loading base model...")
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    torch_dtype   = torch.float16,
    device_map    = "cpu",
    trust_remote_code = True,
)

print("Loading LoRA adapter...")
model = PeftModel.from_pretrained(model, LORA_ADAPTER)

print("Merging weights...")
model = model.merge_and_unload()

print(f"Saving merged model to: {MERGED_DIR}")
model.save_pretrained(MERGED_DIR, safe_serialization=True)
tokenizer.save_pretrained(MERGED_DIR)

print("Done. Merged model ready for GGUF conversion.")
