import asyncio
import logging

from dataclasses import dataclass
from instance import Instance
from enum import IntEnum
from logging import Logger
from asyncio.subprocess import Process
from typing import List, Optional, Any, cast
from config import Configuration, TaskDescription, RestartCondition

class Command:
    pass


class Shutdown(Command):
    pass


@dataclass
class Update(Command):
    desc: TaskDescription


@dataclass
class Start(Command):
    replica: int


@dataclass
class Stop(Command):
    replica: int


class Task:
    logger: Logger
    desc: TaskDescription
    instances: List[Instance]
    command_queue: asyncio.Queue[Command]
    shutting_down: bool

    def __init__(self, logger: Logger, desc: TaskDescription):
        self.logger = logger
        self.desc = desc
        self.command_queue = asyncio.Queue()
        self.shutting_down = False
        self.instances = []

        for _ in range(desc.replicas):
            self.add_instance()

    def add_instance(self) -> Instance:
        id = len(self.instances) + 1
        logger = logging.getLogger(f"{self.logger.name}:{id}")
        instance = Instance(self.desc, logger)
        self.instances.append(instance)
        return Instance

    def stop(self):
        for instance in self.instances:
            instance.shutdown()

    def shutdown(self):
        self.shutting_down = True
        self.stop()

    def update_description(self, desc: TaskDescription):
        for instance in self.instances:
            instance.update_description(desc)

    def instance(self, replica: int) -> Optional[Instance]:
        if 1 <= replica <= len(self.instances):
            return self.instances[replica - 1]
        self.logger.warn(f"Unknown replica {replica}")
        return None

    def requires_restart(self, desc: TaskDescription) -> bool:
        return (
            desc.command != self.desc.command or
            desc.stdout != self.desc.stdout or
            desc.stderr != self.desc.stderr or
            desc.environment != self.desc.environment or
            desc.pwd != self.desc.pwd or
            desc.umask != self.desc.umask
        )

    async def run(self):
        while not self.shutting_down:
            instance_runs = [
                asyncio.create_task(instance.run())
                for instance in self.instances
            ] 

            while True:
                command = await self.command_queue.get()
                self.logger.debug(f"Command: {command}")
                match command:
                    case Start():
                        command: Start
                        instance = self.instance(command.replica)
                        if instance is not None:
                            instance.start()
                    case Stop():
                        command: Stop
                        instance = self.instance(command.replica)
                        if instance is not None:
                            instance.stop()
                    case Update():
                        command : Update
                        self.logger.debug("updating description")
                        # TODO: update on change
                        if self.requires_restart(command.desc):
                            self.logger.info("restarting all processes")
                            self.stop()
                            self.update_description(command.desc)
                            break
                        else:
                            self.logger.info("updating all processes")

                            to_stop = self.instances[command.desc: self.desc.replicas]

                            for instance in to_stop:
                                instance.shutdown()

                            await asyncio.wait(to_stop)
                            
                            self.update_description(command.desc)

                            while len(self.instances) < self.desc.replicas:
                                instance = self.add_instance()
                                instance_runs.append(asyncio.create_task(instance.run()))

                    case Shutdown():
                        self.logger.info("Shutting down")
                        self.shutdown()
                        break

            await asyncio.wait(instance_runs)
