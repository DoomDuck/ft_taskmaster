#!/usr/bin/env python3
import readline
import socket
import json
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


class Command:
    def __init__(self, name, arg):
        self.name = name
        self.arg = arg

    def toJSON(self):
        return json.dumps(
            self,
            default=lambda o: o.__dict__,
            indent=4)


class Request:
    def __init__(self, type: str, command: Command, name: str = None, ):
        self.type = type
        self.name = name if name is not None else command.name
        self.command = command
    
    def toJSON(self):
        return json.dumps(
            self,
            default=lambda o: o.__dict__,
            sort_keys=True,
            indent=4)


class Response:
    pass


commands = [
    "start",
    "stop",
    "restart",
    "status",
    "reload",
    "exit",
    "help",
]


class Connection:
    sock: socket.socket
    buffer: bytes

    def __init__(self, sock: socket.socket):
        self.sock = sock
        self.buffer = bytes()

    def send(self, request: Request):
        
        self.sock.sendall(f"{request.toJSON()}\n".encode())

    def receive(self) -> str:
        while True:
            index = self.buffer.find(b'\n')
            if index != -1:
                break
            self.sock.recv_into(self.buffer)
        message = self.buffer[:index]
        print(f"Got message: {message}")
        self.buffer = self.buffer[index+1:]
        return message.decode()


class CompletionEngine:
    connection: Connection

    def __init__(self, connection: Connection):
        self.connection = connection

    def get_matches(self, prefix: str):
        self.connection.send("getprocess")

        reponse = self.connection.receive("hello")

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
                command = Command(cmd, args)
                request = Request("exec", command)
                connection.send(request)

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


MAX_COMMAND_SIZE = 4096


def main():
    connection = socket.create_connection(("localhost", 4242))
    connection = Connection(connection)

    run(connection)


if __name__ == "__main__":
    main()
