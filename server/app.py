from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import os

from scripts.infer import run, _load

class GenRequest(BaseModel):
    prompt: str
    max_new_tokens: int = 200

app = FastAPI(title="ALD-01 Inference API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
def startup_load_model():
    try:
        _load()
    except Exception as e:
        # keep service up but warn
        print("Model load on startup failed:", e)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/generate")
def generate(req: GenRequest):
    if not req.prompt:
        raise HTTPException(status_code=400, detail="prompt is required")
    try:
        text = run(req.prompt, max_new_tokens=req.max_new_tokens)
        return {"text": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
