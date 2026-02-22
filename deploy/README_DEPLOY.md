ALD-01 v1.0.0 — Deploy Guide

Quick options to run ALD-01 inference server locally or in Docker.

Prerequisites
- Merged HF model present at `outputs/ald01-merged` (see USAGE.md)
- Docker (for container option) or Python 3.10+ locally

Local (Python)
1. Install requirements:

```bash
pip install -r requirements.txt
```

2. Run the server (ensure `ALD01_MODEL_PATH` env var points to merged model if not default):

```bash
export ALD01_MODEL_PATH=outputs/ald01-merged
uvicorn server.app:app --host 0.0.0.0 --port 8080 --workers 1
```

Docker
1. Build image:

```bash
docker build -t ald01:1.0 .
```

2. Run container (mount model if large or store outside image):

```bash
docker run --gpus all -v /path/to/merged:/app/outputs/ald01-merged -p 8080:8080 ald01:1.0
```

Notes
- For GPU in Docker, use NVIDIA Container Toolkit and ensure base image & torch wheel match your GPU. If GPU is not available, the server will run on CPU but slower.
- For production use, run multiple workers behind a load balancer and add request batching.
