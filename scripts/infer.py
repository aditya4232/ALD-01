from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

MODEL_PATH = "outputs/ald01-merged"

def run(prompt, max_new_tokens=200):
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
    model = AutoModelForCausalLM.from_pretrained(MODEL_PATH, torch_dtype=torch.float16, device_map="auto")
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=max_new_tokens)
    return tokenizer.decode(out[0], skip_special_tokens=True)

if __name__ == "__main__":
    p = "Write a short Hinglish office email asking for a meeting tomorrow."
    print(run(p))
