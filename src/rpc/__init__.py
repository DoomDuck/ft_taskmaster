import grpc

from rpc import command_pb2_grpc
from typing import List, AsyncGenerator
from task_master import TaskMaster
from rpc.command_pb2 import Target, TaskStatus, Empty
from rpc.command_pb2_grpc import RunnerStub, RunnerServicer

DEFAULT_PORT: int = 50051


class Client:
    stub: RunnerStub

    def __init__(self, address: str = "localhost", port: int = DEFAULT_PORT):
        self.channel = grpc.insecure_channel(f"{address}:{port}")
        self.stub = RunnerStub(self.channel)

    def start(self, task: str, instance_ids: List[int] = []):
        self.stub.start(Target(name=task, instance_id=instance_ids))

    def stop(self, task: str,  instance_ids: List[int] = [] ):
        self.stub.stop(Target(name=task, instance_id=instance_ids))

    def restart(self, task: str):
        self.stub.restart(Target(name=task))

    def list(self) -> List[str]:
        return list(
            map(lambda target: target.name, self.stub.list(Empty()))
        )

    def status(self, task: str) -> str:
        return self.stub.status(Target(name=task)).status

    def reload(self):
        self.stub.reload(Empty())

    def shutdown(self):
        self.stub.shutdown(Empty())

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        # TODO: remove
        self.channel.close()


class TaskMasterRunner(RunnerServicer):
    task_master: TaskMaster

    def __init__(self, task_master: TaskMaster):
        self.task_master = task_master

    async def start(self, target: Target, _context) -> Empty:
        await self.task_master.start(target.name, target.instance_id)
        return Empty()

    async def stop(self, target: Target, _context) -> Empty:
        await self.task_master.stop(target.name, target.instance_id)
        return Empty()

    async def restart(self, target: Target, _context) -> Empty:
        await self.task_master.restart(target.name, target.instance_id)
        return Empty()

    async def status(self, target: Target, _context) -> TaskStatus:
        # TODO: Return status
        return NotImplemented

    async def list(
        self, _arg: Empty, _context
    ) -> AsyncGenerator[Target, None]:
        for name in self.task_master.tasks:
            yield Target(name=name)

    async def reload(self, _arg: Empty, _context) -> Empty:
        await self.task_master.reload()
        return Empty()

    async def shutdown(self, _arg: Empty, _context) -> Empty:
        await self.task_master.shutdown()
        return Empty()


class Server:
    runner: TaskMasterRunner

    def __init__(self, task_master: TaskMaster):
        self.runner = TaskMasterRunner(task_master)

    async def serve(self, port: int = DEFAULT_PORT):
        server = grpc.aio.server()
        command_pb2_grpc.add_RunnerServicer_to_server(self.runner, server)
        server.add_insecure_port(f"localhost:{port}")
        await server.start()
        await server.wait_for_termination()
