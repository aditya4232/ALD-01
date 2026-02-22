# GGUF Conversion Guide — ALD-01

## Prerequisites

```bash
# Clone llama.cpp (run once)
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
pip install -r requirements.txt

# Build (Linux/WSL/Colab)
make -j$(nproc)

# Windows: use pre-built binaries from
# https://github.com/ggerganov/llama.cpp/releases
```

---

## Step 1 — Convert HuggingFace model to GGUF (f16)

```bash
python llama.cpp/convert_hf_to_gguf.py outputs/ald01-merged \
    --outfile outputs/ald01-f16.gguf \
    --outtype f16
```

Expected output size: ~2.2 GB

---

## Step 2 — Quantize to Q4_K_M

```bash
./llama.cpp/llama-quantize \
    outputs/ald01-f16.gguf \
    outputs/ald01-Q4_K_M.gguf \
    Q4_K_M
```

Expected output size: ~700 MB

---

## Quantization Types Reference

| Type     | Size    | Quality       | Use case               |
|----------|---------|---------------|------------------------|
| Q8_0     | ~1.1 GB | Best          | High VRAM / accuracy   |
| Q4_K_M   | ~700 MB | Good balance  | Recommended default    |
| Q4_0     | ~650 MB | Slightly lower | Ultra-low RAM devices |
| Q2_K     | ~450 MB | Lower         | Extreme low RAM only   |

---

## Step 3 — Test GGUF locally

```bash
./llama.cpp/llama-cli \
    -m outputs/ald01-Q4_K_M.gguf \
    -p "### Instruction:\nExplain AI in Hindi.\n\n### Response:\n" \
    -n 200
```

---

## Google Colab (combined Steps 1+2)

```python
!git clone https://github.com/ggerganov/llama.cpp
!pip install -q -r llama.cpp/requirements.txt
!make -C llama.cpp -j2

!python llama.cpp/convert_hf_to_gguf.py /content/ald01-merged \
    --outfile /content/ald01-f16.gguf --outtype f16

!./llama.cpp/llama-quantize \
    /content/ald01-f16.gguf \
    /content/ald01-Q4_K_M.gguf \
    Q4_K_M

# Copy to Drive
from google.colab import drive
drive.mount('/content/drive')
!cp /content/ald01-Q4_K_M.gguf "/content/drive/MyDrive/ALD-01/"
```
