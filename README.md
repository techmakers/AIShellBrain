# AI-Powered Interactive Shell

This Python script provides an AI-powered interactive shell that integrates with OpenAI's GPT models to execute shell commands and provide information.

## Features

- Execute shell commands using natural language input
- Maintain conversation context across multiple interactions
- Change directories and persist the change for subsequent commands
- Confirm command execution for added safety
- Colorized output for better readability
- Command history support
- OpenAI API key management via command line or environment variable

## Requirements

- Python 3.6+
- OpenAI Python library
- prompt_toolkit library

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/ai-powered-shell.git
   cd ai-powered-shell
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
python ai_shellbrain.py [options]
```

### Command-line Options

- `--keep`: Maintain conversation context across multiple interactions
- `-y`: Execute commands without confirmation
- `--api-key KEY`: Specify the OpenAI API key (alternative to environment variable)

### Examples

1. Run with conversation context and command confirmation:
   ```
   python ai_shellbrain.py --keep
   ```

2. Run without command confirmation:
   ```
   python ai_shellbrain.py -y
   ```

3. Specify API key via command line:
   ```
   python ai_shellbrain.py --api-key YOUR_API_KEY
   ```

## How It Works

1. The script prompts for user input.
2. The input is sent to OpenAI's API to generate a shell command or provide information.
3. If a command is generated, the user is asked for confirmation (unless `-y` is used).
4. The command is executed, and the output is displayed.
5. The process repeats until the user exits.

## Safety and Permissions

- The script runs commands with the same permissions as the user running the script.
- Always review commands before confirming execution.
- Use the `-y` option with caution, as it bypasses command confirmation.

## Contributing

Contributions, issues, and feature requests are welcome. Feel free to check [issues page](https://github.com/yourusername/ai-powered-shell/issues) if you want to contribute.

## License

[MIT](https://choosealicense.com/licenses/mit/)

