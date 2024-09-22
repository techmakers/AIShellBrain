import openai
import subprocess
import json
import time
import sys
import os
import argparse
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
import shlex
import platform
import shutil

# ANSI color codes
COLORS = {
    'RED': '\033[91m',
    'GREEN': '\033[92m',
    'YELLOW': '\033[93m',
    'BLUE': '\033[94m',
    'MAGENTA': '\033[95m',
    'CYAN': '\033[96m',
    'LIGHT_CYAN': '\033[96;1m',
    'WHITE': '\033[97m',
    'RESET': '\033[0m'
}

# Function to print colored text
def print_colored(text, color='WHITE'):
    color_code = COLORS.get(color.upper(), COLORS['WHITE'])
    print(f"{color_code}{text}{COLORS['RESET']}")

# Function to execute interactive programs
def interactive_programs(command):
    # Print message about interactive program execution
    print_colored("Interactive program detected. Launching...", 'YELLOW')
    os.system(command)
    print_colored("Interactive program closed. Returning to script.", 'YELLOW')
    return "Interactive program execution completed."

# Function to execute a shell command and return its output
def execute_shell_command(command):
    try:
        # Print the command that will be executed
        print_colored(f"\nExecuting command: {command}", 'GREEN')
        
        # Check if the command is a cd command
        if command.strip().startswith('cd'):
            # Extract the directory path
            new_dir = command.strip()[3:].strip()
            try:
                os.chdir(new_dir)
                print_colored(f"Changed directory to: {os.getcwd()}", 'GREEN')
                return f"Changed directory to: {os.getcwd()}"
            except FileNotFoundError:
                print_colored(f"Directory not found: {new_dir}", 'RED')
                return f"Error: Directory not found: {new_dir}"
            except PermissionError:
                print_colored(f"Permission denied: {new_dir}", 'RED')
                return f"Error: Permission denied: {new_dir}"
        
        # Check if the command is an interactive program
        interactive_programs_list = ['nano', 'vim', 'emacs', 'less', 'more']
        command_parts = command.split()
        if command_parts and command_parts[0] in interactive_programs_list:
            print_colored("Interactive program detected (force). Launching...", 'YELLOW')
            return interactive_programs(command)

        # For non-interactive commands, use subprocess with real-time output
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, universal_newlines=True)

        output = []
        # Loop to read both stdout and stderr
        while True:
            stdout_line = process.stdout.readline()
            stderr_line = process.stderr.readline()
            
            if not stdout_line and not stderr_line and process.poll() is not None:
                break
            
            if stdout_line:
                print(stdout_line.strip())
                output.append(stdout_line.strip())
            if stderr_line:
                print_colored(stderr_line.strip(), 'RED')
                output.append(stderr_line.strip())

        # Ensure all remaining output is captured
        remaining_stdout, remaining_stderr = process.communicate()
        if remaining_stdout:
            print(remaining_stdout.strip())
            output.append(remaining_stdout.strip())
        if remaining_stderr:
            print_colored(remaining_stderr.strip(), 'RED')
            output.append(remaining_stderr.strip())

        if process.returncode == 0:
            return "\n".join(output)
        else:
            return f"Error: Command exited with status {process.returncode}\n" + "\n".join(output)
    except Exception as e:
        return f"Error in execution: {str(e)}"

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Interactive shell with OpenAI integration")
    parser.add_argument("--keep", action="store_true", help="Keep conversation context")
    parser.add_argument("-y", action="store_true", help="Execute commands without confirmation")
    parser.add_argument("--api-key", help="OpenAI API key")
    args = parser.parse_args()

    # Get the OpenAI API key
    api_key = args.api_key or os.environ.get('OPENAI_API_KEY')
    if not api_key:
        print_colored("Error: OpenAI API key not provided. Please use --api-key or set the OPENAI_API_KEY environment variable.", 'RED')
        sys.exit(1)

    # Initialize OpenAI API with the API key
    openai.api_key = api_key

    # Identify the operating system
    operating_system = platform.system()

    # Create a PromptSession with FileHistory
    session = PromptSession(history=FileHistory('.command_history'))

    # Initialize conversation history with OS details
    conversation_history = [
        {"role": "system", "content": f"You are a helpful assistant that can execute shell commands and provide information. The operating system is {operating_system}."}
    ]
    
    if args.keep:
        conversation_history.append({"role": "system", "content": "You will retain conversation context across interactions."})

    while True:
        try:
            # Use prompt_toolkit to get user input with history
            user_input = session.prompt(f"\n{os.getcwd()}> ")

            if user_input.lower() == 'exit':
                break

            # Add user input to conversation history if --keep is enabled
            if args.keep:
                conversation_history.append({"role": "user", "content": user_input})

            # Prepare messages for OpenAI API
            messages = conversation_history if args.keep else [{"role": "user", "content": user_input}]

            # Call OpenAI API to get the shell command
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=messages,
                functions=[
                    {
                        "name": "execute_shell_command",
                        "description": "Execute a shell command and return the output",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "command": {
                                    "type": "string",
                                    "description": "The shell command to execute"
                                }
                            },
                            "required": ["command"]
                        }
                    },
                    {
                        "name": "interactive_programs",
                        "description": "Execute an interactive program",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "command": {
                                    "type": "string",
                                    "description": "The interactive program command to execute"
                                }
                            },
                            "required": ["command"]
                        }
                    }
                ],
                function_call="auto"
            )

            # Check if a function call was made in the response
            if 'choices' in response and 'function_call' in response['choices'][0]['message']:
                function_call = response['choices'][0]['message']['function_call']
                
                # Parse the JSON string to a dictionary
                arguments = json.loads(function_call['arguments'])
                command_to_execute = arguments['command']
                
                # Ask for confirmation if -y flag is not set
                if not args.y:
                    confirmation = input(f"Do you want to execute the command: '{command_to_execute}'? (y/n): ")
                    if confirmation.lower() != 'y':
                        print_colored("Command execution cancelled.", 'YELLOW')
                        continue

                # Determine the appropriate function to call
                if function_call['name'] == 'interactive_programs':
                    output = interactive_programs(command_to_execute)
                else:
                    output = execute_shell_command(command_to_execute)

                # Print the output
                print(output)

                # Add assistant's response and command output to conversation history if --keep is enabled
                if args.keep:
                    conversation_history.append({"role": "assistant", "content": f"Executed command: {command_to_execute}\nOutput: {output}"})
            else:
                # If no function call was made, print the OpenAI response
                print_colored("OpenAI response:", 'YELLOW')
                if 'choices' in response and 'content' in response['choices'][0]['message']:
                    assistant_response = response['choices'][0]['message']['content']
                    print_colored(assistant_response, 'LIGHT_CYAN')
                    if args.keep:
                        conversation_history.append({"role": "assistant", "content": assistant_response})
                else:
                    print_colored("No text response available.", 'RED')

        except KeyboardInterrupt:
            continue
        except EOFError:
            break

if __name__ == "__main__":
    main()
