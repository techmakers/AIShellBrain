# This script was created by Alessandro Vernassa
# It provides an interactive interface to communicate with an AI model
# using the OpenAI API.
# puoi monitorare l'uso della cpu ogni 5 minuti per un ora?

from openai import OpenAI
import subprocess
import json
import sys
import os
import argparse
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
import platform

# ANSI color codes
COLORS = {
    'RED': '\033[91m',
    'GREEN': '\033[92m',
    'LIGHT_GREEN': '\033[92;1m',
    'YELLOW': '\033[93m',
    'LIGHT_YELLOW': '\033[93;1m',
    'BLUE': '\033[94m',
    'MAGENTA': '\033[95m',
    'CYAN': '\033[96m',
    'LIGHT_CYAN': '\033[96;1m',
    'LIGHT_WHITE': '\033[97;1m',
    'WHITE': '\033[97m',
    'RESET': '\033[0m'
}
conversation_history = []

# List of potentially dangerous commands
dangerous_commands = ['rm', 'rmdir', 'del', 'erase', 'rd']

# Function to print colored text
def print_colored(text, color='WHITE'):
    color_code = COLORS.get(color.upper(), COLORS['WHITE'])
    print(f"{color_code}{text}{COLORS['RESET']}")

def markdown_to_ansi(markdown_text):
    # Simple translation from markdown to ANSI codes
    import re
    
    # Regular expression patterns for markdown
    bold_pattern = r'\*\*(.*?)\*\*'  # Matches **bold**
    italic_pattern = r'\*(.*?)\*'    # Matches *italic*
    header_pattern = r'^(#+) (.*)'   # Matches headers like # Header

    # ANSI escape sequences
    ansi_bold = '\033[1m'
    ansi_italic = '\033[3m'
    ansi_reset = '\033[0m'

    # Function to convert headers
    def convert_header(match):
        header_level = len(match.group(1))
        header_text = match.group(2)
        # Convert header level to bold
        return f"{ansi_bold}{header_text}{ansi_reset}\n"

    # Convert markdown to ANSI
    ansi_text = markdown_text

    # Replace markdown headers with ANSI
    ansi_text = re.sub(header_pattern, convert_header, ansi_text, flags=re.MULTILINE)

    # Replace markdown bold with ANSI
    ansi_text = re.sub(bold_pattern, lambda m: f"{ansi_bold}{m.group(1)}{ansi_reset}", ansi_text)

    # Replace markdown italic with ANSI
    ansi_text = re.sub(italic_pattern, lambda m: f"{ansi_italic}{m.group(1)}{ansi_reset}", ansi_text)

    return ansi_text

# Function to execute interactive programs
def interactive_programs(command):
    # Print message about interactive program execution
    print_colored(f"Launching: {command}", 'LIGHT_YELLOW')
    if True :
        os.system(command)
        return False
    else :
        result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,bufsize=-1)
        print_colored("Interactive program closed. Returning to script.", 'YELLOW')
        ret = ""
        if result.stdout != "" or result.stderr != "" :
            ret = f"stdout:{result.stdout} stderr:{result.stderr}"
        return ret


import os
import subprocess



def execute_shell_command(command):
    try:
        print_colored(f"Executing: {command}", 'LIGHT_GREEN')

        # Split the command by '&&' to handle multiple commands
        command_parts = command.split('&&')
        output = []
        for part in command_parts:
            part = part.strip()  # Remove any leading/trailing whitespace
            if part.startswith('cd'):
                # Handle 'cd' command separately
                new_dir = part[3:].strip()
                try:
                    os.chdir(new_dir)
                    print_colored(f"Changed directory to: {os.getcwd()}", 'GREEN')
                    output.append(f"Changed directory to: {os.getcwd()}")
                except FileNotFoundError:
                    print_colored(f"Directory not found: {new_dir}", 'RED')
                    output.append(f"Error: Directory not found: {new_dir}")
                except PermissionError:
                    print_colored(f"Permission denied: {new_dir}", 'RED')
                    output.append(f"Error: Permission denied: {new_dir}")
            else:
                # Check if the command is an interactive program
                interactive_programs_list = ['nano', 'vim', 'emacs', 'less', 'more','vi','htop']
                command_parts = command.split()
                if command_parts and command_parts[0] in interactive_programs_list:
                    print_colored("Interactive program detected (force). Launching...", 'YELLOW')
                    return interactive_programs(command)
                # Execute non-'cd' commands
                process = subprocess.Popen(part, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=-1, universal_newlines=True)
                
                while True:
                    stderr_line = ""
                    stdout_line = process.stdout.readline()
                    # next line have a problem with:  find ~/Desktop -type f \( -iname '*.png' -o -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.gif' \)
                    #if (process.stderr.readable()):
                    #    stderr_line = process.stderr.readline(1024)
                    if stdout_line:
                        print(stdout_line.strip())
                        output.append(stdout_line.strip())
                    if stderr_line:
                        print_colored(stderr_line.strip(), 'RED')
                        output.append(stderr_line.strip())
                    if not stdout_line and not stderr_line and process.poll() is not None:
                        break

                remaining_stdout, remaining_stderr = process.communicate()
                if remaining_stdout:
                    print(remaining_stdout.strip())
                    output.append(remaining_stdout.strip())
                if remaining_stderr:
                    print_colored(remaining_stderr.strip(), 'RED')
                    output.append(remaining_stderr.strip())

                if process.returncode != 0:
                    print_colored(f"Error: Command exited with status {process.returncode}", 'RED')
                    output.append(f"Error: Command exited with status {process.returncode}")
        return "\n".join(output)
    except Exception as e:
        return f"Error in execution: {str(e)}"

def init_conversation_history (args):
    # Identify the operating system
    operating_system = platform.system() + " " + platform.release() + " " + platform.version()
    # Initialize conversation history with OS details
    conversation_history = [
        {"role": "system", "content": f"You are a helpful assistant that can execute shell commands and provide information. The operating system is {operating_system}."}
    ]
    # Handle instruction file if provided
    if args.instructionfile:
        instruction_file_path = args.instructionfile
        instructions = read_instruction_file(instruction_file_path)
        if instructions:
            conversation_history.append({"role": "system", "content": instructions})

    return conversation_history

def truncate_string(input_string):
    input_string = str(input_string)
    # Define the maximum length allowed for the string
    max_length = 2000
    
    # Check if the string needs to be truncated
    if len(input_string) > max_length:
        # Truncate the string to the first 2000 characters and add "..." at the end
        return input_string[:max_length] + "(TRUNCATED)"
    else:
        # Return the string as is if no truncation is needed
        return input_string


def read_instruction_file(file_path):
    # Check if the file exists; if not, create it
    if not os.path.exists(file_path):
        with open(file_path, 'w') as file:
            file.write("")
        print_colored(f"Instruction file created: {file_path}", 'GREEN')
    
    # Read the content of the file
    with open(file_path, 'r') as file:
        instructions = file.read()
    
    # If the file is empty, provide default instructions
    if not instructions:
        instructions = ""
    
    return instructions

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Interactive shell with OpenAI integration")
    parser.add_argument("--forget", action="store_true", help="Forget conversation context after each interaction")
    parser.add_argument("-y", action="store_true", help="Execute commands without confirmation")
    parser.add_argument("--yy", action="store_true", help="Execute even dangerous commands without confirmation")
    parser.add_argument("--api-key", help="OpenAI API key")
    parser.add_argument("--model", default="gpt-4o-mini", help="Specify a different OpenAI model to use (default: gpt-4o-mini)")
    parser.add_argument("--instructionfile", nargs='?', const=os.path.join(os.path.expanduser('~'), 'AIShellBrain.md'), help="Path to a file with additional instructions for the assistant")
    args = parser.parse_args()

    # Get the OpenAI API key
    api_key = args.api_key or os.environ.get('OPENAI_API_KEY')
    if not api_key:
        print_colored("Error: OpenAI API key not provided. Please use --api-key or set the OPENAI_API_KEY environment variable.", 'RED')
        sys.exit(1)
    
    client = OpenAI(api_key=api_key)

    conversation_history = init_conversation_history(args)

    
    # Create a PromptSession with FileHistory
    home_directory = os.path.expanduser('~')
    history_file_path = os.path.join(home_directory, '.command_history')
    session = PromptSession(history=FileHistory(history_file_path))
    executed_command = False
    while True:
        try:
            # Use prompt_toolkit to get user input with history
            user_input = session.prompt(f"AIShellBrain:{os.getcwd()}> ")
            if user_input == "":
                if executed_command:
                    user_input = "Describe result using language I used previously"
                else:
                    continue

            if user_input.lower() == 'exit':
                break
            
            if user_input.lower() == 'clear' or user_input.lower() == 'cls':
                print("clear history")
                conversation_history = init_conversation_history(args)
            # Add user input to conversation history if --forget is not enabled
            if not args.forget:
                conversation_history.append({"role": "user", "content": user_input})

            # Prepare messages for OpenAI API
            messages = conversation_history if not args.forget else [{"role": "user", "content": user_input}]
            #print(messages)
            # Call OpenAI API to get the shell command
            response = client.chat.completions.create(
                model=args.model,  # Use the model specified by the user
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
                                    "description": "The interactive program command to execute, such as 'text editors', 'programs with graphical interface', and any other interactive applications that do not produce direct output to the console."
                                }
                            },
                            "required": ["command"]
                        }
                    }
                ],
                function_call="auto"
            )
            # Check if a function call was made in the response
            if hasattr(response, 'choices') and len(response.choices) > 0 and hasattr(response.choices[0].message, 'function_call') and response.choices[0].message.function_call is not None:
                function_call = response.choices[0].message.function_call
                # Parse the JSON string to a dictionary
                arguments = json.loads(function_call.arguments)
                command_to_execute = arguments['command']
                
                # Check for dangerous commands
                is_dangerous = any(command_to_execute.strip().startswith(cmd) for cmd in dangerous_commands)
                
                # Ask for confirmation for dangerous commands unless --yy is set
                if is_dangerous and not args.yy:
                    confirmation = input(f"Warning: The command '{command_to_execute}' is potentially dangerous. Do you want to execute it? (y/n): ")
                    if confirmation.lower() != 'y':
                        print_colored("Command execution cancelled.", 'YELLOW')
                        continue
                
                # Ask for confirmation if -y flag is not set
                if not args.y and not is_dangerous:
                    confirmation = input(f"{COLORS['YELLOW']}Do you want to execute the command:{COLORS['RESET']} '{command_to_execute}'? (y/n): ")
                    if confirmation.lower() != 'y':
                        print_colored("Command execution cancelled.", 'YELLOW')
                        continue

                executed_command = False
                # Determine the appropriate function to call
                if function_call.name == 'interactive_programs':
                    output = interactive_programs(command_to_execute)
                else:
                    output = execute_shell_command(command_to_execute)
                if output :
                    executed_command = True
                # Print the output
                #print(output)

                # Add assistant's response and command output to conversation history if --forget is not enabled
                if not args.forget:
                    output_truncated = truncate_string(output)
                    conversation_history.append({"role": "user", "content": f"return:{output_truncated}"})
            else:
                executed_command = False
                # If no function call was made, print the OpenAI response
                if hasattr(response, 'choices') and len(response.choices) > 0 and hasattr(response.choices[0].message, 'content'):
                    assistant_response = response.choices[0].message.content
                    print_colored(markdown_to_ansi(assistant_response),'LIGHT_YELLOW')
                    if not args.forget:
                        conversation_history.append({"role": "assistant", "content": assistant_response})
                else:
                    print_colored("No text response available.", 'RED')

        except KeyboardInterrupt:
            continue
        except EOFError:
            break

if __name__ == "__main__":
    main()
