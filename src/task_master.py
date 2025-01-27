import asyncio
import logging
import task

from dataclasses import dataclass
from task import Task
from logging import Logger
from typing import Optional
from config import Configuration


class Command:
    pass


class Reload(Command):
    pass


class Shutdown(Command):
    pass


@dataclass
class Stop(Command):
    task: str
    pass


@dataclass
class Start(Command):
    task: str
    pass


class TaskMaster:
    config_file: str
    tasks: dict[str, Task]
    command_queue: asyncio.Queue[Command]
    logger: Logger

    def __init__(self, logger: Logger, config_file: str):
        self.tasks = {}
        self.config_file = config_file
        self.command_queue = asyncio.Queue()
        self.logger = logger

    async def start(self, name: str):
        await self.command_queue.put(Start(name))

    async def stop(self, name: str):
        await self.command_queue.put(Stop(name))

    async def restart(self, name: str):
        await self.command_queue.put(Start(name))
        await self.command_queue.put(Stop(name))

    async def reload(self):
        await self.command_queue.put(Reload())

    async def shutdown(self):
        await self.command_queue.put(Shutdown())

    def task(self, name: str) -> Optional[Task]:
        result = self.tasks.get(name)
        if result is None:
            self.logger.warn(f"unknown task: \"{name}\"")
        return result

    async def run(self):
        self.logger.info("Starting taskmaster")

        configuration = Configuration.load(self.config_file)

        self.tasks = {
            name: Task(logging.getLogger(f"{self.logger.name}:{name}"), desc)
            for name, desc in configuration.tasks.items()
        }

        running_tasks = [
            asyncio.create_task(task.run())
            for task in self.tasks.values()
        ]

        # Handle commands until shutdown
        while True:
            command = await self.command_queue.get()
            self.logger.debug(f"Command: {command}")
            match command:
                case Start():
                    command: Start
                    t = self.task(command.task)
                    if t is not None:
                        # TODO: Give the correct replica
                        await t.command_queue.put(task.Start(1))
                    else:
                        self.logger.warn(f"unknown {command.task}")
                case Stop():
                    command: Stop
                    t = self.task(command.task)
                    if t is not None:
                        # TODO: Give the correct replica
                        await t.command_queue.put(task.Stop(1))
                    else:
                        self.logger.warn(f"unknown task {command.task}")

                case Reload():
                    command: Reload
                    self.logger.info("Reloading")
                    # new_configuration = Configuration.load(self.config_file)

                    # TODO: Check for config differences

                case Shutdown():
                    self.logger.info("Shutting down")
                    for t in self.tasks.values():
                        await t.command_queue.put(task.Shutdown())
                    break

        self.logger.debug("Waiting for tasks to return")
        await asyncio.wait(running_tasks)
