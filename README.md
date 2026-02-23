<p align="center">
  <img src="https://readme-typing-svg.herokuapp.com?font=Fira+Code&size=40&duration=3000&pause=1000&color=00D4FF&center=true&vCenter=true&width=600&lines=ALD-01;Advanced+Local+Desktop+Intelligence;Your+Desktop.+Your+AI.+Your+Control." alt="ALD-01 Typing" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/license-MIT-00C853?style=for-the-badge" />
  <img src="https://img.shields.io/badge/version-1.0.0-FF6D00?style=for-the-badge" />
  <img src="https://img.shields.io/badge/agents-5-7C4DFF?style=for-the-badge" />
  <img src="https://img.shields.io/badge/providers-10%2B-00BCD4?style=for-the-badge" />
  <img src="https://img.shields.io/badge/modules-40%2B-E91E63?style=for-the-badge" />
</p>

<p align="center">
  <a href="https://github.com/aditya4232/ALD-01"><img src="https://img.shields.io/github/stars/aditya4232/ALD-01?style=social" /></a>
  <a href="https://github.com/aditya4232/ALD-01/issues"><img src="https://img.shields.io/github/issues/aditya4232/ALD-01?color=yellow" /></a>
  <a href="https://github.com/aditya4232/ALD-01/fork"><img src="https://img.shields.io/github/forks/aditya4232/ALD-01?style=social" /></a>
</p>

---

**ALD-01** is a fully open-source, privacy-first AI agent system that runs **locally on your desktop**. It combines 10+ free AI providers, 5 specialized agents, advanced reasoning strategies, a professional web dashboard, and full device access — all in a single `pip install`.

> 🧠 Think of it as **your own local, open-source AI assistant** — with the power of commercial tools, but free, private, and fully under your control.

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+** — [Download Python](https://www.python.org/downloads/)
- **pip** (comes with Python)
- At least one AI provider API key, **or** [Ollama](https://ollama.ai) for fully local/offline use

### Install from PyPI (Global Command)

```bash
pip install ald-01
```

> After installing, the **`ald-01`** command is available globally from any terminal.

### Install from Source (Developers)

```bash
# Clone the repository
git clone https://github.com/aditya4232/ALD-01.git
cd ALD-01

# Install in editable mode (recommended for development)
pip install -e .

# Or install with voice support
pip install -e ".[voice]"

# Or install with dev tools (pytest, black, ruff)
pip install -e ".[dev]"
```

### Verify Installation

```bash
# Check if ald-01 is available globally
ald-01 --help

# Alternative command (same thing)
ald01 --help
```

### First Run

```bash
# Run the interactive setup wizard
ald-01 setup

# Or jump straight into chat
ald-01 chat

# Launch the web dashboard
ald-01 dashboard
```

### Set Up a Free Provider

```bash
# Option 1: Groq (fastest, generous free tier)
# Get your key from https://console.groq.com
export GROQ_API_KEY=gsk_your_key_here        # Linux/Mac
set GROQ_API_KEY=gsk_your_key_here           # Windows CMD
$env:GROQ_API_KEY="gsk_your_key_here"        # Windows PowerShell

# Option 2: Cerebras
export CEREBRAS_API_KEY=your_key_here         # https://cloud.cerebras.ai

# Option 3: Fully local with Ollama (no API key needed)
# Install from https://ollama.ai, then:
ollama pull llama3.2

# Verify your providers
ald-01 provider list
```

---

## ✨ Features

### 🤖 Multi-Agent System

| Agent | Specialty | Example Use |
|-------|-----------|-------------|
| **Code Gen** | Code generation & scaffolding | "Write a REST API in FastAPI" |
| **Debug** | Debugging & error resolution | "Fix this TypeError in my code" |
| **Review** | Code review & best practices | "Review this function for issues" |
| **Security** | Security analysis & hardening | "Check this code for vulnerabilities" |
| **General** | General Q&A & reasoning | "Explain decorators in Python" |

- **Automatic Agent Routing** — Queries are intelligently routed to the best agent
- **10 Brain Power Levels** — From basic Q&A to full AGI-like autonomous reasoning

### 🔌 10+ AI Providers (All Free Tiers)

| Provider | Model | Free Tier | Speed |
|----------|-------|-----------|-------|
| **Groq** | Llama 3.3 70B | ✅ Generous | ⚡ Ultra-fast |
| **Cerebras** | Llama 3.3 70B | ✅ | ⚡ Fast |
| **OpenRouter** | Various | ✅ | ⚡ |
| **Together AI** | Mixtral | ✅ | ⚡ |
| **GitHub Copilot** | GPT-4.1 | ✅ Pro users | ⚡ |
| **Google Gemini** | Gemini 2.0 | ✅ | ⚡ |
| **SambaNova** | Llama 3.1 | ✅ | ⚡ |
| **Novita AI** | Llama 3 | ✅ | ⚡ |
| **Hyperbolic** | Deepseek R1 | ✅ | ⚡ |
| **Ollama** | Any local model | ✅ Fully local | Depends on HW |

- **Automatic failover** — If one provider fails, the next one picks up instantly
- **Priority routing** — You choose which provider gets tried first
- **Provider benchmarking** — Built-in latency & quality scoring

### 🧠 Advanced Reasoning Engine

- **Chain-of-Thought** — Step-by-step logical reasoning
- **Tree-of-Thought** — Multi-branch problem exploration
- **Reflexion** — Self-correcting iterative refinement
- **Problem Decomposition** — Complex task breakdown into subtasks
- Reasoning depth scales automatically with brain power level (1–10)

### 🖥️ Professional Web Dashboard

- **Glassmorphism dark UI** with modern aesthetics
- **Real-time Activity Visualizer** via WebSocket
- **Chat Interface** with streaming responses
- **Sandbox Code Editor** with Python execution & export
- **File Browser** for full filesystem navigation
- **Terminal** for direct command execution
- **System Monitor** with live process listing
- **Doctor Diagnostics** with 12+ health checks
- **Provider Management** with one-click testing

### 🔧 Full Device Access (40+ Integrated Modules)

| Category | Capabilities |
|----------|-------------|
| **Filesystem** | Read, write, search, delete, move files |
| **Terminal** | Execute shell commands |
| **Code Sandbox** | Run Python in isolated subprocess |
| **System Info** | CPU, RAM, disk, GPU detection |
| **Process Mgmt** | List & manage running processes |
| **Clipboard** | Read and write clipboard content |
| **HTTP Requests** | Make web requests |
| **File Watcher** | Monitor files for changes in real-time |
| **Backup Manager** | Create & restore backups |
| **Analytics** | Usage analytics & insights |
| **Task Scheduler** | Schedule recurring tasks |
| **Export System** | Export data in multiple formats |
| **Webhooks** | Event-driven webhook system |
| **Code Analyzer** | Static code analysis |
| **API Gateway** | Built-in API gateway |
| **Session Manager** | Multi-session management |
| **Template Engine** | Jinja2-powered templating |
| **Plugin System** | Extensible plugin architecture |
| **Themes** | Customizable UI themes |
| **Localization** | Multi-language support (i18n) |

### 🔊 Voice / Text-to-Speech

- **Edge TTS** — Free Microsoft Neural voices (50+ voices, high quality)
- **pyttsx3** — Offline TTS fallback
- **System TTS** — OS-native speech (Windows, macOS, Linux)

### 📱 Remote Access

- **Telegram Bot** — Control ALD-01 from your phone
- Ask questions, check status, change settings remotely

### 💾 Persistent Memory

- **SQLite-backed** conversation & knowledge storage
- **Semantic memory** — Facts, preferences, patterns
- **Decision logs** — Track AI reasoning over time
- **User profile** — Personalized experience
- **Context manager** — Intelligent conversation context

---

## 📖 Usage

### CLI Commands

```bash
# ─── Chat ─────────────────────────────────────────
ald-01 chat                         # Interactive chat
ald-01 chat --agent security        # Chat with a specific agent
ald-01 chat --voice                 # Chat with voice output
ald-01 chat --stream                # Stream responses

# ─── Quick Question ───────────────────────────────
ald-01 ask "How do I reverse a linked list in Python?"

# ─── Dashboard ────────────────────────────────────
ald-01 dashboard                    # Launch web dashboard (default: localhost:7860)
ald-01 dashboard --port 8080        # Custom port

# ─── System ───────────────────────────────────────
ald-01 status                       # System status overview
ald-01 doctor                       # Full diagnostic health check
ald-01 setup                        # Run the setup wizard

# ─── Providers ────────────────────────────────────
ald-01 provider list                # Show all providers & status
ald-01 provider free                # Show free provider options
ald-01 provider add groq            # Add a provider interactively

# ─── Configuration ────────────────────────────────
ald-01 config show                  # Show current config
ald-01 config set brain_power 7     # Set brain power level
ald-01 config reset                 # Reset to defaults

# ─── Voice ────────────────────────────────────────
ald-01 voice test                   # Test TTS
ald-01 voice voices                 # List available voices
```

### In-Chat Commands

```
/exit    — Exit chat
/clear   — Clear conversation history
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
ALD-01/
├── src/ald01/
│   ├── __init__.py               # Package init & directory setup
│   ├── __main__.py               # python -m ald01 entry point
│   ├── cli.py                    # Click CLI (all commands)
│   ├── config.py                 # YAML config with brain power presets
│   │
│   ├── core/                     # ⚙️  Core Systems (40+ modules)
│   │   ├── orchestrator.py       # Central coordinator
│   │   ├── brain.py              # AI brain & decision engine
│   │   ├── chat_engine.py        # Chat processing engine
│   │   ├── reasoning.py          # Multi-strategy reasoning
│   │   ├── memory.py             # SQLite persistent memory
│   │   ├── tools.py              # Tool executor (fs, terminal, etc.)
│   │   ├── events.py             # Async pub-sub event bus
│   │   ├── context_manager.py    # Conversation context management
│   │   ├── pipeline.py           # Processing pipeline
│   │   ├── modes.py              # Operating modes
│   │   ├── tasks.py              # Task management
│   │   ├── scheduler.py          # Task scheduler
│   │   ├── worker.py             # Background workers
│   │   ├── plugins.py            # Plugin system
│   │   ├── skill_manager.py      # Skill management
│   │   ├── subagents.py          # Sub-agent orchestration
│   │   ├── multi_model.py        # Multi-model coordination
│   │   ├── analytics.py          # Usage analytics
│   │   ├── backup_manager.py     # Backup & restore
│   │   ├── code_analyzer.py      # Static code analysis
│   │   ├── executor.py           # Command executor
│   │   ├── export_system.py      # Data export (JSON, CSV, etc.)
│   │   ├── file_watcher.py       # Real-time file monitoring
│   │   ├── gateway.py            # API gateway
│   │   ├── webhooks.py           # Webhook engine
│   │   ├── session_manager.py    # Session management
│   │   ├── template_engine.py    # Jinja2 templating
│   │   ├── themes.py             # UI theme engine
│   │   ├── localization.py       # i18n / multi-language
│   │   ├── integrations.py       # Third-party integrations
│   │   ├── learning.py           # Adaptive learning
│   │   ├── mcp_manager.py        # MCP protocol manager
│   │   ├── self_heal.py          # Self-healing & recovery
│   │   ├── prompt_library.py     # Prompt templates
│   │   ├── notifications.py      # Notification system
│   │   ├── logging_config.py     # Structured logging
│   │   ├── validator.py          # Input validation
│   │   ├── revert.py             # Undo/revert system
│   │   ├── status.py             # System status engine
│   │   ├── config_editor.py      # Config editor
│   │   ├── data_manager.py       # Data management
│   │   └── autostart.py          # Auto-start configuration
│   │
│   ├── agents/                   # 🤖 Specialized AI Agents
│   │   ├── base.py               # Base agent class
│   │   ├── codegen.py            # Code generation
│   │   ├── debug.py              # Debugging
│   │   ├── review.py             # Code review
│   │   ├── security.py           # Security analysis
│   │   └── general.py            # General purpose
│   │
│   ├── providers/                # 🔌 AI Model Providers
│   │   ├── base.py               # Abstract provider interface
│   │   ├── openai_compat.py      # Universal OpenAI-compatible
│   │   ├── ollama.py             # Local Ollama provider
│   │   ├── manager.py            # Provider routing & failover
│   │   └── benchmark.py          # Provider benchmarking
│   │
│   ├── dashboard/                # 🖥️  Web Dashboard
│   │   ├── server.py             # FastAPI + WebSocket server
│   │   ├── api_routes.py         # REST API routes
│   │   ├── api_v2.py             # API v2 endpoints
│   │   ├── api_ext.py            # Extended API endpoints
│   │   └── static/               # Frontend assets
│   │       ├── index.html        # Dashboard UI
│   │       ├── app.js            # Frontend logic
│   │       └── styles.css        # Styles
│   │
│   ├── services/                 # 🔊 Optional Services
│   │   └── voice.py              # Text-to-Speech engine
│   │
│   ├── doctor/                   # 🩺 Diagnostics
│   │   └── diagnostics.py        # 12+ health checks
│   │
│   ├── visualization/            # 📊 Visualization
│   │   └── thinking.py           # Rich terminal thinking UI
│   │
│   ├── telegram/                 # 📱 Remote Access
│   │   └── bot.py                # Telegram bot
│   │
│   ├── onboarding/               # 🎓 First-Time Setup
│   │   └── wizard.py             # Interactive setup wizard
│   │
│   └── utils/                    # 🔨 Utilities
│       └── hardware.py           # Hardware detection & GPU
│
├── pyproject.toml                # Package configuration
├── requirements.txt              # Dependencies
├── LICENSE                       # MIT License
└── README.md                     # This file
```

---

## ⚙️ Configuration

Configuration is stored in `~/.ald01/config.yaml`. Key settings:

```yaml
brain_power: 5              # 1–10, controls reasoning depth

providers:
  groq:
    enabled: true
    priority: 1              # Lower = higher priority
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
    enabled: false           # Enable shell command execution
  code_execute:
    enabled: false           # Enable Python sandbox

telegram:
  token: ""                  # Telegram bot token
  allowed_users: []          # List of authorized user IDs
```

---

## 🧠 Brain Power Levels

| Level | Name | Reasoning Depth | Autonomous | Best For |
|-------|------|:---------------:|:----------:|----------|
| 1 | **Basic** | 1 | ❌ | Simple Q&A |
| 2 | **Simple** | 2 | ❌ | Quick answers with reasoning |
| 3 | **Moderate** | 3 | ❌ | Step-by-step explanations |
| 4 | **Standard** | 4 | ❌ | Multi-step problem solving |
| 5 | **Advanced** | 5 | ⚡ Limited | Complex analysis |
| 6 | **Deep** | 6 | ⚡ Limited | Multi-perspective evaluation |
| 7 | **Expert** | 7 | ✅ | Expert-level reasoning |
| 8 | **Master** | 8 | ✅ | Deep research & synthesis |
| 9 | **Genius** | 9 | ✅ | Multi-strategy reasoning |
| 10 | **AGI** | 10 | ✅ | Full autonomous reasoning |

```bash
# Set your brain power level
ald-01 config set brain_power 7
```

---

## 🩺 Doctor Diagnostics

Run `ald-01 doctor` to perform a full system health check:

- ✅ Python version compatibility
- ✅ Required & optional dependencies
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

| Feature | Details |
|---------|---------|
| **Fully Local** | Can run 100% offline with Ollama |
| **No Telemetry** | Zero data sent without your consent |
| **API Keys** | Stored as env vars, never in code |
| **Tool Access** | Configurable — enable only what you need |
| **Sandbox** | Code execution runs in isolated subprocess |
| **Open Source** | Full code transparency |

---

## 📦 Dependencies

### Required (auto-installed)

| Package | Purpose |
|---------|---------|
| `click` | CLI framework |
| `rich` | Beautiful terminal UI |
| `httpx` | Async HTTP client |
| `fastapi` | Web dashboard & API server |
| `uvicorn` | ASGI server |
| `websockets` | Real-time communication |
| `pyyaml` | Configuration parsing |
| `psutil` | System monitoring |
| `python-dotenv` | Environment variable management |
| `prompt_toolkit` | Interactive terminal input |
| `jinja2` | Template engine |
| `aiosqlite` | Async SQLite |

### Optional

```bash
# Voice / TTS support
pip install ald-01[voice]

# Development tools
pip install ald-01[dev]
```

---

## 🤝 Contributing

Contributions are welcome! Here's how to get started:

```bash
# 1. Fork & clone
git clone https://github.com/YOUR_USERNAME/ALD-01.git
cd ALD-01

# 2. Install in dev mode
pip install -e ".[dev]"

# 3. Create a feature branch
git checkout -b feature/awesome-feature

# 4. Make your changes & run tests
pytest

# 5. Submit a pull request
```

### Contribution Guidelines

- Follow PEP 8 style (enforced by `ruff`)
- Add docstrings to new functions and classes
- Write tests for new features
- Keep PRs focused and descriptive

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🌟 Star History

<p align="center">
  <a href="https://star-history.com/#aditya4232/ALD-01&Date">
    <img src="https://api.star-history.com/svg?repos=aditya4232/ALD-01&type=Date" width="600" alt="Star History Chart" />
  </a>
</p>

---

<p align="center">
  <strong>ALD-01 — Your Desktop, Your Intelligence, Your Control.</strong>
  <br/><br/>
  Made with ❤️ by <a href="https://github.com/aditya4232">Aditya Shenvi</a>
  <br/><br/>
  <a href="https://github.com/aditya4232/ALD-01">⭐ Star this repo</a> •
  <a href="https://github.com/aditya4232/ALD-01/issues">🐛 Report Bug</a> •
  <a href="https://github.com/aditya4232/ALD-01/issues">💡 Request Feature</a>
</p>
