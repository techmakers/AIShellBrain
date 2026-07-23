# ShellBrain — AI-Powered Interactive Shell

ShellBrain is a single-file Python assistant that turns natural language into
shell commands and runs them for you. It works with any OpenAI-compatible
backend, so you can use the OpenAI cloud API **or** a fully local model.

**Supported backends:**

| Provider   | What it is                                    | Default endpoint              |
|------------|-----------------------------------------------|-------------------------------|
| `openai`   | OpenAI cloud API                              | `api.openai.com`              |
| `llamacpp` | Local `llama-server` (llama.cpp)              | `http://localhost:8080/v1`    |
| `ollama`   | Local Ollama (OpenAI-compatible endpoint)     | `http://localhost:11434/v1`   |

All connection details (provider, base URL, API key, model) live in a `.env`
file, and can be overridden on the command line.

## Features

- Execute shell commands from natural language input.
- Works with OpenAI, llama.cpp, or Ollama — switch with a single setting.
- Modern tool-calling: the model requests commands via the standard tools API.
- Responses stream to the terminal token by token, with markdown rendered to
  ANSI (bold, italics, headers, colored lists).
- On-demand explanations: by default a command's output is shown but not sent to
  the model; press Enter to have it explained. `--auto-explain` restores the
  automatic agentic loop (model reads output and can chain more commands).
- Configuration via `.env` (git-ignored) — no secrets in code or shell history.
- Conversation context kept across turns (disable with `--forget`).
- `cd` persists across commands.
- Confirmation prompts before running commands, with extra protection for
  dangerous ones (`rm`, `dd`, `mkfs`, `shutdown`, …).
- Interactive programs (`nano`, `vim`, `htop`, `less`, …) launched directly.
- Colorized output and command history.
- Standing instructions file: `~/AIShellBrain.md` is loaded automatically (if it
  exists) and its rules/facts are applied to every request.

## Requirements

- Python 3.8+
- Packages in `requirements.txt`: `openai`, `prompt_toolkit`, `python-dotenv`

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/techmakers/AIShellBrain.git
   cd AIShellBrain
   ```

2. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create your configuration:
   ```bash
   cp .env.example .env
   ```
   Then edit `.env` — pick a provider and fill in the relevant values (see below).

## Configuration (`.env`)

Copy `.env.example` to `.env` and edit it. Key settings:

```ini
# Which backend to use: openai | llamacpp | ollama
SHELLBRAIN_PROVIDER=llamacpp

# OpenAI cloud
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini

# llama.cpp server
LLAMACPP_BASE_URL=http://localhost:8080/v1
LLAMACPP_API_KEY=EMPTY
LLAMACPP_MODEL=local-model

# Ollama
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_API_KEY=ollama
OLLAMA_MODEL=llama3.1:latest
```

**Value precedence** for each setting (highest wins):
CLI argument → provider-specific env var (e.g. `OLLAMA_MODEL`) →
generic env var (`SHELLBRAIN_MODEL`) → built-in default.

## Usage

```bash
python shellbrain.py [options]
```

Everything is read from `.env` by default. Override any value on the command line:

```bash
# Use whatever is configured in .env
python shellbrain.py

# Force a specific backend / model
python shellbrain.py --provider ollama --model llama3.1:latest
python shellbrain.py --provider llamacpp --model qwen3-vl
python shellbrain.py --provider openai --model gpt-4o-mini --api-key sk-...
```

### Command-line Options

- `--provider {openai,llamacpp,ollama}`: Backend to use (overrides `SHELLBRAIN_PROVIDER`).
- `--model MODEL`: Model name (overrides the `.env` model).
- `--base-url URL`: OpenAI-compatible base URL (overrides `.env`).
- `--api-key KEY`: API key (overrides `.env`).
- `--forget`: Do not keep conversation context between inputs.
- `--auto-explain`: Automatically send each command's output back to the model
  so it explains and chains results. By default the output is only sent when you
  press Enter on an empty line right after the command.
- `-y`: Execute non-dangerous commands without confirmation.
- `--yy`: Execute even dangerous commands without confirmation.
- `--instructionfile [FILE]`: Path to a file with standing instructions for the
  assistant (created if missing). When the flag is omitted, `~/AIShellBrain.md`
  is loaded automatically if it exists.

### Quick start scripts

- Linux/macOS: `./start_AIShellBrain.sh` (installs deps, creates `.env`, then runs)
- Windows: `start_AIShellBrain.bat`

## How It Works

1. You type a request in natural language.
2. ShellBrain sends it, with the available tools, to the configured model.
3. If the model requests a command, you're asked to confirm (unless `-y`/`--yy`).
4. The command runs and its output is streamed to your terminal.
5. By default the output is **not** sent back to the model. Press Enter on an
   empty line to send it and get an explanation. (With `--auto-explain` the
   output is sent automatically and the model can chain further commands.)
6. Repeat until you type `exit`.

This on-demand explanation avoids an extra model round-trip (and its token cost)
for the many commands whose output you just want to see.

Special inputs: `clear`/`cls` resets the conversation, an empty line right after
a command asks the model to explain its output, `exit` quits.

## Safety and Permissions

- Commands run with the same permissions as the user running ShellBrain.
- Always review commands before confirming.
- `-y` skips confirmation for ordinary commands; dangerous ones still prompt.
- `--yy` skips **all** confirmations — use with caution.
- Command output sent back to the model is truncated to keep prompts small.

## License

See LICENCE.txt (MIT).

## Author

Techmakers srl — Alessandro Vernassa
