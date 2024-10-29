#!/usr/bin/env python3

import asyncio
import readline
from config import Configuration
import sys
from dataclasses import dataclass
import socket


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


class Connection:
    sock: socket.socket
    buffer: bytes

    def __init__(self, sock: socket.socket):
        self.sock = sock
        self.buffer = bytes()

    def send(self, message: str):
        self.sock.sendall(f"{message}\n".encode())

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
        self.connection.send("get process")
        reponse = self.connection.receive()

        names = reponse.split()
        return [s for s in names if s.startswith(text)]


    def __call__(self, text: str, state):
        buffer = readline.get_line_buffer()
        cmd_with_args = buffer.split()
        if len(cmd_with_args) <= 1:
            matches = [
                cmd for cmd in command_dict.keys()
                if cmd.startswith(text)
            ]
        elif len(cmd_with_args) > 1:
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

            if True:
                connection.send(command_line)

            # if cmd in command_dict:
            #     if args:
            #         command_dict[cmd](args[0])
            #     else:
            #         command_dict[cmd]()
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

MAX_COMMAND_SIZE=4096

def main():
    connection = socket.create_connection(("localhost", 4242))
    connection = Connection(connection)

    run(connection)


if __name__ == "__main__":
    main()
