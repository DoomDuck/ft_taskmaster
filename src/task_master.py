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
            self.logger.warn(f'Unknown task: "{name}"')
        return result

    async def run(self):
        self.logger.info("Starting")

        configuration = Configuration.load(self.config_file)

        self.tasks = {
            name: Task(logging.getLogger(f"{self.logger.name}:{name}"), desc)
            for name, desc in configuration.tasks.items()
        }

        running_tasks = {
            name: asyncio.create_task(task.run())
            for name, task in self.tasks.items()
        }

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
                        self.logger.warn(f'Unknown "{command.task}"')
                case Stop():
                    command: Stop
                    t = self.task(command.task)
                    if t is not None:
                        # TODO: Give the correct replica
                        await t.command_queue.put(task.Stop(1))
                    else:
                        self.logger.warn(f'Unknown task "{command.task}"')

                case Reload():
                    command: Reload
                    self.logger.info("Reloading")
                    new_configuration = Configuration.load(self.config_file)

                    previous_tasks = set(configuration.tasks.keys())
                    new_tasks = set(new_configuration.tasks.keys())

                    to_shutdown = previous_tasks.difference(new_tasks)
                    to_update = previous_tasks.intersection(new_tasks)
                    to_start = new_tasks.difference(previous_tasks)

                    tasks_shutting_down = []

                    for name in to_shutdown:
                        self.logger.debug(f"Shutting down {name}")
                        await self.tasks[name].command_queue.put(
                            task.Shutdown()
                        )
                        tasks_shutting_down.append(running_tasks[name])

                    for name in to_update:
                        self.logger.debug(f"Updating {name}")
                        command = task.Update(new_configuration.tasks[name])
                        await self.tasks[name].command_queue.put(command)

                    for name in to_start:
                        self.logger.debug(f"Starting {name}")
                        logger = logging.getLogger(
                            f"{self.logger.name}:{name}"
                        )
                        self.tasks[name] = Task(
                            logger, new_configuration.tasks[name]
                        )

                    if len(tasks_shutting_down) != 0:
                        await asyncio.wait(tasks_shutting_down)

                    for name in to_shutdown:
                        del self.tasks[name]
                        del running_tasks[name]

                    for name in to_start:
                        running_tasks[name] = asyncio.create_task(
                            self.tasks[name].run()
                        )

                    configuration = new_configuration

                case Shutdown():
                    self.logger.info("Shutting down")
                    for t in self.tasks.values():
                        await t.command_queue.put(task.Shutdown())
                    break

        self.logger.debug("Waiting for tasks to return")
        await asyncio.wait(list(running_tasks.values()))
