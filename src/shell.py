import sys
import asyncio
import readline
from dataclasses import dataclass
from config import Configuration


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


class CompletionEngine:
    configuration: Configuration

    def __init__(self, configuration: Configuration):
        self.configuration = configuration

    def __call__(self, text: str, state):
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
                for arg in self.configuration.tasks.keys()
                if arg.startswith(text)
            ]

        if state < len(matches):
            return matches[state]
        else:
            return None

async def connect_stdin_stdout() -> (asyncio.StreamReader, asyncio.StreamWriter):
    loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)
    w_transport, w_protocol = await loop.connect_write_pipe(
            asyncio.streams.FlowControlMixin, sys.stdout)
    writer = asyncio.StreamWriter(w_transport, w_protocol, reader, loop)
    return reader, writer


def setup(configuration: Configuration):
    completion_engine = CompletionEngine(configuration)

    readline.set_completer(completion_engine)
    readline.parse_and_bind("tab: complete")


async def run(configuration: Configuration):
    setup(configuration)
    # reader, writer = await connect_stdin_stdout()

    # writer.write(b"Welcome to Taskmaster Shell!
    # Type 'help' for a list of commands.")
    while True:
        # writer.write((
        #     Colors.YELLOW +
        #     "🔧 Taskmaster\n   ⤷ " +
        #     Colors.RESET
        # ).encode())
        # await writer.drain()
        try:
            # command_line = (await reader.read()).strip().lower()
            # TODO: make async
            # command_line = sys.stdin.readline()
            command_line = input(
                Colors.YELLOW +
                "🔧 Taskmaster\n   ⤷ " +
                Colors.RESET,
            )

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
                # writer.write(
                #     "Unknown command\n."
                #     "Available commands: "
                #     "status, start, stop, restart, reload, exit."
                # )
                # await writer.drain()

        except KeyboardInterrupt:
            print("\nExiting Taskmaster.")
            # writer.write("\nExiting Taskmaster.")
            # await writer.drain()
            break

    readline.write_history_file(history_file)
