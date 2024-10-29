import readline
from config import configuration
from dataclasses import dataclass


class Colors:
    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"


history_file = "taskmaster_history.txt"


try:
    readline.read_history_file(history_file)
except FileNotFoundError:
    pass


def help():
    print("help")


def status():
    print("Showing status...")


def start_task(task):
    print(f"Starting {task}...")


def stop_task(task):
    print(f"Stopping {task}...")


def restart_task(task):
    print(f"Restarting {task}...")


def reload_config():
    print("Reloading configuration...")


class Command:
    pass


class GlobalCommand:
    pass


class ReloadCommand(GlobalCommand):
    pass


@dataclass
class TaskCommand(Command):
    task_name: str


class StartCommand(TaskCommand):
    pass


class StopCommand(TaskCommand):
    pass


command_dict = {
    "start": start_task,
    "stop": stop_task,
    "restart": restart_task,
    "status": status,
    "reload": reload_config,
    "exit": exit,
    "help": help,
}


def completion(text, state):
    buffer = readline.get_line_buffer()
    cmd_with_args = buffer.split()
    if len(cmd_with_args) <= 1:
        matches = [
            cmd
            for cmd in command_dict.keys()
            if cmd.startswith(text)
        ]
    elif len(cmd_with_args) > 1:
        matches = [
            arg
            for arg in configuration.tasks.keys()
            if arg.startswith(text)
        ]

    print("state, matches", state, len(matches))
    if state < len(matches):
        return matches[state]
    else:
        return None


readline.set_completer(completion)
readline.parse_and_bind("tab: complete")


def main_shell():
    print("Welcome to Taskmaster Shell! Type 'help' for a list of commands.")
    while True:
        try:
            command_line = input(
                Colors.YELLOW +
                "🔧 Taskmaster\n   ⤷ " +
                Colors.RESET
            ).strip().lower()

            if not command_line:
                continue

            cmd, *args = command_line.split()

            if cmd in command_dict:
                if args:
                    command_dict[cmd](args[0])
                else:
                    command_dict[cmd]()
            else:
                print(
                    "Unknown command\n."
                    "Available commands: "
                    "status, start, stop, restart, reload, exit."
                )

        except KeyboardInterrupt:
            print("\nExiting Taskmaster.")
            break

    readline.write_history_file(history_file)
