#!/usr/bin/env python3

import rpc
import socket
import readline
import platform
from dataclasses import dataclass
from communication import Request, Command, Connection

class Colors:
    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"


HISTORY_FILE = "taskmaster_history.log"


try:
    readline.read_history_file(HISTORY_FILE)
except FileNotFoundError:
    pass


def get_process(value):
    authorized_values = get_matches
    if value not in authorized_values:
        raise ValueError(f"'{value}' is not authorized")
    return value

def get_matches(self, prefix: str):
    print("tets")
    self.connection.send(Request("get", Command("getProcess", "test")).toJSON)
    response = self.connection.receive(),
    names = response.split()
    return [s for s in names if s.startswith(prefix)]

class Commands:
    list : [Command]

commands = [
    "start",
    "stop",
    "restart",
    "status",
    "reload",
]

class CompletionEngine:
    client: rpc.Client

    def __init__(self, client: rpc.Client):
        self.client = client

    def get_matches(self, prefix: str):
        return [
            task_name
            for task_name in self.client.list()
            if s.startswith(prefix)
        ]

    def __call__(self, text: str, state):
        buffer = readline.get_line_buffer()
        cmd, *cmd_with_args = buffer.split()
        if not cmd_with_args:
            matches = [
                cmd for cmd in commands
                if cmd.startswith(text)
            ]
        elif cmd_with_args:
            matches = self.get_matches(text)

        if state < len(matches):
            return matches[state]
        else:
            return None


def setup(client: rpc.Client):
    try:
        completion_engine = CompletionEngine(client)
        readline.set_completer(completion_engine)
        if platform.system() == "Darwin":
            readline.parse_and_bind("bind ^I rl_complete") # on MacOS 🥶
        else:
            readline.parse_and_bind("tab: complete")
    except Exception as e:
        print(f"Could not setup readline: {e}")


def run(client: rpc.Client):
    setup(client)

    while True:
        try:
            command_line = input(
                Colors.YELLOW +
                "🔧 Taskmaster\n   ⤷ " +
                Colors.RESET,
            )

            if not command_line:
                continue

            try:
                match command_line.split():
                    case ["start", task]:
                        client.start(task)
                    case ["stop", task]: 
                        client.stop(task)
                    case ["restart", task]: 
                        client.restart(task)
                    case ["reload"]: 
                        client.reload()
                    case ["shutdown"]: 
                        client.shutdown()
                    case ["quit"]:
                        break
                    case invalid:
                        print("Invalid command:", command_line)
            except Exception as e:
                print(f"Error running command: {e}")

        except KeyboardInterrupt:
            print("\nExiting Taskmaster.")
            break

    readline.write_history_file(HISTORY_FILE)


def main():
    "client main"
    try:
        with rpc.Client() as client:
            run(client)
    except Exception as e:
        print(f"Could not connect to server: {e}")

if __name__ == "__main__":
    main()
