import json
import socket


class Command:
    def __init__(self, name, arg):
        self.name = name
        self.arg = arg

    def toJSON(self):
        return json.dumps(
            self,
            default=lambda o: o.__dict__)


class Request:
    def __init__(self, type: str, command: Command):
        self.type = type
        self.command = command
    def to_json(self):
        return json.dumps(
            self,
            default=lambda o: o.__dict__)

class Response:
    def __init__(self, status: str, data: bytes):
        self.status = status
        self.data = data

    def to_dict(self):
        return json.loads(self.data)

class Connection:
    sock: socket.socket
    buffer: bytearray

    def __init__(self, sock: socket.socket):
        self.sock = sock
        self.buffer = bytearray()

    def send(self, request: Request):
        data = request.to_json().encode() + b'\n'
        self.sock.sendall(data)

    def receive(self) -> Response:
        while True:
            index = self.buffer.find(b'\n')
            if index != -1:
                break
            data = self.sock.recv(0x1000)
            if len(data) == 0:
                raise Exception("End of stream")
            self.buffer.extend(data)
            

        message = self.buffer[:index]
        print(f"Got message: {message}")
        del self.buffer[:index + 1]
        response = Response("success", message.decode())
        return response