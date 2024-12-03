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
    def __init__(self, status: str, data: bytes):
        self.status = status
        self.data = data

    def to_dict(self):
        return json.loads(self.data)

class Connection:
    sock: socket.socket
    buffer: bytes

    def __init__(self, sock: socket.socket):
        self.sock = sock
        self.buffer = b''

    def send(self, request):
        print("Sending request:", request.command.name)
        data = request.toJSON()
        self.sock.sendall(bytes(data,encoding="utf-8"))

    def receive(self) -> Response:
        data = self.sock.recv(1024)
        return Response("success", data.decode("utf-8"))

  