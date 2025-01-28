import asyncio
import logging

from dataclasses import dataclass
from instance import Instance
from logging import Logger
from typing import List, Optional
from config import TaskDescription


class Command:
    pass


class Shutdown(Command):
    pass


@dataclass
class Update(Command):
    desc: TaskDescription


@dataclass
class Start(Command):
    instance: int


@dataclass
class Stop(Command):
    instance: int

@dataclass
class Restart(Command):
    instance: int

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
        return instance

    def stop(self):
        for instance in self.instances:
            instance.shutdown()

    def shutdown(self):
        self.shutting_down = True
        self.stop()

    def update_description(self, desc: TaskDescription):
        for instance in self.instances:
            instance.update_description(desc)

    def instance(self, instance: int) -> Optional[Instance]:
        if 1 <= instance <= len(self.instances):
            return self.instances[instance - 1]
        self.logger.warn(f"Unknown instance {instance}")
        return None

    def requires_restart(self, desc: TaskDescription) -> bool:
        return (
            desc.command != self.desc.command
            or desc.stdout != self.desc.stdout
            or desc.stderr != self.desc.stderr
            or desc.environment != self.desc.environment
            or desc.pwd != self.desc.pwd
            or desc.umask != self.desc.umask
        )

    async def run(self):
        instance_runs = [
            asyncio.create_task(instance.run()) for instance in self.instances
        ]
        while not self.shutting_down:
            while True:
                command = await self.command_queue.get()
                self.logger.debug(f"Command: {command}")
                match command:
                    case Start():
                        command: Start
                        instance = self.instance(command.instance)
                        if instance is not None:
                            instance.start()
                    case Stop():
                        command: Stop
                        instance = self.instance(command.instance)
                        if instance is not None:
                            instance.stop()
                    case Restart():
                        command: Restart
                        instance = self.instance(command.instance)
                        if instance is None:
                            continue

                        instance.shutdown()

                        index = command.instance - 1
                        await instance_runs[index]
                        logger = logging.getLogger(f"{self.logger.name}:{command.instance}")
                        new_instance = Instance(self.desc, logger)
                        self.instances[index] = new_instance

                        instance_runs[command.instance] = asyncio.create_task(
                            new_instance.run()
                        )

                    case Update():
                        command: Update
                        self.logger.debug("updating description")
                        if self.requires_restart(command.desc):
                            self.logger.info("restarting all processes")
                            self.stop()
                            await asyncio.wait(instance_runs)
                            self.desc = command.desc
                            self.instances = []
                            instance_runs = []
                            while len(self.instances) < self.desc.replicas:
                                instance = self.add_instance()
                                instance_runs.append(
                                    asyncio.create_task(instance.run())
                                )
                        else:
                            self.logger.info("updating all processes")

                            to_stop = self.instances[
                                command.desc.replicas: self.desc.replicas
                            ]

                            for instance in to_stop:
                                instance.shutdown()

                            if len(to_stop) != 0:
                                await asyncio.wait(instance_runs[
                                    command.desc.replicas: self.desc.replicas
                                ])

                            while command.desc.replicas < len(self.instances):
                                self.instances.pop()


                            self.update_description(command.desc)
                            self.desc = command.desc

                            while len(self.instances) < self.desc.replicas:
                                instance = self.add_instance()
                                instance_runs.append(
                                    asyncio.create_task(instance.run())
                                )

                    case Shutdown():
                        self.logger.info("Shutting down")
                        self.shutdown()
                        break

        await asyncio.wait(instance_runs)
