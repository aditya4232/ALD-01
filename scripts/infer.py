import os
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

MODEL_PATH = os.environ.get("ALD01_MODEL_PATH", "outputs/ald01-merged")

# Load model/tokenizer once at import to avoid repeated heavy I/O
_MODEL = None
_TOKENIZER = None
_DEVICE = None

def _load():
    global _MODEL, _TOKENIZER, _DEVICE
    if _MODEL is not None and _TOKENIZER is not None:
        return
    if not os.path.isdir(MODEL_PATH):
        raise FileNotFoundError(f"Model directory not found: {MODEL_PATH}")
    _TOKENIZER = AutoTokenizer.from_pretrained(MODEL_PATH)
    # load to device automatically (use CPU if no GPU)
    cuda = torch.cuda.is_available()
    dtype = torch.float16 if cuda else torch.float32
    _MODEL = AutoModelForCausalLM.from_pretrained(MODEL_PATH, torch_dtype=dtype, device_map="auto")
    _DEVICE = next(_MODEL.parameters()).device

def run(prompt, max_new_tokens=200):
    _load()
    inputs = _TOKENIZER(prompt, return_tensors="pt").to(_DEVICE)
    with torch.no_grad():
        out = _MODEL.generate(**inputs, max_new_tokens=max_new_tokens)
    return _TOKENIZER.decode(out[0], skip_special_tokens=True)

if __name__ == "__main__":
    try:
        prompt = "Write a short Hinglish office email asking for a meeting tomorrow."
        print(run(prompt))
    except Exception as e:
        print("Inference failed:", e)
