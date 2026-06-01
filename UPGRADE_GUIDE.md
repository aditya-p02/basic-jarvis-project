# JARVIS v2 — Multi-Agent Upgrade Guide

## What's New in v2

### 🤖 Multi-Agent Routing
Six specialized agents now handle commands:
- **⚡ Automation** — desktop control, apps, WhatsApp, Gmail
- **💻 Developer** — writing code, building projects, debugging  
- **🔍 Research** — web search, summarizing, Q&A
- **🖥️ System** — system stats, file management, processes
- **📋 Executive** — planning, emails, scheduling
- **🎨 Creative** — writing, brainstorming, content

### 🧠 Persistent Memory
- Memory no longer wiped after every task
- Semantic search finds relevant past conversations
- Long-term memory survives restarts
- Preference learning from natural conversation

### 👁️ Screen Vision
- JARVIS can now see your screen
- Triggered automatically when you say "screen", "what do you see", "what's open", etc.
- Uses Groq Vision (Llama 4 Scout)

---

## Project Structure

```
jarvis_v2/
├── main.py                    ← Entry point (UPDATED)
├── contacts.json
├── user_preferences.json      ← NEW: persistent preferences
├── jarvis_memory.db           ← NEW: persistent memory DB
├── core/
│   ├── agent_brain.py         ← UPGRADED: multi-agent routing
│   ├── database.py            ← UPGRADED: persistent memory
│   ├── screen_vision.py       ← NEW: screen analysis
│   ├── automator.py           ← unchanged
│   ├── code_executor.py       ← unchanged
│   ├── speech_engine.py       ← unchanged
│   ├── vision_engine.py       ← unchanged
│   └── voice_engine.py        ← unchanged
├── agents/
│   ├── __init__.py
│   └── router.py              ← NEW: agent classifier
├── ui/
│   └── hud.py                 ← UPGRADED: agent display
└── web/
    ├── index.html             ← UPGRADED: agent strip + voice viz
    └── three.min.js
```

---

## Installation

### 1. New Dependencies

```bash
pip install mss Pillow
```

mss = screen capture
Pillow = image compression

### 2. Update your .env

```
GROQ_API_KEY=your_key_here
```

Make sure Groq key has access to:
- `llama-3.3-70b-versatile` (brain)
- `meta-llama/llama-4-scout-17b-16e-instruct` (vision)

### 3. Copy files into your project

Replace these files with the new versions:
- `core/agent_brain.py`
- `core/database.py`  
- `ui/hud.py`
- `main.py`
- `web/index.html`

Add these NEW files:
- `agents/__init__.py`
- `agents/router.py`
- `core/screen_vision.py`

---

## New Voice Commands

| Command | What it does |
|---------|-------------|
| "Clear memory" | Wipes short-term context only |
| "Memory stats" | Reports how many memories stored |
| "Remember that [fact]" | Teaches JARVIS a preference |
| "My name is [name]" | Sets your name |
| "What do you see on screen" | Triggers screen analysis |

---

## Architecture Overview

```
Voice Input
    ↓
Wake Word Check
    ↓
AgentRouter.classify(command)  ← fast Groq call, ~200ms
    ↓
Pick Agent (automation/developer/research/system/executive/creative)
    ↓
Inject: relevant memories + user preferences + [optional screen context]
    ↓
Agent generates code
    ↓
CodeExecutor.execute(code)
    ↓
SpeechEngine.speak(output)
    ↓
Save to persistent memory (NO WIPE)
```

---

## Phase 2 Roadmap (Next Steps)

1. **Better TTS** — replace edge-tts with Kokoro (local, emotional)
   ```bash
   pip install kokoro-onnx soundfile
   ```

2. **Autonomous Planner** — break multi-step goals into sub-tasks
   - Add `agents/planner.py` with goal decomposition

3. **Plugin System** — YAML-defined skills
   - Drop `.yaml` files into `plugins/` folder
   - JARVIS auto-discovers them

4. **Full HUD Overhaul** — floating panels for:
   - Task queue
   - System resource monitor  
   - Calendar widget
   - Active agent dashboard

5. **Local LLM Fallback** — Ollama + Mistral 7B for offline mode

---

## Known Issues / Notes

- Vision model requires Groq key with Llama 4 access
- If embeddings fail (Ollama not running), falls back to keyword search
- Screen vision adds ~1-2s latency when triggered
- The router adds ~200ms overhead per command (worth it for quality)
