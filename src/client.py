#!/usr/bin/env python3
import socket
import readline
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
    connection: Connection

    def __init__(self, connection: Connection):
        self.connection = connection

    def get_matches(self, prefix: str):
        console.log("test")
        self.connection.send(Request("get", Command("getProcess", "test")).toJSON)
        response = self.connection.receive(),
        names = response.split()
        return [s for s in names if s.startswith(prefix)]

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


def setup(connection: Connection):
    try:
        completion_engine = CompletionEngine(connection)

        readline.set_completer(completion_engine)
        if platform.system() == "Darwin":
            readline.parse_and_bind("bind ^I rl_complete") # on MacOS 🥶
        else:
            readline.parse_and_bind("tab: complete")
    except Exception as e:
        print(f"Could not setup readline: {e}")


def run(connection: Connection):
    setup(connection)

    while True:
        try:
            command_line = input(
                Colors.YELLOW +
                "🔧 Taskmaster\n   ⤷ " +
                Colors.RESET,
            )

            if not command_line:
                continue

            cmd, *args = command_line.split()

            if cmd in commands:
                if len(args) > 2:
                    print(
                    "unexpected argument\n.",
                    "Available argument: ") 
                command = Command(cmd, args)
                request = Request("exec", command)
                connection.send(request)
                response = connection.receive()
                print(response.data)

            else:
                print(
                    "Unknown command\n."
                    "Available commands: ",
                    commands
                )

        except KeyboardInterrupt:
            print("\nExiting Taskmaster.")
            break

    readline.write_history_file(HISTORY_FILE)


MAX_COMMAND_SIZE = 4096


def main():
    "client main"
    try:
        connection = socket.create_connection(("localhost", 4242))
        connection = Connection(connection)
        run(connection)
    except Exception as e:
        print(f"Could not connect to server: {e}")
if __name__ == "__main__":
    main()
