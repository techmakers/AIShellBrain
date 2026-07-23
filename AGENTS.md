# AGENTS.md - AI Agent Guidelines for ShellBrain

This document provides guidelines for AI coding agents working on the ShellBrain codebase.

## Project Overview

ShellBrain is an AI-powered interactive shell that turns natural language into
shell commands and runs them. It talks to any OpenAI-compatible backend
(OpenAI cloud, a local llama.cpp server, or Ollama) through the `openai` SDK.
The whole application lives in a **single file**: `shellbrain.py`.

## Repository Structure

```
ShellBrain/
├── shellbrain.py            # The entire application (single file)
├── .env.example             # Template for local configuration
├── .env                     # Local configuration (git-ignored)
├── requirements.txt         # Python dependencies
├── instructionfile_example.md
├── start_AIShellBrain.sh    # Linux/macOS launcher
├── start_AIShellBrain.bat   # Windows launcher
├── README.md
├── LICENCE.txt              # MIT License
└── screenshots/             # Documentation screenshots
```

## Configuration

All connection details are read from `.env` via `python-dotenv`. Never hardcode
credentials. Provider defaults live in the `PROVIDER_DEFAULTS` dict in
`shellbrain.py`.

Value precedence for each setting (highest wins):
CLI argument → provider-specific env var (e.g. `OLLAMA_MODEL`) →
generic env var (e.g. `SHELLBRAIN_MODEL`) → built-in default.

Relevant env vars:

- `SHELLBRAIN_PROVIDER` — `openai` | `llamacpp` | `ollama`
- `SHELLBRAIN_MODEL`, `SHELLBRAIN_BASE_URL`, `SHELLBRAIN_API_KEY` — generic overrides
- `OPENAI_*`, `LLAMACPP_*`, `OLLAMA_*` — per-provider `*_MODEL`, `*_BASE_URL`, `*_API_KEY`

## Build/Run Commands

### Installation

```bash
pip install -r requirements.txt
cp .env.example .env   # then edit .env
```

### Running the Application

```bash
# Use whatever is configured in .env
python shellbrain.py

# Force a backend / model on the command line
python shellbrain.py --provider ollama --model llama3.1:latest
python shellbrain.py --provider llamacpp --model qwen3-vl
python shellbrain.py --provider openai --model gpt-4o-mini --api-key sk-...
```

### CLI Options

- `--provider {openai,llamacpp,ollama}`: Backend (overrides `SHELLBRAIN_PROVIDER`)
- `--model MODEL`: Model name
- `--base-url URL`: OpenAI-compatible base URL
- `--api-key KEY`: API key
- `--forget`: Don't keep conversation context
- `--auto-explain`: Auto-send command output back to the model (loop). Off by
  default — output is sent only when the user presses Enter after a command.
- `-y`: Execute non-dangerous commands without confirmation
- `--yy`: Execute ALL commands without confirmation
- `--instructionfile [PATH]`: Extra-instructions file

## Testing

**Note:** This project has no formal test suite. `test.py` (in `.gitignore`) is a
development scratch file, not unit tests.

### Manual Testing

```bash
# Against a local llama.cpp server on :8080
python shellbrain.py --provider llamacpp

# Against a local Ollama server on :11434
python shellbrain.py --provider ollama --model llama3.1:latest

# Non-interactive smoke test
printf 'what is my current working directory?\nexit\n' | python shellbrain.py -y
```

## Code Style Guidelines

### Architecture

- Everything is in `shellbrain.py`. Keep it a single file.
- All backends go through the `openai` SDK; only `base_url`/`api_key`/`model`
  differ per provider. Do not add per-provider request code or manual JSON
  tool-call parsing — use the standard `tools` / `tool_calls` API.

### Import Organization

Standard library first, then third-party, both alphabetized. Imports live at the
top of the file only (no imports inside functions).

```python
import argparse
import json
import os
import platform
import subprocess
import sys

from dotenv import load_dotenv
from openai import OpenAI
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
```

### Naming Conventions

| Element             | Convention  | Example                     |
|---------------------|-------------|-----------------------------|
| Functions           | snake_case  | `execute_shell_command()`   |
| Variables           | snake_case  | `conversation_history`      |
| Module constants    | UPPER_CASE  | `COLORS`, `DANGEROUS_COMMANDS`, `TOOLS` |

### Formatting

- 4-space indentation, no tabs.
- f-strings for formatting; double quotes for strings.
- Use docstrings for functions; inline comments for non-obvious logic.

### ANSI Color Output

Use `print_colored()` and the `COLORS` dict. Do not print raw escape codes.

### Error Handling

Prefer specific exception types. Errors that must be reported back to the model
(command execution, API calls) are caught broadly and returned/printed as text
rather than crashing the REPL.

## Key Patterns

### Tool-calling loop

`chat_turn()` streams the model response, appends the assistant message (with any
`tool_calls`), executes each requested tool, and appends a `role: "tool"` result
message with the matching `tool_call_id`.

By default it then **stops** and returns True (output shown but not explained);
the main loop lets the user press Enter to send the pending output for an
explanation. With `--auto-explain` it instead loops — re-calling the model on the
tool results until a plain answer — bounded by `MAX_TOOL_ITERATIONS`.

Streaming detail: tool-call fragments arrive across chunks and are reassembled by
`index` into `{id, name, arguments}` dicts; `handle_tool_calls()` consumes that
shape. Assistant text is rendered live through `StreamingMarkdownPrinter`.

### Command Execution

- `execute_shell_command()`: `subprocess.Popen`, streams combined stdout/stderr.
- `run_interactive_program()`: `os.system()` for full-screen programs.
- `cd` is handled in-process so directory changes persist across commands.

### Interactive Programs

```python
INTERACTIVE_PROGRAMS = ["nano", "vim", "vi", "emacs", "less", "more", "htop", "top", "man"]
```

### Dangerous Commands

```python
DANGEROUS_COMMANDS = ["rm", "rmdir", "del", "erase", "rd", "mkfs", "dd", "shutdown", "reboot"]
is_dangerous = any(command.strip().startswith(cmd) for cmd in DANGEROUS_COMMANDS)
```

## Dependencies

Required (`requirements.txt`):

- `openai` — OpenAI-compatible API client (used for all three backends)
- `prompt_toolkit` — interactive prompt with history
- `python-dotenv` — loads `.env`

## Platform Support

Cross-platform (Linux, macOS, Windows). Use the `platform` module for OS detection.

## Security Considerations

- Never hardcode API keys; read them from `.env`.
- `.env` is git-ignored — keep it that way.
- Always confirm dangerous commands unless `--yy` is set.
- Command output is truncated (`MAX_OUTPUT_LENGTH`) before being sent back.
- Review AI-generated commands before execution.

## File Locations

- Command history: `~/.shellbrain_history`
- Default instruction file: `~/AIShellBrain.md` (loaded automatically when it
  exists, even without `--instructionfile`)
- Local configuration: `./.env`

### Standing instructions

`load_instructions()` reads the instruction file; `init_conversation_history()`
injects it both as a high-priority system message AND as a seeded user/assistant
exchange near the start of the conversation. The conversational seeding matters:
small local models follow facts stated in the conversation far more reliably than
facts placed only in the system prompt.

## Contributing

When making changes:

1. Keep the app in the single `shellbrain.py` file.
2. Test manually against at least one local backend (llama.cpp or Ollama).
3. Update `README.md` and this file when adding features/options.
4. Consider the security implications of shell command execution.
