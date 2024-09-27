# AI-Powered Interactive Shell

This Python script provides an AI-powered interactive shell that integrates with OpenAI's GPT models to execute shell commands and provide information.

## Features

- Execute shell commands using natural language input.
- Maintain conversation context across multiple interactions unless specified otherwise.
- Change directories and persist the change for subsequent commands.
- Confirm command execution for added safety.
- Colorized output for better readability.
- Command history support.
- OpenAI API key management via command line or environment variable.
- Option to specify a different GPT model.
- Explanation of the last output by pressing the enter key.
- Read additional instructions from a specified file.
- Automatically create the instruction file if it does not exist.
- Use a default instruction file `AIShellBrain.md` in the user's home directory if no file is specified.

## Requirements

- Python 3.6+
- OpenAI Python library
- prompt_toolkit library

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/techmakers/AIShellBrain.git
   cd AIShellBrain
   ```

2. Install the required packages:
   ```
   pip install openai prompt_toolkit
   ```

3. Set up your OpenAI API key (choose one method):
   - Set an environment variable:
     ```
     export OPENAI_API_KEY='your-api-key-here'
     ```
   - Or, prepare to pass it as a command-line argument when running the script

## Usage

Run the script with:

```
python AIShellBrain.py [options]
```

### Command-line Options

- `--forget`: Do not maintain conversation context across multiple interactions.
- `-y`: Execute commands without confirmation except for "rm", "del" etc.
- `--yy`: Execute commands without confirmation.
- `--api-key KEY`: Specify the OpenAI API key (alternative to environment variable).
- `--model MODEL_NAME`: Force the use of a different GPT model instead of the default "gpt-4o-mini".
- `--instructionfile [FILE_PATH]`: Path to a file with additional instructions for the assistant. If the file does not exist, it will be created. If the flag is present but no file is specified, the default `AIShellBrain.md` in the user's home directory is used.

### Examples

1. Run maintaining conversation context with command confirmation:
   ```
   python AIShellBrain.py
   ```

2. Run without conversation context and with command confirmation:
   ```
   python AIShellBrain.py --forget
   ```

3. Run without command confirmation:
   ```
   python AIShellBrain.py --y
   ```

4. Specify API key via command line:
   ```
   python AIShellBrain.py --api-key YOUR_API_KEY
   ```

5. Use a different GPT model, default is gpt-4o-mini:
   ```
   python AIShellBrain.py --model gpt-3.5-turbo
   ```

6. Use a specific instruction file:
   ```
   python AIShellBrain.py --instructionfile /path/to/instructionfile.md
   ```

7. Use the default instruction file `AIShellBrain.md` in the user's home directory:
   ```
   python AIShellBrain.py --instructionfile
   ```

## How It Works

1. The script prompts for user input.
2. The input is sent to OpenAI's API to generate a shell command or provide information.
3. If a command is generated, the user is asked for confirmation (unless `--yy` is used).
4. The command is executed, and the output is displayed.
5. The process repeats until the user exits.

## Safety and Permissions

- The script runs commands with the same permissions as the user running the script.
- Always review commands before confirming execution.
- Use the `--yy` option with caution, as it bypasses command confirmation.

## Contributing

Contributions, issues, and feature requests are welcome. Feel free to check the [issues page](https://github.com/techmakers/AIShellBrain/issues) if you want to contribute.

## License

See LICENCE.txt

## Author

Techmakers srl - Alessandro Vernassa
