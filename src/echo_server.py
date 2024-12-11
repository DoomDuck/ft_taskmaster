import asyncio

from runner import TaskMaster
from asyncio import StreamReader, StreamWriter


class EchoServer:
    task_master: TaskMaster
    connection_tasks: list[asyncio.Task]

    def __init__(self, task_master: TaskMaster):
        self.task_master = task_master
        self.connection_tasks = []

    async def serve(self, port: int = 4242):
        async def on_connection(reader: StreamReader, writer: StreamWriter):
            connection = Connection(self, reader, writer)
            task = asyncio.create_task(connection.handle())
            self.connection_tasks.append(task)

        start_server_task = asyncio.start_server(on_connection, port=port)
        async with await start_server_task as server:
            try:
                # TODO: see why I cannot use server.serve_forever()
                await server.start_serving()
                await server.wait_closed()
            except asyncio.CancelledError:
                for task in self.connection_tasks:
                    task.cancel()
                raise


class Connection:
    server: EchoServer
    reader: StreamReader
    writer: StreamWriter

    def __init__(
            self,
            server: EchoServer,
            reader: StreamReader,
            writer: StreamWriter
            ):
        self.server = server
        self.reader = reader
        self.writer = writer

    async def handle(self):
        try:
            async for line in self.reader:
                self.writer.write(line)
                await self.writer.drain()
        finally:
            self.writer.close()
