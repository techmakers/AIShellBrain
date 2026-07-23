#!/usr/bin/env python3
"""
ShellBrain - AI-powered interactive shell.

A single-file assistant that turns natural language into shell commands and runs
them for you. It talks to any OpenAI-compatible backend:

  * openai    - OpenAI cloud API
  * llamacpp  - a local llama.cpp server (llama-server, /v1 endpoint)
  * ollama    - a local Ollama server (/v1 OpenAI-compatible endpoint)

All connection details (provider, base URL, API key, model) are read from a
`.env` file. Copy `.env.example` to `.env` and edit it, or override any value
on the command line.

Author: Alessandro Vernassa
License: MIT
"""

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

# --------------------------------------------------------------------------- #
# Constants and configuration
# --------------------------------------------------------------------------- #

APP_NAME = "ShellBrain"

# ANSI color codes for terminal output.
COLORS = {
    "RED": "\033[91m",
    "GREEN": "\033[92m",
    "LIGHT_GREEN": "\033[92;1m",
    "YELLOW": "\033[93m",
    "LIGHT_YELLOW": "\033[93;1m",
    "BLUE": "\033[94m",
    "MAGENTA": "\033[95m",
    "CYAN": "\033[96m",
    "LIGHT_CYAN": "\033[96;1m",
    "LIGHT_WHITE": "\033[97;1m",
    "WHITE": "\033[97m",
    "RESET": "\033[0m",
}

# Commands considered destructive: an extra confirmation is required.
DANGEROUS_COMMANDS = ["rm", "rmdir", "del", "erase", "rd", "mkfs", "dd", "shutdown", "reboot"]

# Programs that take over the terminal: run them directly instead of capturing.
INTERACTIVE_PROGRAMS = ["nano", "vim", "vi", "emacs", "less", "more", "htop", "top", "man"]

# Built-in per-provider defaults. Values in `.env` override these.
PROVIDER_DEFAULTS = {
    "openai": {
        "base_url": None,  # use the SDK default (api.openai.com)
        "api_key": None,   # must be provided
        "model": "gpt-4o-mini",
    },
    "llamacpp": {
        "base_url": "http://localhost:8080/v1",
        "api_key": "EMPTY",
        "model": "local-model",
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "api_key": "ollama",
        "model": "llama3.1:latest",
    },
}

# Maximum length of a tool result fed back to the model.
MAX_OUTPUT_LENGTH = 4000

# Safety guard against infinite tool-calling loops in a single turn.
MAX_TOOL_ITERATIONS = 15

# Default instruction file, loaded automatically when it exists.
DEFAULT_INSTRUCTION_FILE = os.path.join(os.path.expanduser("~"), "AIShellBrain.md")


# --------------------------------------------------------------------------- #
# Output helpers
# --------------------------------------------------------------------------- #

def print_colored(text, color="WHITE"):
    """Print `text` using the given named ANSI color."""
    color_code = COLORS.get(color.upper(), COLORS["WHITE"])
    print(f"{color_code}{text}{COLORS['RESET']}")


class StreamingMarkdownPrinter:
    """Render a stream of markdown text to ANSI, chunk by chunk.

    Handles **bold**, *italic* and `#` headers incrementally while writing each
    piece to the terminal as it arrives. Because markdown markers span several
    tokens, ambiguous trailing characters (a lone ``*`` that might turn into
    ``**``, or a run of ``#`` at the start of a line) are buffered until enough
    text arrives to resolve them.
    """

    def __init__(self, base_color="LIGHT_YELLOW", list_color="CYAN"):
        self.base_color = COLORS.get(base_color.upper(), COLORS["WHITE"])
        self.list_color = COLORS.get(list_color.upper(), COLORS["CYAN"])
        self.bold = False
        self.italic = False
        self.header = False
        self.in_list_line = False  # a bullet/numbered list line, shown in list_color
        self.at_line_start = True
        self.buffer = ""
        self.started = False
        self._last = ""
        self.prev_char = ""  # last text char emitted, for emphasis flanking rules

    def _state(self):
        """ANSI sequence that re-establishes the current style from scratch."""
        base = self.list_color if self.in_list_line else self.base_color
        seq = COLORS["RESET"] + base
        if self.bold or self.header:
            seq += "\033[1m"
        if self.italic:
            seq += "\033[3m"
        return seq

    @staticmethod
    def _list_marker_len(buf, i, n):
        """Length of a list marker at position `i`, or 0 (none) / -1 (need more).

        Recognizes unordered markers ("* ", "- ", "+ ") and ordered markers
        ("1. ", "2) ", ...) at the very start of a line.
        """
        c = buf[i]
        if c in "*-+":
            if i + 1 >= n:
                return -1  # need the next char to tell a marker from '**'/text
            return 2 if buf[i + 1] == " " else 0
        if c.isdigit():
            j = i
            while j < n and buf[j].isdigit():
                j += 1
            if j >= n:
                return -1  # digits might continue, or the punctuation is missing
            if buf[j] in ".)":
                if j + 1 >= n:
                    return -1  # need the char after the punctuation
                return (j + 2 - i) if buf[j + 1] == " " else 0
            return 0
        return 0

    def _write(self, text):
        if not text:
            return
        sys.stdout.write(text)
        self._last = text[-1]

    def feed(self, text):
        """Consume a chunk of streamed text and print what can be resolved."""
        if not self.started:
            self._write(self.base_color)
            self.started = True

        self.buffer += text
        out = []
        buf = self.buffer
        n = len(buf)
        i = 0

        def emit_literal(s):
            out.append(s)
            self.at_line_start = False
            if s:
                self.prev_char = s[-1]

        while i < n:
            c = buf[i]

            # Header: one or more '#' at the start of a line followed by a space.
            if self.at_line_start and c == "#":
                j = i
                while j < n and buf[j] == "#":
                    j += 1
                if j == n:
                    break  # need the next char to decide; hold in buffer
                if buf[j] == " ":
                    self.header = True
                    out.append(self._state())
                    i = j + 1  # skip the '#'s and the single space
                    self.at_line_start = False
                    continue
                emit_literal(buf[i:j])
                i = j
                continue

            # List item: bullet or numbered marker at the start of a line.
            if self.at_line_start:
                mlen = self._list_marker_len(buf, i, n)
                if mlen == -1:
                    break  # need more text to decide; hold in buffer
                if mlen > 0:
                    self.in_list_line = True
                    out.append(self._state())  # switch to the list color
                    emit_literal(buf[i:i + mlen])  # keep the marker visible
                    i += mlen
                    continue

            if c == "\n":
                changed = self.header or self.in_list_line
                self.header = False
                self.in_list_line = False
                if changed:
                    out.append(self._state())  # restore the base color
                out.append("\n")
                self.prev_char = "\n"
                i += 1
                self.at_line_start = True
                continue

            if c == "*":
                # Determine whether this is a '**' (bold) or '*' (italic) marker.
                if i + 1 >= n:
                    break  # could be the first '*' of '**'; hold for more text
                marker = "**" if buf[i + 1] == "*" else "*"
                mlen = len(marker)
                active = self.bold if marker == "**" else self.italic

                if active:
                    # Closing marker: valid only if preceded by a non-space char.
                    prev = buf[i - 1] if i > 0 else self.prev_char
                    if prev and not prev.isspace():
                        if marker == "**":
                            self.bold = False
                        else:
                            self.italic = False
                        out.append(self._state())
                        i += mlen
                        self.at_line_start = False
                        continue
                    emit_literal(marker)
                    i += mlen
                    continue

                # Opening marker: valid only if followed by a non-space char.
                if i + mlen >= n:
                    break  # need the char after the marker to decide; hold
                after = buf[i + mlen]
                if not after.isspace():
                    if marker == "**":
                        self.bold = True
                    else:
                        self.italic = True
                    out.append(self._state())
                    i += mlen
                    self.at_line_start = False
                    continue
                emit_literal(marker)
                i += mlen
                continue

            emit_literal(c)
            i += 1

        self.buffer = buf[i:]
        self._write("".join(out))
        sys.stdout.flush()

    def flush(self):
        """Emit any held-back text literally and reset styling."""
        tail = self.buffer
        self.buffer = ""
        self._write(tail)
        need_newline = self._last != "\n"
        self._write(COLORS["RESET"])
        if need_newline:
            self._write("\n")
        sys.stdout.flush()


def truncate_string(input_string, max_length=MAX_OUTPUT_LENGTH):
    """Truncate long output before sending it back to the model."""
    input_string = str(input_string)
    if len(input_string) > max_length:
        return input_string[:max_length] + "\n[TRUNCATED]"
    return input_string


# --------------------------------------------------------------------------- #
# Command execution
# --------------------------------------------------------------------------- #

def run_interactive_program(command):
    """Launch a program that needs full terminal control (editors, pagers)."""
    print_colored(f"Launching interactive program: {command}", "LIGHT_YELLOW")
    os.system(command)
    return "Interactive program finished."


def execute_shell_command(command):
    """Run a shell command, streaming output live, and return it as a string.

    `cd` is handled in-process so directory changes persist across commands.
    Interactive programs are detected and launched directly.
    """
    try:
        # Detect interactive programs up front (before any splitting).
        first_word = command.split()[0] if command.split() else ""
        if first_word in INTERACTIVE_PROGRAMS:
            print_colored("Interactive program detected. Launching...", "YELLOW")
            return run_interactive_program(command)

        print_colored(f"Executing: {command}", "LIGHT_GREEN")

        output = []
        # Handle chained commands so in-process `cd` works between parts.
        for part in command.split("&&"):
            part = part.strip()
            if not part:
                continue

            if part == "cd" or part.startswith("cd "):
                target = part[2:].strip() or os.path.expanduser("~")
                target = os.path.expanduser(target)
                try:
                    os.chdir(target)
                    msg = f"Changed directory to: {os.getcwd()}"
                    print_colored(msg, "GREEN")
                    output.append(msg)
                except FileNotFoundError:
                    msg = f"Error: directory not found: {target}"
                    print_colored(msg, "RED")
                    output.append(msg)
                except PermissionError:
                    msg = f"Error: permission denied: {target}"
                    print_colored(msg, "RED")
                    output.append(msg)
                continue

            process = subprocess.Popen(
                part,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            for line in process.stdout:
                line = line.rstrip("\n")
                print(line)
                output.append(line)
            process.wait()
            if process.returncode != 0:
                msg = f"Error: command exited with status {process.returncode}"
                print_colored(msg, "RED")
                output.append(msg)

        return "\n".join(output) if output else "(no output)"
    except Exception as exc:  # noqa: BLE001 - report any execution failure to the model
        return f"Error during execution: {exc}"


# --------------------------------------------------------------------------- #
# Tool definitions (OpenAI-compatible function calling)
# --------------------------------------------------------------------------- #

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "execute_shell_command",
            "description": (
                "Execute a non-interactive shell command and return its combined "
                "stdout/stderr output. Use for anything that prints a result."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute.",
                    }
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_interactive_program",
            "description": (
                "Launch an interactive/full-screen program (text editors, pagers, "
                "TUIs such as nano, vim, less, htop) that needs terminal control."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The interactive program command to launch.",
                    }
                },
                "required": ["command"],
            },
        },
    },
]

# Maps tool names to their Python implementations.
TOOL_IMPLEMENTATIONS = {
    "execute_shell_command": execute_shell_command,
    "run_interactive_program": run_interactive_program,
}


# --------------------------------------------------------------------------- #
# Configuration loading
# --------------------------------------------------------------------------- #

def resolve_config(args):
    """Merge `.env`, provider defaults, and CLI arguments into a config dict."""
    # Load a `.env` from the current directory first (project-local config wins),
    # then fall back to the `.env` next to this script. load_dotenv does not
    # override already-set variables, so a global launcher still finds its config.
    load_dotenv()
    script_env = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    load_dotenv(script_env)

    provider = (args.provider or os.getenv("SHELLBRAIN_PROVIDER") or "llamacpp").lower()
    if provider not in PROVIDER_DEFAULTS:
        print_colored(
            f"Error: unknown provider '{provider}'. "
            f"Choose one of: {', '.join(PROVIDER_DEFAULTS)}.",
            "RED",
        )
        sys.exit(1)

    defaults = PROVIDER_DEFAULTS[provider]
    prefix = provider.upper()  # OPENAI / LLAMACPP / OLLAMA

    # Precedence for each value: CLI arg > provider-specific env > generic env > default.
    base_url = (
        args.base_url
        or os.getenv(f"{prefix}_BASE_URL")
        or os.getenv("SHELLBRAIN_BASE_URL")
        or defaults["base_url"]
    )
    api_key = (
        args.api_key
        or os.getenv(f"{prefix}_API_KEY")
        or os.getenv("SHELLBRAIN_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or defaults["api_key"]
    )
    model = (
        args.model
        or os.getenv(f"{prefix}_MODEL")
        or os.getenv("SHELLBRAIN_MODEL")
        or defaults["model"]
    )

    if provider == "openai" and not api_key:
        print_colored(
            "Error: no API key for the 'openai' provider. Set OPENAI_API_KEY in "
            ".env or pass --api-key.",
            "RED",
        )
        sys.exit(1)

    return {
        "provider": provider,
        "base_url": base_url,
        "api_key": api_key or "EMPTY",
        "model": model,
    }


def build_client(config):
    """Create an OpenAI SDK client pointed at the configured backend."""
    kwargs = {"api_key": config["api_key"]}
    if config["base_url"]:
        kwargs["base_url"] = config["base_url"]
    return OpenAI(**kwargs)


# --------------------------------------------------------------------------- #
# Conversation
# --------------------------------------------------------------------------- #

def read_instruction_file(file_path):
    """Read an instruction file, creating an empty one if missing."""
    if not os.path.exists(file_path):
        with open(file_path, "w") as handle:
            handle.write("")
        print_colored(f"Instruction file created: {file_path}", "GREEN")
    with open(file_path, "r") as handle:
        return handle.read()


def instruction_file_path(args):
    """Path of the instruction file in effect (default when the flag is absent)."""
    return args.instructionfile or DEFAULT_INSTRUCTION_FILE


def load_instructions(args):
    """Return the instruction text to apply, or an empty string.

    Precedence:
      * ``--instructionfile PATH`` -> that path (created if missing).
      * ``--instructionfile`` (bare) -> the default file (created if missing).
      * flag absent -> the default ``~/AIShellBrain.md`` if it already exists.
    """
    if args.instructionfile:
        return read_instruction_file(args.instructionfile)
    if os.path.exists(DEFAULT_INSTRUCTION_FILE):
        with open(DEFAULT_INSTRUCTION_FILE, "r") as handle:
            return handle.read()
    return ""


def init_conversation_history(args):
    """Build the initial system messages for a new conversation."""
    operating_system = f"{platform.system()} {platform.release()} {platform.version()}"
    history = [
        {
            "role": "system",
            "content": (
                "You are ShellBrain, a helpful assistant that runs shell commands to "
                "accomplish the user's requests. Use the provided tools to execute "
                "commands, then explain the results concisely. "
                "Always reply in the same language the user uses. "
                f"The operating system is: {operating_system}. "
                f"The current working directory is: {os.getcwd()}."
            ),
        }
    ]
    instructions = load_instructions(args)
    if instructions.strip():
        # Keep the instructions in a system message for models that honor it...
        history.append(
            {
                "role": "system",
                "content": (
                    "The following are the user's standing instructions and "
                    "authoritative facts about this system. They OVERRIDE your own "
                    "assumptions and general knowledge. Follow them exactly and never "
                    "contradict them:\n\n" + instructions
                ),
            }
        )
        # ...and also seed them as conversation context. Small local models follow
        # facts stated in the conversation far more reliably than system-prompt facts.
        history.append(
            {
                "role": "user",
                "content": (
                    "Remember these facts and rules for the whole session and apply "
                    "them whenever relevant:\n\n" + instructions
                ),
            }
        )
        history.append({"role": "assistant", "content": "OK."})
    return history


def confirm_command(command, args):
    """Ask the user to confirm a command. Return True to proceed."""
    is_dangerous = any(command.strip().startswith(cmd) for cmd in DANGEROUS_COMMANDS)

    if is_dangerous and not args.yy:
        answer = input(
            f"{COLORS['RED']}WARNING: '{command}' is potentially dangerous. "
            f"Execute it? (y/n): {COLORS['RESET']}"
        )
        return answer.strip().lower() == "y"

    if not args.y and not is_dangerous:
        answer = input(
            f"{COLORS['YELLOW']}Execute the command:{COLORS['RESET']} "
            f"'{command}'? (y/n): "
        )
        return answer.strip().lower() == "y"

    return True


def handle_tool_calls(tool_calls, history, args):
    """Execute a batch of tool calls and append their results to `history`.

    `tool_calls` is a list of dicts with "id", "name" and "arguments" keys, as
    reassembled from the streamed response. Returns True if at least one command
    actually ran (used for the empty-input "explain the last result" shortcut).
    """
    executed = False
    for tool_call in tool_calls:
        name = tool_call["name"]
        try:
            arguments = json.loads(tool_call["arguments"] or "{}")
        except json.JSONDecodeError:
            arguments = {}
        command = arguments.get("command", "")

        if not confirm_command(command, args):
            print_colored("Command execution cancelled.", "YELLOW")
            history.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": "The user cancelled this command.",
                }
            )
            continue

        implementation = TOOL_IMPLEMENTATIONS.get(name, execute_shell_command)
        output = implementation(command)
        executed = True

        history.append(
            {
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": truncate_string(output),
            }
        )
    return executed


def chat_turn(client, config, history, args):
    """Run a model response and execute any commands it requests.

    By default the command output is shown to the user but NOT sent back to the
    model: the function returns True so the caller knows an explanation can be
    requested by pressing Enter. With ``--auto-explain`` the model keeps looping
    over the tool results until it produces a final natural-language answer.

    Returns True if a command was executed whose output has not been explained.
    """
    max_iterations = MAX_TOOL_ITERATIONS if args.auto_explain else 1
    for _ in range(max_iterations):
        try:
            stream = client.chat.completions.create(
                model=config["model"],
                messages=history,
                tools=TOOLS,
                tool_choice="auto",
                stream=True,
            )
        except Exception as exc:  # noqa: BLE001 - surface API/connection errors nicely
            print_colored(f"Error calling the model: {exc}", "RED")
            return False

        content_parts = []
        tool_calls_acc = {}  # index -> {"id", "name", "arguments"}
        printer = StreamingMarkdownPrinter(base_color="LIGHT_YELLOW")
        streamed_content = False
        try:
            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta is None:
                    continue
                # Final natural-language answer: print it token by token.
                if delta.content:
                    printer.feed(delta.content)
                    content_parts.append(delta.content)
                    streamed_content = True
                # Tool calls arrive as fragments that must be reassembled.
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index if tc.index is not None else 0
                        entry = tool_calls_acc.setdefault(
                            idx, {"id": None, "name": "", "arguments": ""}
                        )
                        if tc.id:
                            entry["id"] = tc.id
                        if tc.function:
                            if tc.function.name:
                                entry["name"] += tc.function.name
                            if tc.function.arguments:
                                entry["arguments"] += tc.function.arguments
        except Exception as exc:  # noqa: BLE001 - surface streaming errors nicely
            print_colored(f"\nError while streaming the response: {exc}", "RED")
            return False
        finally:
            if streamed_content:
                printer.flush()

        # Assemble the accumulated tool calls in a stable order.
        tool_calls = []
        for idx in sorted(tool_calls_acc):
            entry = tool_calls_acc[idx]
            if not entry["id"]:
                entry["id"] = f"call_{idx}"
            tool_calls.append(entry)

        # Record the assistant turn (with any tool calls) in the history.
        assistant_entry = {"role": "assistant", "content": "".join(content_parts)}
        if tool_calls:
            assistant_entry["tool_calls"] = [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {"name": tc["name"], "arguments": tc["arguments"]},
                }
                for tc in tool_calls
            ]
        history.append(assistant_entry)

        if tool_calls:
            executed = handle_tool_calls(tool_calls, history, args)
            if args.auto_explain:
                # Loop back so the model reacts to the output automatically.
                continue
            # Default: stop here. The output was shown but not sent to the model;
            # pressing Enter will request an explanation. `executed` is False when
            # every command was cancelled, so there is nothing to explain.
            return executed

        # No tool calls: the final answer has already been streamed.
        return False

    print_colored(
        f"Reached the tool-call limit ({MAX_TOOL_ITERATIONS}). Stopping this turn.",
        "RED",
    )
    return False


# --------------------------------------------------------------------------- #
# Main loop
# --------------------------------------------------------------------------- #

def parse_args():
    parser = argparse.ArgumentParser(
        description="ShellBrain - AI-powered interactive shell (OpenAI / llama.cpp / Ollama)."
    )
    parser.add_argument(
        "--provider",
        choices=list(PROVIDER_DEFAULTS),
        help="Backend to use. Overrides SHELLBRAIN_PROVIDER in .env.",
    )
    parser.add_argument("--model", help="Model name. Overrides the .env model.")
    parser.add_argument("--base-url", help="OpenAI-compatible base URL. Overrides .env.")
    parser.add_argument("--api-key", help="API key. Overrides .env.")
    parser.add_argument(
        "--forget",
        action="store_true",
        help="Do not keep conversation context between inputs.",
    )
    parser.add_argument(
        "--auto-explain",
        action="store_true",
        help=(
            "Automatically send each command's output back to the model so it "
            "explains/chains results. By default the output is only sent when you "
            "press Enter on an empty line right after the command."
        ),
    )
    parser.add_argument(
        "-y",
        action="store_true",
        help="Execute non-dangerous commands without confirmation.",
    )
    parser.add_argument(
        "--yy",
        action="store_true",
        help="Execute even dangerous commands without confirmation.",
    )
    parser.add_argument(
        "--instructionfile",
        nargs="?",
        const=DEFAULT_INSTRUCTION_FILE,
        help=(
            "Path to a file with standing instructions for the assistant. "
            f"When omitted, {DEFAULT_INSTRUCTION_FILE} is loaded automatically if "
            "it exists."
        ),
    )
    return parser.parse_args()


def main():
    args = parse_args()
    config = resolve_config(args)
    client = build_client(config)

    print_colored(f"{APP_NAME} ready.", "LIGHT_WHITE")
    print_colored(
        f"Provider: {config['provider']} | Model: {config['model']}"
        + (f" | URL: {config['base_url']}" if config["base_url"] else ""),
        "CYAN",
    )
    if args.auto_explain:
        print_colored("Type your request, 'clear' to reset, or 'exit' to quit.", "CYAN")
    else:
        print_colored(
            "Type your request. After a command, press Enter to have the output "
            "explained. 'clear' to reset, 'exit' to quit.",
            "CYAN",
        )

    history = init_conversation_history(args)
    if load_instructions(args).strip():
        print_colored(f"Instructions loaded from {instruction_file_path(args)}.", "GREEN")

    history_file = os.path.join(os.path.expanduser("~"), ".shellbrain_history")
    session = PromptSession(history=FileHistory(history_file))

    pending_explanation = False
    while True:
        try:
            user_input = session.prompt(f"{APP_NAME}:{os.getcwd()}> ")

            if user_input == "":
                if pending_explanation:
                    # Empty line right after a command: send the output to the
                    # model for an explanation by letting it continue from the
                    # tool results already in the history. Injecting no prompt
                    # keeps the reply in the user's language and honors the
                    # standing instructions.
                    pending_explanation = chat_turn(client, config, history, args)
                continue

            command = user_input.strip().lower()
            if command == "exit":
                break
            if command in ("clear", "cls"):
                print_colored("Conversation history cleared.", "GREEN")
                history = init_conversation_history(args)
                pending_explanation = False
                continue

            # In --forget mode, start a fresh context for each new request.
            if args.forget:
                history = init_conversation_history(args)

            history.append({"role": "user", "content": user_input})
            pending_explanation = chat_turn(client, config, history, args)

        except KeyboardInterrupt:
            continue
        except EOFError:
            break

    print_colored("Goodbye!", "LIGHT_WHITE")


if __name__ == "__main__":
    main()
