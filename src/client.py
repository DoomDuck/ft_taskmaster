#!/usr/bin/env python3

import socket
import readline
from dataclasses import dataclass
from communication import Request, Command, Connection
from schema import Schema, And, Or, In, Optional as SchemaOptional, SchemaError


class Colors:
    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"


history_file = "taskmaster_history.log"


try:
    readline.read_history_file(history_file)
except FileNotFoundError:
    pass


def get_process(value):
    valeurs_autorisees = get_matches# Remplace par ta liste
    if value not in valeurs_autorisees:
        raise ValueError(f"La valeur '{value}' n'est pas autorisée.")
    return value

def get_matches(self, prefix: str):
        print("tets")
        self.connection.send(Request("get", Command("getProcess")).toJSON)
        response = sef.connection.receive(),
        names = reponse.split()
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



exec_command_schema = Schema([
    {
        
    }
])


args_schema = Schema({
    "<process>" : And(str, lambda n : n < 1)
})

class CompletionEngine:
    connection: Connection

    def __init__(self, connection: Connection):
        self.connection = connection

    def get_matches(self, prefix: str):
        print("tets")
        self.connection.send(Request("get", Command("getProcess")).toJSON)
        response = sef.connection.receive(),
        names = reponse.split()
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
            match 
            matches = self.get_matches(text)

        if state < len(matches):
            return matches[state]
        else:
            return None


def setup(connection: Connection):
    completion_engine = CompletionEngine(connection)

    readline.set_completer(completion_engine)
    readline.parse_and_bind("tab: complete")


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
                    "Available argument: "
                ) 
                command = Command(cmd, args)
                request = Request("exec", command)
                connection.send(request)

            else:
                print(
                    "Unknown command\n."
                    "Available commands: ",
                    commands
                )

        except KeyboardInterrupt:
            print("\nExiting Taskmaster.")
            break

    readline.write_history_file(history_file)


MAX_COMMAND_SIZE = 4096


def main():
    connection = socket.create_connection(("localhost", 4242))
    connection = Connection(connection)

    run(connection)

if __name__ == "__main__":
    main()
