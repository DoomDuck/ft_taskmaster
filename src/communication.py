import json
import socket


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
    def __init__(self, type: str, command: Command):
        self.type = type
        self.command = command
    def toJSON(self):
        return json.dumps(
            self,
            default=lambda o: o.__dict__,
            indent=4)

class Response:
    def __init__(self, status: str, message: str):
        self.status = status
        self.message = message

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
