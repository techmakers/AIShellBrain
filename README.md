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
python ai_shellbrain.py [options]
```

### Command-line Options

- `--forget`: Do not maintain conversation context across multiple interactions.
- `--y`: Execute commands without confirmation except for "rm", "del" etc
- `--yy`: Execute commands without confirmation.
- `--api-key KEY`: Specify the OpenAI API key (alternative to environment variable).
- `--model MODEL_NAME`: Force the use of a different GPT model instead of the default "gpt-4o-mini".

### Examples

1. Run maintaining conversation context with command confirmation:
   ```
   python ai_shellbrain.py
   ```

2. Run without conversation context and with command confirmation:
   ```
   python ai_shellbrain.py --forget
   ```

3. Run without command confirmation:
   ```
   python ai_shellbrain.py --y
   ```

4. Specify API key via command line:
   ```
   python ai_shellbrain.py --api-key YOUR_API_KEY
   ```

5. Use a different GPT model:
   ```
   python ai_shellbrain.py --model gpt-3.5-turbo
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

[MIT](https://choosealicense.com/licenses/mit/)

## Author

Alessandro Vernassa
