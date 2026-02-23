<p align="center">
  <img src="https://readme-typing-svg.herokuapp.com?font=Fira+Code&size=40&duration=3000&pause=1000&color=00D4FF&center=true&vCenter=true&width=600&lines=ALD-01;Advanced+Local+Desktop+Intelligence;Your+Desktop.+Your+AI.+Your+Control." alt="ALD-01 Typing" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/node-16%2B-339933?style=for-the-badge&logo=nodedotjs&logoColor=white" alt="Node" />
  <img src="https://img.shields.io/badge/license-MIT-00C853?style=for-the-badge" alt="License" />
  <img src="https://img.shields.io/badge/version-1.0.0-FF6D00?style=for-the-badge" alt="Version" />
</p>

<p align="center">
  <img src="https://img.shields.io/npm/v/ald-01?style=flat-square&logo=npm&label=npm" alt="npm" />
  <img src="https://img.shields.io/pypi/v/ald-01?style=flat-square&logo=pypi&label=pypi" alt="pypi" />
  <a href="https://github.com/aditya4232/ALD-01/stargazers"><img src="https://img.shields.io/github/stars/aditya4232/ALD-01?style=flat-square&logo=github" alt="Stars" /></a>
  <a href="https://github.com/aditya4232/ALD-01/issues"><img src="https://img.shields.io/github/issues/aditya4232/ALD-01?style=flat-square&logo=github&color=yellow" alt="Issues" /></a>
  <a href="https://github.com/aditya4232/ALD-01/fork"><img src="https://img.shields.io/github/forks/aditya4232/ALD-01?style=flat-square&logo=github" alt="Forks" /></a>
</p>

---

**ALD-01** is a fully open-source, privacy-first AI agent system that runs **locally on your desktop**. It combines 10+ free AI providers, 5 specialized agents, advanced reasoning strategies, a professional web dashboard, and full device access — all in a single install.

> Think of it as **your own local, open-source AI assistant** — with the power of commercial tools, but free, private, and fully under your control.

---

## <img src="https://img.shields.io/badge/-Quick%20Start-0078D4?style=flat-square&logo=rocket&logoColor=white" height="25" alt="Quick Start" />

### Prerequisites

- **Python 3.10+** — [python.org/downloads](https://www.python.org/downloads/)
- **Node.js 16+** *(optional, for npm install)* — [nodejs.org](https://nodejs.org/)

### Install via npm (recommended)

```bash
npm install -g ald-01
```

> Installs the `ald-01` global command. On first run, it auto-detects Python and installs all Python dependencies for you.

### Install via pip

```bash
pip install ald-01
```

### Install from Source

```bash
git clone https://github.com/aditya4232/ALD-01.git
cd ALD-01

# Editable install (dev)
pip install -e .

# With voice support
pip install -e ".[voice]"

# With dev tools (pytest, ruff, black)
pip install -e ".[dev]"
```

### Verify

```bash
ald-01 --help
```

### First Run

```bash
ald-01 setup          # Interactive setup wizard
ald-01 chat           # Start chatting
ald-01 dashboard      # Launch web UI
```

### Set Up a Free Provider

```bash
# Groq — fastest, generous free tier (console.groq.com)
export GROQ_API_KEY=gsk_your_key_here          # Linux / Mac
set GROQ_API_KEY=gsk_your_key_here             # Windows CMD
$env:GROQ_API_KEY="gsk_your_key_here"          # PowerShell

# Cerebras (cloud.cerebras.ai)
export CEREBRAS_API_KEY=your_key_here

# Fully local — no key needed (ollama.ai)
ollama pull llama3.2

# Check what's available
ald-01 provider list
```

---

## <img src="https://img.shields.io/badge/-Features-7C4DFF?style=flat-square&logo=sparkles&logoColor=white" height="25" alt="Features" />

### <img src="https://img.shields.io/badge/-Multi--Agent%20System-blue?style=flat-square&logo=robot&logoColor=white" height="20" alt="Agents" />

| Agent | Specialty | Example |
|:------|:----------|:--------|
| **Code Gen** | Code generation and scaffolding | *"Write a REST API in FastAPI"* |
| **Debug** | Debugging and error resolution | *"Fix this TypeError in my code"* |
| **Review** | Code review and best practices | *"Review this function for issues"* |
| **Security** | Security analysis and hardening | *"Check this endpoint for vulns"* |
| **General** | General Q&A and reasoning | *"Explain decorators in Python"* |

- Automatic agent routing — queries go to the best agent
- 10 brain power levels — from basic Q&A to full autonomous reasoning

### <img src="https://img.shields.io/badge/-10%2B%20AI%20Providers-00BCD4?style=flat-square&logo=openai&logoColor=white" height="20" alt="Providers" />

All providers below offer **free tiers** — no credit card required.

| Provider | Model | Notes |
|:---------|:------|:------|
| **Groq** | Llama 3.3 70B | Ultra-fast inference, generous free tier |
| **Cerebras** | Llama 3.3 70B | High throughput |
| **OpenRouter** | Various | Aggregator, many free models |
| **Together AI** | Mixtral | Free tier available |
| **GitHub Copilot** | GPT-4.1 | Free for Pro users |
| **Google Gemini** | Gemini 2.0 | Google's latest |
| **SambaNova** | Llama 3.1 | Free tier |
| **Novita AI** | Llama 3 | Free tier |
| **Hyperbolic** | Deepseek R1 | Free tier |
| **Ollama** | Any local model | 100% offline, no API key |

Built-in **automatic failover** — if one provider drops, the next one picks up.

### <img src="https://img.shields.io/badge/-Advanced%20Reasoning-FF6D00?style=flat-square&logo=brain&logoColor=white" height="20" alt="Reasoning" />

- **Chain-of-Thought** — step-by-step logical reasoning
- **Tree-of-Thought** — multi-branch problem exploration
- **Reflexion** — self-correcting iterative refinement
- **Problem Decomposition** — complex task breakdown into subtasks
- Depth scales automatically with brain power level (1–10)

### <img src="https://img.shields.io/badge/-Web%20Dashboard-E91E63?style=flat-square&logo=googlechrome&logoColor=white" height="20" alt="Dashboard" />

- Glassmorphism dark UI with modern aesthetics
- Real-time activity visualizer via WebSocket
- Chat interface with streaming responses
- Sandbox code editor with Python execution and export
- File browser for full filesystem navigation
- Terminal for direct command execution
- System monitor with live process listing
- Doctor diagnostics with 12+ health checks
- Provider management with one-click testing

### <img src="https://img.shields.io/badge/-Device%20Access%20(40%2B%20Modules)-4CAF50?style=flat-square&logo=chip&logoColor=white" height="20" alt="Modules" />

| Category | Capabilities |
|:---------|:-------------|
| **Filesystem** | Read, write, search, delete, move files |
| **Terminal** | Execute shell commands |
| **Code Sandbox** | Run Python in isolated subprocess |
| **System Info** | CPU, RAM, disk, GPU detection |
| **Process Mgmt** | List and manage running processes |
| **Clipboard** | Read and write clipboard |
| **HTTP** | Make web requests |
| **File Watcher** | Monitor files for real-time changes |
| **Backup** | Create and restore backups |
| **Analytics** | Usage analytics and insights |
| **Scheduler** | Schedule recurring tasks |
| **Export** | Export data (JSON, CSV, etc.) |
| **Webhooks** | Event-driven webhook system |
| **Code Analyzer** | Static code analysis |
| **API Gateway** | Built-in gateway |
| **Sessions** | Multi-session management |
| **Templates** | Jinja2-powered templating |
| **Plugins** | Extensible plugin architecture |
| **Themes** | Customizable UI themes |
| **i18n** | Multi-language support |

### <img src="https://img.shields.io/badge/-Voice%20%2F%20TTS-9C27B0?style=flat-square&logo=speakerdeck&logoColor=white" height="20" alt="Voice" />

- **Edge TTS** — free Microsoft Neural voices (50+ voices, high quality)
- **pyttsx3** — offline TTS fallback
- **System TTS** — OS-native speech (Windows, macOS, Linux)

### <img src="https://img.shields.io/badge/-Remote%20Access-009688?style=flat-square&logo=telegram&logoColor=white" height="20" alt="Telegram" />

- **Telegram Bot** — control ALD-01 from your phone
- Ask questions, check status, change settings remotely

### <img src="https://img.shields.io/badge/-Persistent%20Memory-607D8B?style=flat-square&logo=databricks&logoColor=white" height="20" alt="Memory" />

- **SQLite-backed** conversation and knowledge storage
- **Semantic memory** — facts, preferences, patterns
- **Decision logs** — track AI reasoning over time
- **User profile** — personalized experience
- **Context manager** — intelligent conversation context

---

## <img src="https://img.shields.io/badge/-Usage-2196F3?style=flat-square&logo=windowsterminal&logoColor=white" height="25" alt="Usage" />

### CLI Commands

```bash
# Chat
ald-01 chat                         # Interactive chat
ald-01 chat --agent security        # Specific agent
ald-01 chat --voice                 # With voice output
ald-01 chat --stream                # Stream responses

# Quick question
ald-01 ask "How do I reverse a linked list in Python?"

# Dashboard
ald-01 dashboard                    # Default: localhost:7860
ald-01 dashboard --port 8080        # Custom port

# System
ald-01 status                       # System status
ald-01 doctor                       # Full health check
ald-01 setup                        # Setup wizard

# Providers
ald-01 provider list                # All providers
ald-01 provider free                # Free options
ald-01 provider add groq            # Add interactively

# Config
ald-01 config show                  # Current config
ald-01 config set brain_power 7     # Set brain power
ald-01 config reset                 # Reset defaults

# Voice
ald-01 voice test                   # Test TTS
ald-01 voice voices                 # List voices
```

### In-Chat Commands

```text
/exit    — Exit chat
/clear   — Clear conversation history
/agent   — Switch agent (code_gen, debug, review, security, general)
/voice   — Toggle voice on/off
/status  — System status
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

## <img src="https://img.shields.io/badge/-Architecture-795548?style=flat-square&logo=files&logoColor=white" height="25" alt="Architecture" />

```text
ALD-01/
├── bin/cli.js                    # npm global CLI wrapper
├── package.json                  # npm package config
│
├── src/ald01/
│   ├── __init__.py               # Package init & directory setup
│   ├── __main__.py               # python -m ald01 entry point
│   ├── cli.py                    # Click CLI (all commands)
│   ├── config.py                 # YAML config with brain power presets
│   │
│   ├── core/                     # Core Systems (40+ modules)
│   │   ├── orchestrator.py       # Central coordinator
│   │   ├── brain.py              # AI brain & decision engine
│   │   ├── chat_engine.py        # Chat processing engine
│   │   ├── reasoning.py          # Multi-strategy reasoning
│   │   ├── memory.py             # SQLite persistent memory
│   │   ├── tools.py              # Tool executor (fs, terminal, etc.)
│   │   ├── events.py             # Async pub-sub event bus
│   │   ├── context_manager.py    # Conversation context
│   │   ├── pipeline.py           # Processing pipeline
│   │   ├── plugins.py            # Plugin system
│   │   ├── scheduler.py          # Task scheduler
│   │   ├── analytics.py          # Usage analytics
│   │   ├── backup_manager.py     # Backup & restore
│   │   ├── code_analyzer.py      # Static analysis
│   │   ├── export_system.py      # Data export
│   │   ├── file_watcher.py       # File monitoring
│   │   ├── gateway.py            # API gateway
│   │   ├── webhooks.py           # Webhook engine
│   │   ├── session_manager.py    # Session management
│   │   ├── template_engine.py    # Jinja2 templating
│   │   ├── themes.py             # Theme engine
│   │   ├── localization.py       # i18n
│   │   ├── self_heal.py          # Self-healing & recovery
│   │   └── ...                   # 20+ more modules
│   │
│   ├── agents/                   # Specialized AI Agents
│   │   ├── base.py               # Base agent class
│   │   ├── codegen.py            # Code generation
│   │   ├── debug.py              # Debugging
│   │   ├── review.py             # Code review
│   │   ├── security.py           # Security analysis
│   │   └── general.py            # General purpose
│   │
│   ├── providers/                # AI Model Providers
│   │   ├── base.py               # Abstract provider
│   │   ├── openai_compat.py      # OpenAI-compatible
│   │   ├── ollama.py             # Local Ollama
│   │   ├── manager.py            # Routing & failover
│   │   └── benchmark.py          # Benchmarking
│   │
│   ├── dashboard/                # Web Dashboard
│   │   ├── server.py             # FastAPI + WebSocket
│   │   ├── api_routes.py         # REST API v1
│   │   ├── api_v2.py             # REST API v2
│   │   ├── api_ext.py            # Extended endpoints
│   │   └── static/               # Frontend (HTML/JS/CSS)
│   │
│   ├── services/voice.py         # TTS engine
│   ├── doctor/diagnostics.py     # Health checks
│   ├── telegram/bot.py           # Telegram bot
│   ├── onboarding/wizard.py      # Setup wizard
│   └── utils/hardware.py         # Hardware detection
│
├── pyproject.toml                # Python package config
├── requirements.txt              # pip dependencies
├── LICENSE                       # MIT
└── README.md
```

---

## <img src="https://img.shields.io/badge/-Configuration-F57C00?style=flat-square&logo=gear&logoColor=white" height="25" alt="Config" />

Stored in `~/.ald01/config.yaml`:

```yaml
brain_power: 5              # 1–10, controls reasoning depth

providers:
  groq:
    enabled: true
    priority: 1              # Lower = tried first
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
    enabled: false           # Shell command execution
  code_execute:
    enabled: false           # Python sandbox

telegram:
  token: ""
  allowed_users: []
```

---

## <img src="https://img.shields.io/badge/-Brain%20Power%20Levels-6A1B9A?style=flat-square&logo=zap&logoColor=white" height="25" alt="Brain Power" />

| Level | Name | Depth | Autonomous | Best For |
|:-----:|:-----|:-----:|:----------:|:---------|
| 1 | **Basic** | 1 | No | Simple Q&A |
| 2 | **Simple** | 2 | No | Quick answers |
| 3 | **Moderate** | 3 | No | Step-by-step explanations |
| 4 | **Standard** | 4 | No | Multi-step problem solving |
| 5 | **Advanced** | 5 | Limited | Complex analysis |
| 6 | **Deep** | 6 | Limited | Multi-perspective evaluation |
| 7 | **Expert** | 7 | Yes | Expert-level reasoning |
| 8 | **Master** | 8 | Yes | Deep research & synthesis |
| 9 | **Genius** | 9 | Yes | Multi-strategy reasoning |
| 10 | **AGI** | 10 | Yes | Full autonomous reasoning |

```bash
ald-01 config set brain_power 7
```

---

## <img src="https://img.shields.io/badge/-Doctor%20Diagnostics-43A047?style=flat-square&logo=stethoscope&logoColor=white" height="25" alt="Doctor" />

Run `ald-01 doctor` to check:

| Check | Details |
|:------|:--------|
| Python version | 3.10+ compatibility |
| Dependencies | Required and optional packages |
| Config file | YAML validity |
| Data directory | Permissions |
| Memory database | SQLite health |
| Dashboard port | Availability |
| System resources | RAM, disk space |
| Connectivity | Internet access |
| Ollama | Local model availability |
| Providers | API connections |
| API keys | Free tier configuration |
| Voice/TTS | Engine availability |

---

## <img src="https://img.shields.io/badge/-Privacy%20%26%20Security-D32F2F?style=flat-square&logo=shield&logoColor=white" height="25" alt="Security" />

| Principle | Details |
|:----------|:--------|
| **Fully local** | Runs 100% offline with Ollama |
| **No telemetry** | Zero data sent without consent |
| **API keys** | Stored as env vars, never in code |
| **Tool access** | Configurable — enable only what you need |
| **Sandbox** | Code execution in isolated subprocess |
| **Open source** | Full code transparency |

---

## <img src="https://img.shields.io/badge/-Dependencies-1565C0?style=flat-square&logo=python&logoColor=white" height="25" alt="Deps" />

### Core (auto-installed)

| Package | Purpose |
|:--------|:--------|
| `click` | CLI framework |
| `rich` | Terminal UI |
| `httpx` | Async HTTP client |
| `fastapi` | Web dashboard & API |
| `uvicorn` | ASGI server |
| `websockets` | Real-time communication |
| `pyyaml` | Config parsing |
| `psutil` | System monitoring |
| `python-dotenv` | Environment variables |
| `prompt_toolkit` | Interactive input |
| `jinja2` | Template engine |
| `aiosqlite` | Async SQLite |

### Optional

```bash
pip install ald-01[voice]       # Edge TTS + pyttsx3
pip install ald-01[dev]         # pytest, black, ruff
```

---

## <img src="https://img.shields.io/badge/-Contributing-00897B?style=flat-square&logo=git&logoColor=white" height="25" alt="Contributing" />

```bash
# Fork & clone
git clone https://github.com/YOUR_USERNAME/ALD-01.git
cd ALD-01

# Install dev mode
pip install -e ".[dev]"

# Feature branch
git checkout -b feature/awesome-feature

# Test
pytest

# PR
```

**Guidelines:** PEP 8 style (enforced by `ruff`) · docstrings on new functions · tests for new features · focused PRs

---

## <img src="https://img.shields.io/badge/-License-37474F?style=flat-square&logo=opensourceinitiative&logoColor=white" height="25" alt="License" />

MIT License — see [LICENSE](LICENSE) for details.

---

<p align="center">
  <a href="https://star-history.com/#aditya4232/ALD-01&Date">
    <img src="https://api.star-history.com/svg?repos=aditya4232/ALD-01&type=Date" width="550" alt="Star History" />
  </a>
</p>

---

<p align="center">
  <strong>ALD-01 — Your Desktop, Your Intelligence, Your Control.</strong>
  <br/><br/>
  Made by <a href="https://github.com/aditya4232">Aditya Shenvi</a>
  <br/><br/>
  <a href="https://github.com/aditya4232/ALD-01">Star this repo</a> · 
  <a href="https://github.com/aditya4232/ALD-01/issues">Report Bug</a> · 
  <a href="https://github.com/aditya4232/ALD-01/issues">Request Feature</a>
</p>
