import subprocess
import json
import time
import sys
import os
import argparse
import requests
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory

# ANSI color codes
COLORS = {
    'RED': '\033[91m',
    'GREEN': '\033[92m',
    'YELLOW': '\033[93m',
    'BLUE': '\033[94m',
    'MAGENTA': '\033[95m',
    'CYAN': '\033[96m',
    'LIGHT_CYAN': '\033[96;1m',  # Light Cyan and Bold
    'WHITE': '\033[97m',
    'RESET': '\033[0m'
}

def process_response(response):
    if "EXECUTE:" in response:
        # Extract only the command part, remove extra spaces and backticks
        command_parts = response.split("EXECUTE:")
        command = command_parts[-1].strip()
        command = command.replace('`', '').strip()
        return f"EXECUTE: {command}"
    return response.strip()

# Nel ciclo principale:



# Function to print colored text
def print_colored(text, color='WHITE'):
    color_code = COLORS.get(color.upper(), COLORS['WHITE'])
    print(f"{color_code}{text}{COLORS['RESET']}")

# Function to execute a shell command and return its output
def execute_shell_command(command):
    try:
        # Print the command that will be executed
        print_colored(f"\nExecuting command: {command}", 'GREEN')
        print_colored("Starting execution...", 'GREEN')

        # Check if the command is an interactive program
        interactive_programs = ['nano', 'vim', 'emacs', 'less', 'more']
        command_parts = command.split()
        if command_parts and command_parts[0] in interactive_programs:
            print_colored("Interactive program detected. Launching...", 'YELLOW')
            os.system(command)
            print_colored("Interactive program closed. Returning to script.", 'YELLOW')
            return "Interactive program execution completed."

        # For non-interactive commands, use subprocess
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        # Print dots while the command is running
        while process.poll() is None:
            sys.stdout.write(f"{COLORS['GREEN']}.{COLORS['RESET']}")
            sys.stdout.flush()
            time.sleep(0.5)

        # Get the output
        stdout, stderr = process.communicate()

        print_colored("\nExecution completed.", 'GREEN')

        if process.returncode == 0:
            return stdout
        else:
            return f"Error: {stderr}"
    except Exception as e:
        return f"Error in execution: {str(e)}"

# Function to call Ollama API
def call_ollama(messages):
    url = "http://localhost:11434/api/chat"
    data = {
##        "model": "llama3.1:latest",
        "model": "mistral:latest",
##        "model": "phi3:mini",
        "messages": messages,
        "stream": False
    }
    
    response = requests.post(url, json=data)
    if response.status_code == 200:
        return response.json()['message']['content']
    else:
        return f"Error: Unable to get response from Ollama. Status code: {response.status_code}"

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Interactive shell with Ollama integration")
    parser.add_argument("--keep", action="store_true", help="Keep conversation context")
    args = parser.parse_args()

    # Create a PromptSession with FileHistory
    session = PromptSession(history=FileHistory('.command_history'))

    # Initialize conversation history
    conversation_history = []
    system_prompt = """You are a helpful assistant that can execute shell commands and provide information. Follow these rules strictly:
    1. If the user asks to execute a command or perform an action that requires a shell command, respond ONLY with the exact command to run, prefixed with 'EXECUTE: '.
    2. Do not add any explanations, spaces, or special characters (like backticks) when providing a command.
    3. For other queries that don't require command execution, provide a concise helpful response.
    4. If you're unsure whether a query requires a command, ask for clarification without suggesting any commands.
    5. Never combine explanations with commands in the same response.
    6. For system information queries, always respond with the appropriate command to retrieve that information.
    7. Ensure that the command immediately follows 'EXECUTE:' without any spaces in between."""


    # In the main function:
    if args.keep:
        conversation_history.append({"role": "system", "content": system_prompt})

    while True:
        try:
            # Use prompt_toolkit to get user input with history
            user_input = session.prompt("\nEnter a command or 'exit' to terminate: ")

            if user_input.lower() == 'exit':
                break

            # Add user input to conversation history if --keep is enabled
            if args.keep:
                conversation_history.append({"role": "user", "content": user_input})

            # Prepare messages for Ollama API
            messages = conversation_history if args.keep else [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_input}]
            
            # Call Ollama API
            response = process_response(call_ollama(messages))

            # Check if the response is a command to execute
            if response.startswith("EXECUTE: "):
                command_to_execute = response[8:].strip()  # Remove "EXECUTE: " prefix
                output = execute_shell_command(command_to_execute)

                # Print the output
                print_colored("\nCommand result:", 'GREEN')
                print(output)  # This will be printed in the default color

                # Add assistant's response and command output to conversation history if --keep is enabled
                if args.keep:
                    conversation_history.append({"role": "assistant", "content": f"Executed command: {command_to_execute}\nOutput: {output}"})
            else:
                # If no command to execute, print the Ollama response
                print_colored("\nOllama response:", 'CYAN')
                print_colored(response, 'LIGHT_CYAN')  # Print Ollama's text response in light cyan and bold

                # Add assistant's response to conversation history if --keep is enabled
                if args.keep:
                    conversation_history.append({"role": "assistant", "content": response})

        except KeyboardInterrupt:
            continue
        except EOFError:
            break

if __name__ == "__main__":
    main()