import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

MODEL_PATH = "outputs/ald01-merged"   # or adapter path for quick test

TEST_CASES = [
    {
        "name": "Hindi Response",
        "prompt": "### Instruction:\nMujhe machine learning ko simple Hindi mein explain karo.\n\n### Response:\n",
    },
    {
        "name": "Office Email",
        "prompt": "### Instruction:\nWrite a professional email to inform a client about a project delay of 1 week due to server migration.\n\n### Response:\n",
    },
    {
        "name": "React Component",
        "prompt": "### Instruction:\nWrite a minimal React functional component that displays a loading spinner.\n\n### Response:\n",
    },
    {
        "name": "Logical Reasoning",
        "prompt": "### Instruction:\nIf all A are B, and all B are C, are all A necessarily C? Explain step by step.\n\n### Response:\n",
    },
]

def load_pipeline(model_path: str):
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map  = "auto",
    )
    return pipeline(
        "text-generation",
        model     = model,
        tokenizer = tokenizer,
        max_new_tokens       = 256,
        do_sample            = True,
        temperature          = 0.7,
        repetition_penalty   = 1.1,
        pad_token_id         = tokenizer.eos_token_id,
    )

def run_evaluation(pipe):
    print("=" * 60)
    print("ALD-01 Evaluation")
    print("=" * 60)
    for i, tc in enumerate(TEST_CASES, 1):
        print(f"\n[{i}/{len(TEST_CASES)}] {tc['name']}")
        print("-" * 40)
        result = pipe(tc["prompt"])[0]["generated_text"]
        response = result[len(tc["prompt"]):].strip()
        print(response)
        print()

if __name__ == "__main__":
    pipe = load_pipeline(MODEL_PATH)
    run_evaluation(pipe)
