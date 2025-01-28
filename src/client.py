#!/usr/bin/env python3

import rpc
import grpc
import readline
import platform
from typing import List
HISTORY_FILE  = ".taskmaster_history"

class Colors:
    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
commands = [
    "start",
    "stop",
    "restart",
    "status",
    "reload",
    "list",
    "shutdown",
    "quit",
]

def printError(message: str, arg: [str] = ""):
    print(f"{Colors.RED}{message} {arg}{Colors.RESET}")

class CompletionEngine:
    client: rpc.Client
    def __init__(self, client: rpc.Client):
        self.client = client

    def get_matches(self, prefix: str) -> List[str]:
        return [
            task_name
            for task_name in self.client.list()
            if task_name.startswith(prefix)
        ]

    def get_instance_ids(self, task_name: str, prefix: str) -> List[str]:
        instances = self.client.listInstances(task_name)
        print("instance:", instances)
        return instances

    def __call__(self, text: str, state):
        buffer = readline.get_line_buffer()
        tokens = buffer.split()
        current_token = len(tokens)
        if buffer.endswith(' '):
            current_token += 1

        matches = []
        if current_token <= 1:  # Completing command
            matches = [cmd for cmd in commands if cmd.startswith(text)]
        elif current_token == 2:  # Completing process name
            matches = self.get_matches(text)
        elif current_token == 3:  # Completing instance ID
            if len(tokens) > 1:
                matches = self.get_instance_ids(tokens[1], text)

        if state < len(matches):
            return matches[state]
        else:
            return None

def run(client: rpc.Client):
    setup(client)

    while True:
        try:
            command_line = input(
                Colors.YELLOW + "🔧 Taskmaster\n   ⤷ " + Colors.RESET,
            )

            if not command_line:
                continue

            try:
                tokens = command_line.split()
                match tokens:
                    case ["start", task, *instance_ids]:
                        client.start(task, list(map(int, instance_ids)))
                    case ["stop", task, *instance_ids]:
                        client.stop(task, list(map(int, instance_ids)))
                    case ["restart", task, *instance_ids]:
                        client.restart(task,  list(map(int, instance_ids)))
                    case ["status", task, *instance_ids]:
                        status = client.status(task,  list(map(int, instance_ids)))
                        print(f"Status:\n\t{status}")
                    case ["list"]:
                        for task in client.list():
                            print(task)
                    case ["reload"]:
                        client.reload()
                    case ["shutdown"]:
                        client.shutdown()
                    case ["quit"]:
                        break
                    case _:
                       printError("Invalid command:", command_line)
            except grpc.RpcError:
                printError("Server is not responding, is it running ?")
            except Exception as e:
                printError("Error running command: ", e)

        except (KeyboardInterrupt, EOFError):
            print("\nExiting Taskmaster.")
            break

    readline.write_history_file(HISTORY_FILE)

def setup(client: rpc.Client):
    try:
        completion_engine = CompletionEngine(client)
        readline.set_completer(completion_engine)
        if platform.system() == "Darwin":
            readline.parse_and_bind("bind ^I rl_complete")  # on MacOS 🥶
        else:
            readline.parse_and_bind("tab: complete")
    except Exception as e:
        print(f"Could not setup readline: {e}")


def main():
    "client main"
    try:
        with rpc.Client() as client:
            run(client)
    except Exception as e:
        print(f"Could not connect to server: {e}")


if __name__ == "__main__":
    main()
