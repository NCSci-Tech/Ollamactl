# Ollamactl
A complete guide to Ollama, ollamactl, and sgpt setup and use, particularly with mistral and codellama. Please be careful when following this guide as I had to troubleshoot and you may have to as well.

# Local AI Setup — (Arch Linux with intel/nvidia)

---

## Table of Contents

1. [System Specs](#system-specs)
2. [What Was Installed & Why](#what-was-installed--why)
3. [How It All Works Together](#how-it-all-works-together)
4. [Privacy & Data](#privacy--data)
5. [Ollama](#ollama)
6. [ollamactl](#ollamactl)
7. [sgpt (Shell-GPT)](#sgpt-shell-gpt)
8. [Your .zshrc Config](#your-zshrc-config)
9. [Model Guide](#model-guide)
10. [GPU & VRAM Management](#gpu--vram-management)
11. [Fine-tuning / Teaching the AI](#fine-tuning--teaching-the-ai)
12. [File Locations](#file-locations)
13. [Troubleshooting](#troubleshooting)
14. [Quick Reference Cheatsheet](#quick-reference-cheatsheet)

## What Was Installed & Why

| Tool | How Installed | Purpose |
|------|--------------|---------|
| `ollama` | AUR / install script | The core engine that runs AI models locally |
| `nvidia` drivers + CUDA | `pacman` | Lets Ollama use your GPU for faster inference |
| `python-pipx` | `pacman` | Safely installs Python CLI tools in isolated environments |
| `shell-gpt` (sgpt) | `pipx` | Lets you query the AI directly from your terminal inline |
| `ollamactl` | Manual script | Custom control script for managing everything |

---

## How It All Works Together

```
You (terminal)
     │
     ├── ollamactl ──────────────► manages Ollama service + models + GPU
     │
     ├── sgpt ───────────────────► sends prompts to Ollama API → prints response inline
     │
     └── ollama run <model> ─────► opens interactive chat session
              │
              ▼
         Ollama (localhost:11434)
              │
              ├── CPU ◄── handles overflow layers
              └── GPU ◄── handles as many layers as VRAM allows
                       │
                       └── Model ← stored on disk as .gguf files
```

**Ollama** is a local server that runs on `http://localhost:11434`. It loads AI models and exposes an API. Nothing ever leaves your machine.

**sgpt** is configured to talk to Ollama's API instead of OpenAI. The `OPENAI_API_KEY="ollama"` and `OPENAI_BASE_URL` env vars trick sgpt into pointing at your local server.

**ollamactl** is a bash wrapper that makes managing everything easier — starting/stopping the service, switching models, watching GPU usage, etc.

---

## Privacy & Data

| Question | Answer |
|----------|--------|
| Does Ollama send data anywhere? | No. After install, it's fully offline |
| Do the models call home? | No. Models are static files (.gguf) on your disk |
| Does sgpt send data to OpenAI? | No. It's pointed at localhost:11434 |
| Is chat history stored anywhere? | Only locally in `~/.local/share/ollamactl/history.log` |
| Can I block Ollama from the internet entirely? | Yes — `sudo ufw deny out from any to any app ollama` |

Your setup is 100% local. No telemetry, no data collection, no external API calls.

---

## Ollama

### What is it?
Ollama is a runtime that downloads, manages, and serves large language models locally. It runs as a background service and exposes a REST API at `http://localhost:11434`.

### Service Management

```bash
# Start
sudo systemctl start ollama

# Stop
sudo systemctl stop ollama

# Enable on boot
sudo systemctl enable ollama

# Check status
systemctl status ollama
```

### Basic Usage

```bash
# Interactive chat
ollama run mistral

# Inside the chat prompt (>>>):
# Just type and press Enter to chat
# /? — show help
# /bye — exit
# /set system "You are a linux expert" — set a system prompt for the session
# /show info — show model info
# /clear — clear conversation history

# List downloaded models
ollama list

# See what's currently loaded in memory
ollama ps

# Pull a new model
ollama pull phi3:mini

# Remove a model
ollama rm mistral

# Show model info
ollama show mistral
```

### API (what sgpt uses under the hood)

```bash
# Direct API call example
curl http://localhost:11434/api/generate \
  -d '{"model": "mistral", "prompt": "hello", "stream": false}'
```

---

## ollamactl

A custom bash script installed at `/usr/local/bin/ollamactl`.

### Installation Info
- Location: `/usr/local/bin/ollamactl`
- Config: `~/.config/ollamactl/config`
- Log: `~/.local/share/ollamactl/ollamactl.log`
- History: `~/.local/share/ollamactl/history.log`

### All Commands

#### Service Control
```bash
ollamactl start        # Start Ollama service
ollamactl stop         # Stop Ollama service
ollamactl restart      # Restart Ollama service
ollamactl status       # Full status: service, GPU, loaded models
```

#### Model Management
```bash
ollamactl models                  # List all downloaded + loaded models
ollamactl pull mistral            # Download a model
ollamactl pull phi3:mini          # Download phi3 mini
ollamactl remove mistral          # Delete a model from disk (asks confirmation)
ollamactl set-model phi3:mini     # Change your default model (saved to config)
```

#### GPU Control
```bash
ollamactl gpu status              # Full nvidia-smi output
ollamactl gpu watch               # Live GPU stats, updates every 2s (Ctrl+C to stop)
ollamactl gpu layers              # Show current layer offload setting
ollamactl gpu layers 20           # Set 20 layers on GPU (less VRAM)
ollamactl gpu layers 0            # CPU only — no GPU at all
ollamactl gpu layers 99           # Max GPU offload (default/auto)
ollamactl gpu reset               # Remove override, go back to auto
```

#### Chat & Queries
```bash
ollamactl chat                    # Interactive chat with default model
ollamactl chat phi3               # Interactive chat with specific model
ollamactl ask how do I tar a folder          # Single question, then exits
ollamactl ask --model phi3 explain iptables  # Ask with a specific model
```

#### Logs & History
```bash
ollamactl logs                    # Last 50 lines of the script log
ollamactl logs 100                # Last 100 lines
ollamactl history                 # Last 20 ask Q&A pairs
ollamactl history 50              # Last 50
```

#### Fine-tuning Guide
```bash
ollamactl finetune                # Prints the step-by-step training guide
```

#### Help
```bash
ollamactl --help
ollamactl help
ollamactl -h
```

### Understanding GPU Layers

When you run a model, Ollama splits it into "layers" and puts as many as possible into VRAM. Whatever doesn't fit goes into RAM and runs on CPU.

- Mistral has **33 layers** total
- With 4GB VRAM, roughly 20-25 layers fit depending on what else is using VRAM
- More layers on GPU = faster responses
- Use `ollamactl gpu layers <n>` to manually control this

```bash
# Example: limit to 15 GPU layers to leave VRAM free for other things
ollamactl gpu layers 15
ollamactl restart
ollamactl chat
```

---

## sgpt (Shell-GPT)

### What is it?
Shell-GPT (`sgpt`) is a CLI tool that lets you ask AI questions inline in your terminal without opening an interactive session. It's configured to use your local Ollama instead of OpenAI.

### How it's configured
These env vars in your `.zshrc` redirect sgpt to Ollama:
```bash
export OPENAI_API_KEY="ollama"        # dummy key, Ollama doesn't need a real one
export OPENAI_BASE_URL="http://localhost:11434/v1"  # points to local server
```

### All Usage Modes

```bash
# Basic question
sgpt --model mistral "how do I check disk usage"

# Using your aliases (shorter)
s "how do I check disk usage"

# Shell command mode — generates a shell command
sgpt --shell "find all .log files older than 7 days"
ss "find all .log files older than 7 days"    # using alias

# Execute mode — generates AND runs the command (be careful!)
sgpt --shell --execute "list processes sorted by memory"

# Code generation
sgpt --code "python script to batch rename files"

# Pipe input into it
dmesg | sgpt --model mistral "summarize any errors"
cat ~/.zshrc | sgpt "explain what this config does"
ls -la | sgpt "which files are largest"

# Read from a file
sgpt "explain this code" < script.py
```

### Aliases you have set up
```bash
ai    # = ollama run mistral (interactive chat)
ask   # = ollama run mistral (interactive chat)
s     # = sgpt (inline query)
ss    # = sgpt --shell (shell command mode)
ai-env # = activates the Python venv for fine-tuning
```

### sgpt vs ollamactl ask vs ollama run

| Tool | Use case |
|------|----------|
| `sgpt "question"` | Quick inline question, stays in your shell flow |
| `ss "do something"` | Get a shell command suggestion |
| `ollamactl ask "question"` | Same as sgpt but logged to history file |
| `ollama run mistral` | Full interactive multi-turn conversation |
| `ollamactl chat` | Same as above but uses your configured default model |

---

## Your .zshrc Config

Here's what was added to `~/.zshrc` and what each line does:

```bash
# Ollama / AI section

# Tells sgpt to use your local Ollama instead of OpenAI
export OPENAI_API_KEY="ollama"
export OPENAI_BASE_URL="http://localhost:11434/v1"

# Quick aliases for interactive chat
alias ai='ollama run mistral'
alias ask='ollama run mistral'

# Quick aliases for sgpt
alias s='sgpt'
alias ss='sgpt --shell'

# Activate the Python venv used for fine-tuning
alias ai-env='source ~/.venv/ai/bin/activate'

# Makes pipx-installed tools available (sgpt lives here)
export PATH="$HOME/.local/bin:$PATH"
```

To edit your zshrc: `nvim ~/.zshrc`
To reload after edits: `source ~/.zshrc`

---

## Model Guide

### Recommended models

| Model | Size | Best for | GPU fit |
|-------|------|----------|---------|
| `phi3:mini` | ~2.3GB | Fast answers, coding, terminal use |
| `llama3.2:3b` | ~2.0GB | Balanced reasoning | fast |
| `mistral` | ~4.1GB | General purpose, very capable |
| `codellama:7b` | ~3.8GB | Code generation, debugging |
| `deepseek-coder:6.7b` | ~3.8GB | Excellent for code |
| `llama3.1:8b` | ~4.7GB | Most capable, slower |

### Pulling models

```bash
ollama pull phi3:mini
ollama pull llama3.2:3b
ollama pull codellama:7b
```

### Switching your default model

```bash
ollamactl set-model phi3:mini
# Now 'ai', 'ask', and 'ollamactl chat' all use phi3
```

Or change the alias directly in `.zshrc`:
```bash
alias ai='ollama run phi3:mini'
```

---

## GPU & VRAM Management

### Reading nvidia-smi

```
| 0  NVIDIA GeForce GTX 1650  On  | 2934MiB / 4096MiB |  0%  |
```

- `2934MiB / 4096MiB` — VRAM used / total
- `0%` GPU Util — idle (no active inference)
- When you're actively chatting, GPU Util will spike to 60-100%

### Live monitoring

```bash
ollamactl gpu watch     # updates every 2s
# or
nvidia-smi              # one-time snapshot
watch -n1 nvidia-smi   # refresh every 1s
```

### If VRAM runs out

Ollama handles this automatically — it spills layers into RAM. You'll notice slower response times but it won't crash. To control this:

```bash
# Reduce GPU layers to free up VRAM for other apps
ollamactl gpu layers 15
ollamactl restart

# Go back to full auto
ollamactl gpu reset
ollamactl restart
```

---

## Fine-tuning / Teaching the AI

Fine-tuning lets you train a model on your own data so it learns your preferences, domain knowledge, or writing style. This creates a custom model that you own entirely.

### Method 1: RAG (Easiest — no training required)

RAG (Retrieval-Augmented Generation) lets the AI search your files when answering. No GPU training needed, updates instantly.

```bash
pip install llama-index --break-system-packages
```

Point it at your notes/docs and it retrieves relevant content before answering. Good for personal knowledge bases, documentation, etc.

### Method 2: LoRA Fine-tuning (Actual training)

LoRA (Low-Rank Adaptation) lets you fine-tune a model on your own data without retraining everything from scratch. Your 1650 Max-Q can do this for small models.

#### Setup

```bash
# Activate your AI venv first
ai-env

# Install unsloth (makes fine-tuning efficient on consumer GPU)
pip install unsloth
```

#### Step 1: Create your dataset

Make a file `~/my_dataset.jsonl` where each line is a JSON object:

```json
{"instruction": "How do I list hidden files?", "output": "Use ls -la to show all files including hidden ones."}
{"instruction": "What does chmod 755 mean?", "output": "chmod 755 sets owner: read/write/execute, group: read/execute, others: read/execute."}
```

The more examples, the better. Aim for at least 50-100 pairs.

#### Step 2: Fine-tune

Use Unsloth with a base model that fits your VRAM:
- `unsloth/Phi-3-mini-4k-instruct` (recommended for 4GB VRAM)
- `unsloth/llama-3.2-3b-instruct`
- `unsloth/mistral-7b-instruct-v0.3-bnb-4bit` (quantized, fits in 4GB)

See: https://github.com/unslothai/unsloth for training scripts.

#### Step 3: Export and load into Ollama

```python
# After training, export to GGUF format
model.save_pretrained_gguf("my_model", tokenizer, quantization_method="q4_k_m")
```

```bash
# Create a Modelfile
cat > Modelfile <<EOF
FROM ./my_model-Q4_K_M.gguf
SYSTEM "You are blvck's personal assistant with knowledge of his preferences and workflow."
EOF

# Import into Ollama
ollama create mymodel -f Modelfile

# Run it
ollama run mymodel
```

---

## File Locations

| File | Path | Purpose |
|------|------|---------|
| Ollama binary | `/usr/local/bin/ollama` | Main Ollama executable |
| ollamactl | `/usr/local/bin/ollamactl` | Your custom control script |
| sgpt | `~/.local/bin/sgpt` | Shell-GPT executable (installed by pipx) |
| Models storage | `~/.ollama/models/` | Where downloaded models live |
| ollamactl config | `~/.config/ollamactl/config` | Default model setting |
| ollamactl log | `~/.local/share/ollamactl/ollamactl.log` | Command history/log |
| Ask history | `~/.local/share/ollamactl/history.log` | Q&A history from `ollamactl ask` |
| AI venv | `~/.venv/ai/` | Python virtual environment for fine-tuning |
| Shell config | `~/.zshrc` | Your shell config with aliases and env vars |

---

## Troubleshooting

### Ollama not responding / API unreachable
```bash
ollamactl status          # check if it's running
ollamactl start           # start it
curl http://localhost:11434  # test API directly
```

### sgpt asking for OpenAI API key
```bash
# Check env vars are loaded
echo $OPENAI_API_KEY         # should print: ollama
echo $OPENAI_BASE_URL        # should print: http://localhost:11434/v1

# If empty, reload zshrc
source ~/.zshrc
```

### Model responding very slowly
- Check how many layers are on GPU: `ollamactl gpu watch`
- If GPU Util is 0% during inference, GPU isn't being used
- Make sure CUDA is working: `nvidia-smi` should show ollama process
- Try a smaller model: `ollama run phi3:mini`

### Out of VRAM
```bash
ollamactl gpu layers 10    # reduce GPU layers
ollamactl restart
```

### command not found: ollamactl
```bash
ls -la /usr/local/bin/ollamactl    # check it exists
hash -r                             # clear zsh command cache
/usr/local/bin/ollamactl --help    # try full path
```

### command not found: sgpt
```bash
echo $PATH | grep local            # check ~/.local/bin is in PATH
pipx ensurepath                    # re-add it
source ~/.zshrc
```

---

## Quick Reference Cheatsheet

```bash
# ── Start everything ──────────────────────────────────────
ollamactl start

# ── Check status ──────────────────────────────────────────
ollamactl status

# ── Chat interactively ────────────────────────────────────
ai                              # uses mistral
ollamactl chat phi3:mini        # uses phi3

# ── Quick questions ───────────────────────────────────────
s "how do I find large files"           # sgpt inline
ss "kill process on port 8080"          # get a shell command
ollamactl ask explain grep -v flag      # logged to history

# ── Pipe stuff in ────────────────────────────────────────
dmesg | s "any errors here?"
cat script.py | s "explain this"
ls -la | s "which is largest"

# ── GPU ──────────────────────────────────────────────────
ollamactl gpu watch             # live monitor
ollamactl gpu layers 15         # limit VRAM usage
ollamactl gpu reset             # back to auto

# ── Models ───────────────────────────────────────────────
ollamactl models                # list all
ollamactl pull phi3:mini        # download
ollamactl set-model phi3:mini   # change default

# ── Fine-tuning ──────────────────────────────────────────
ai-env                          # activate training environment
ollamactl finetune              # show full guide

# ── Logs ─────────────────────────────────────────────────
ollamactl logs                  # script log
ollamactl history               # Q&A history
```

---

---

## Updates & Fixes Log

### sgpt Model Name Format Fix
**Problem:** sgpt was throwing a 404 `model 'ollama/codellama:7b' not found` error.
**Cause:** The `DEFAULT_MODEL` in `~/.config/shell_gpt/.sgptrc` was set to `ollama/codellama:7b` — the `ollama/` prefix is not valid when talking to Ollama's API directly. Ollama just wants the model name as-is.
**Fix:** Edited `~/.config/shell_gpt/.sgptrc` and changed:
```
DEFAULT_MODEL=ollama/codellama:7b  ← wrong
DEFAULT_MODEL=codellama:7b         ← correct
```

### Switched Default Model from Mistral to Codellama:7b
**Why:** Codellama is trained specifically on code and terminal commands. It outputs cleaner responses in sgpt `--shell` mode without prepending descriptive text that breaks command execution.
**What changed:**
- `ollamactl` default → `codellama:7b` (saved in `~/.config/ollamactl/config`)
- `sgpt` default → `codellama:7b` (saved in `~/.config/shell_gpt/.sgptrc`)
- `ai` and `ask` aliases in `~/.zshrc` updated to use `codellama:7b`
- Mistral is still downloaded and available — run it anytime with `ollama run mistral`

### sgpt --shell Output Behavior
**How it works:** sgpt sends your prompt to the model with a system instruction to return only a shell command. Local models don't always follow this perfectly — Mistral would add descriptive text before the command causing execution to fail. Codellama follows the instruction cleanly.
**What clean output looks like:**
```
find . -type f -mtime 0
[E]xecute, [M]odify, [D]escribe, [A]bort:
```
**Always use D (Describe) before E (Execute)** to verify what the command does before running it.

### sgpt --shell Execute Behavior
When you hit E to execute, sgpt runs the command in your current shell. Some commands like `find . -mtime 0` will list files and then your shell may attempt to execute them as commands — this is normal and harmless. To avoid it, use M to modify and add `-print` explicitly, or just copy the command and run it yourself.

### Models Currently Downloaded
| Model | Size | Status |
|-------|------|--------|
| `codellama:7b` | 3.8GB | Default |
| `mistral` | 4.1GB | Available |

````markdown
---

## RAG (Retrieval-Augmented Generation)

### What is RAG?
RAG lets you feed your own documents, notes, code, and files to the AI so it can reference them when answering questions. Instead of retraining the model, it searches your files at query time and includes relevant chunks in the prompt automatically. This is the easiest way to "teach" codellama your own knowledge base without any GPU training.

Good for:
- Personal pentest notes and writeups
- Your own scripts and code
- CVE/vulnerability notes
- Tool documentation
- Anything you want the AI to reference without fine-tuning

### Installation
llama-index is a Python library, not a CLI tool, so pipx won't work for it. Install it inside your AI venv to keep it isolated from system Python:

```bash
# Activate your AI venv
ai-env

# Install llama-index with Ollama integration
pip install llama-index llama-index-llms-ollama llama-index-embeddings-ollama
````

### How it works

```
Your files (notes, code, docs)
        │
        ▼
llama-index indexes them into a local vector database
        │
        ▼
You ask a question
        │
        ▼
llama-index searches the index for relevant chunks
        │
        ▼
Relevant chunks + your question are sent to codellama
        │
        ▼
codellama answers with context from YOUR files
```

Everything stays local. No data leaves your machine.

### Basic usage (once set up)

```bash
# Always activate venv first
ai-env

# Then run your RAG script
python rag.py "how did I exploit that login bypass last week"
```

### RAG vs Fine-tuning

||RAG|Fine-tuning|
|---|---|---|
|Setup time|Minutes|Hours|
|GPU training required|No|Yes|
|Update with new data|Instant|Retrain|
|Best for|Notes, docs, references|Style, behavior, deep knowledge|
|Recommended to start|✓ Yes|Later|
