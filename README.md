# ALD-01 — Advanced Local Desktop Intelligence

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/license-MIT-green?style=for-the-badge" />
  <img src="https://img.shields.io/badge/status-beta-orange?style=for-the-badge" />
  <img src="https://img.shields.io/badge/agents-5-purple?style=for-the-badge" />
  <img src="https://img.shields.io/badge/providers-10%2B-cyan?style=for-the-badge" />
</p>

**ALD-01** is your personal AI agent system that runs locally on your desktop. It combines multiple AI providers, specialized agents, a reasoning engine, and full device access into one powerful, open-source package.

Think of it as **your own local, open-source AI assistant** with the power of commercial tools — but free, private, and fully under your control.

---

## ✨ Features

### 🤖 Multi-Agent System

- **5 Specialized Agents**: Code Generation, Debugging, Code Review, Security Analysis, and General Assistant
- **Automatic Agent Routing**: Queries are intelligently routed to the best agent
- **Configurable Brain Power**: 10 levels from basic Q&A to full AGI-like autonomy

### 🔌 10+ AI Provider Support (Free)

| Provider       | Model           | Free Tier      |
| -------------- | --------------- | -------------- |
| Groq           | Llama 3.3 70B   | ✅ Generous    |
| Cerebras       | Llama 3.3 70B   | ✅             |
| OpenRouter     | Various         | ✅             |
| Together AI    | Mixtral         | ✅             |
| GitHub Copilot | GPT-4.1         | ✅ Pro users   |
| Google Gemini  | Gemini 2.0      | ✅             |
| SambaNova      | Llama 3.1       | ✅             |
| Novita AI      | Llama 3         | ✅             |
| Hyperbolic     | Deepseek R1     | ✅             |
| Ollama         | Any local model | ✅ Fully local |

### 🧠 Advanced Reasoning

- **Chain-of-Thought**: Step-by-step logical reasoning
- **Tree-of-Thought**: Multi-branch problem exploration
- **Reflexion**: Self-correcting iterative refinement
- **Problem Decomposition**: Complex task breakdown
- Depth scales automatically with brain power level

### 🖥️ Professional Dashboard

- **Dark, modern UI** with glassmorphism aesthetics
- **Real-time Activity Visualizer** via WebSocket
- **Chat Interface** with streaming responses
- **Sandbox Code Editor** with Python execution and export
- **File Browser** for full filesystem navigation
- **Terminal** for command execution
- **System Monitor** with process listing
- **Doctor Diagnostics** with 12+ health checks
- **Provider Management** with one-click testing

### 🔧 Full Device Access

- **Filesystem**: Read, write, search, delete, move files
- **Terminal**: Execute shell commands
- **Code Sandbox**: Run Python in a controlled environment
- **System Info**: CPU, RAM, disk, GPU detection
- **Process Management**: List running processes
- **Clipboard**: Read and write clipboard content
- **HTTP Requests**: Make web requests

### 🔊 Voice / Text-to-Speech

- **Edge TTS**: Free Microsoft Neural voices (high quality)
- **pyttsx3**: Offline TTS fallback
- **System TTS**: OS-native speech (Windows, macOS, Linux)
- 50+ neural voice options

### 📱 Remote Access

- **Telegram Bot**: Control ALD-01 from your phone
- Ask questions, check status, change settings remotely

### 💾 Persistent Memory

- **SQLite-backed** conversation storage
- **Semantic memory**: Facts, preferences, patterns
- **Decision logs**: Track AI reasoning
- **User profile**: Personalization

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- At least one AI provider (or Ollama for fully local)

### Installation

```bash
# Clone the repo
git clone https://github.com/ald-01/ald-01.git
cd ald-01

# Install (editable mode for development)
pip install -e .

# Or install with voice support
pip install -e ".[voice]"
```

### First Run

```bash
# Run the setup wizard
ald-01 setup

# Or jump straight in
ald-01 chat
```

### Set Up a Provider

```bash
# Free option 1: Groq (fastest, generous free tier)
export GROQ_API_KEY=gsk_your_key_here  # Get from console.groq.com

# Free option 2: Cerebras
export CEREBRAS_API_KEY=your_key_here  # Get from cloud.cerebras.ai

# Free option 3: Use Ollama (fully local, no API key needed)
# Install from ollama.ai, then: ollama pull llama3.2

# Verify providers
ald-01 provider list
```

---

## 📖 Usage

### CLI Commands

```bash
# Interactive chat
ald-01 chat

# Quick question
ald-01 ask "How do I reverse a linked list in Python?"

# Chat with specific agent
ald-01 chat --agent security

# Chat with voice output
ald-01 chat --voice

# Launch web dashboard
ald-01 dashboard

# System diagnostics
ald-01 doctor

# System status
ald-01 status

# Provider management
ald-01 provider list          # Show all providers
ald-01 provider free          # Show free provider options
ald-01 provider add groq      # Add a provider

# Configuration
ald-01 config show            # Show config
ald-01 config set brain_power 7  # Set brain power
ald-01 config reset           # Reset to defaults

# Voice
ald-01 voice test             # Test TTS
ald-01 voice voices           # List available voices
```

### In-Chat Commands

When in interactive chat mode:

```
/exit    — Exit chat
/clear   — Clear conversation
/agent   — Switch agent (code_gen, debug, review, security, general)
/voice   — Toggle voice on/off
/status  — Show system status
```

### Python API

```python
import asyncio
from ald01.core.orchestrator import get_orchestrator

async def main():
    orch = get_orchestrator()
    await orch.initialize()

    # Simple query
    response = await orch.process_query("Explain decorators in Python")
    print(response.content)

    # Stream response
    async for chunk in orch.stream_query("Write a sorting algorithm"):
        print(chunk, end="")

    # Use specific agent
    response = await orch.process_query(
        "Review this code for security issues",
        agent_name="security"
    )

    await orch.shutdown()

asyncio.run(main())
```

---

## 🏗️ Architecture

```
ald-01/
├── src/ald01/
│   ├── __init__.py          # Package init, directory setup
│   ├── __main__.py          # python -m ald01
│   ├── cli.py               # Click CLI with all commands
│   ├── config.py            # YAML config with brain power presets
│   │
│   ├── core/                # Core systems
│   │   ├── events.py        # Async pub-sub event bus
│   │   ├── memory.py        # SQLite persistent memory
│   │   ├── tools.py         # Tool executor (filesystem, terminal, etc.)
│   │   ├── orchestrator.py  # Central coordinator
│   │   └── reasoning.py     # Multi-strategy reasoning engine
│   │
│   ├── agents/              # Specialized AI agents
│   │   ├── base.py          # Base agent class
│   │   ├── codegen.py       # Code generation agent
│   │   ├── debug.py         # Debugging agent
│   │   ├── review.py        # Code review agent
│   │   ├── security.py      # Security analysis agent
│   │   └── general.py       # General purpose agent
│   │
│   ├── providers/           # AI model providers
│   │   ├── base.py          # Abstract provider interface
│   │   ├── openai_compat.py # Universal OpenAI-compatible provider
│   │   ├── ollama.py        # Local Ollama provider
│   │   └── manager.py       # Provider routing & failover
│   │
│   ├── dashboard/           # Web dashboard
│   │   ├── server.py        # FastAPI + WebSocket server
│   │   └── static/
│   │       └── index.html   # Single-page dashboard UI
│   │
│   ├── services/            # Optional services
│   │   └── voice.py         # Text-to-Speech engine
│   │
│   ├── doctor/              # System diagnostics
│   │   └── diagnostics.py   # 12+ health checks
│   │
│   ├── visualization/       # Thinking visualizer
│   │   └── thinking.py      # Rich terminal visualization
│   │
│   ├── telegram/            # Remote access
│   │   └── bot.py           # Telegram bot
│   │
│   ├── onboarding/          # First-time setup
│   │   └── wizard.py        # Interactive wizard
│   │
│   └── utils/               # Utilities
│       └── hardware.py      # Hardware detection & GPU
│
├── plans/                   # Project planning documents
├── pyproject.toml           # Package configuration
├── requirements.txt         # Dependencies
└── README.md                # This file
```

---

## ⚙️ Configuration

Configuration is stored in `~/.ald01/config.yaml`. Key settings:

```yaml
brain_power: 5 # 1-10, controls reasoning depth

providers:
  groq:
    enabled: true
    priority: 1 # Lower = higher priority
  ollama:
    enabled: true
    host: http://localhost:11434

dashboard:
  host: 127.0.0.1
  port: 7860
  auto_open: true

voice:
  enabled: false

tools:
  terminal:
    enabled: false # Enable shell command execution
  code_execute:
    enabled: false # Enable Python sandbox

telegram:
  token: "" # Telegram bot token
  allowed_users: [] # List of authorized user IDs
```

---

## 🧠 Brain Power Levels

| Level | Name     | Reasoning Depth | Autonomous | Use Case                     |
| ----- | -------- | --------------- | ---------- | ---------------------------- |
| 1     | Basic    | 1               | No         | Simple Q&A                   |
| 2     | Simple   | 2               | No         | Answers with some reasoning  |
| 3     | Moderate | 3               | No         | Step-by-step explanations    |
| 4     | Standard | 4               | No         | Multi-step problem solving   |
| 5     | Advanced | 5               | Limited    | Complex analysis             |
| 6     | Deep     | 6               | Limited    | Multi-perspective evaluation |
| 7     | Expert   | 7               | Yes        | Expert-level reasoning       |
| 8     | Master   | 8               | Yes        | Deep research & synthesis    |
| 9     | Genius   | 9               | Yes        | Multi-strategy reasoning     |
| 10    | AGI      | 10              | Yes        | Full autonomous reasoning    |

---

## 🩺 Doctor Diagnostics

Run `ald-01 doctor` to check:

- ✅ Python version compatibility
- ✅ Required and optional dependencies
- ✅ Config file validity
- ✅ Data directory permissions
- ✅ Memory database health
- ✅ Dashboard port availability
- ✅ System resources (RAM, disk)
- ✅ Internet connectivity
- ✅ Ollama availability
- ✅ Provider connections
- ✅ Free API key configuration
- ✅ Voice/TTS engine availability

---

## 🔒 Privacy & Security

- **Fully local**: Can run 100% offline with Ollama
- **No telemetry**: No data sent without your consent
- **API keys**: Stored as environment variables, never in code
- **Tool access**: Configurable — enable only what you need
- **Sandbox**: Code execution runs in isolated subprocess
- **Open source**: Full code transparency

---

## 📦 Dependencies

### Required

- `click` — CLI framework
- `rich` — Terminal UI
- `httpx` — HTTP client
- `fastapi` — Web dashboard
- `uvicorn` — ASGI server
- `pyyaml` — Config parser
- `psutil` — System info
- `python-dotenv` — Environment variables

### Optional

- `edge-tts` — Microsoft Neural TTS (voice)
- `pyttsx3` — Offline TTS (voice)

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest`
5. Submit a pull request

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<p align="center">
  <strong>ALD-01 — Your Desktop, Your Intelligence, Your Control.</strong>
</p>
