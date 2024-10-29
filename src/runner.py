import os
import logging
import asyncio
from asyncio.subprocess import Process
from enum import Enum
from typing import Optional, Any
from config import Configuration, TaskDescription, RestartCondition


class Status(Enum):
    # Process is stop or has'nt been started
    STOPPED = 0
    # Process hasn't been running long enough to be considered
    # completly successfully started
    STARTING = 1
    # Process in running
    RUNNING = 2
    # Process has been started several times without success
    BACKOFF = 3
    # Process has received its stop signal but isn't done yet
    STOPPING = 4
    # Process has exited from running state
    EXITED = 5
    # Process could not start running
    FATAL = 6


class Task:
    name: str
    status: Status
    description: TaskDescription
    process: Optional[Process]
    # TODO: Add logger

    def __init__(self, name: str, description: TaskDescription):
        self.name = name
        self.description = description
        self.status = Status.STOPPED
        self.process = None

    def make_start_arguments(self) -> dict[str, Any]:
        arguments: dict[str, Any] = {}
        if self.description.environment is not None:
            env = os.environ.copy()
            env.update(self.description.environment)
            arguments["env"] = env

        # if self.description.pwd is not None:
        #     arguments["pwd"] = self.description.pwd

        return arguments

    async def start(self):
        self.status = Status.STARTING
        logging.info(f"{self.name}: Starting")
        self.process = await asyncio.create_subprocess_shell(
                self.description.command,
                **self.make_start_arguments())
        await self.wait_successful_start()

    async def wait_successful_start(self):
        logging.info(f"{self.name}: Waiting for successful start")
        delay = self.description.success_start_delay.total_seconds()
        try:
            async with asyncio.timeout(delay):
                await self.wait()
                logging.info(f"{self.name}: Start failed")
                raise TaskStartFailure(self.description)
        except asyncio.TimeoutError:
            logging.info(f"{self.name}: Successful start")
            self.status = Status.RUNNING

    # TODO: Add gracefull stop && force stop methods
    async def wait(self) -> int:
        """
            Warning only call when process is running
        """
        if self.process is None:
            raise Exception("Waiting for a process that is not running")
        exit_code = await self.process.wait()
        self.status = Status.EXITED
        self.process = None
        return exit_code

    async def start_until_success(self):
        logging.info(f"{self.name}: Starting task")
        for i in range(self.description.restart_attempts):
            logging.info(f"{self.name}: Start number {i + 1}")
            try:
                return await self.start()
            except TaskStartFailure:
                # TODO: log error
                continue
            except Exception as e:
                logging.info(f"{self.name}: Error starting process {e}")
                self.status = Status.FATAL
                return
        logging.info(f"{self.name}: Could not start process")
        self.status = Status.BACKOFF
        raise TaskStartFailure(self.description)

    async def run(self):
        while True:
            try:
                await self.start_until_success()

                exit_code = await self.wait()
                success_exit_codes = self.description.success_exit_codes
                successful_exit = exit_code in success_exit_codes
                logging.info(f"exited with code {exit_code}")

                match self.description.restart:
                    case RestartCondition.ALWAYS:
                        continue
                    case RestartCondition.ONFAILURE if not successful_exit:
                        continue

            except Exception as e:
                logging.info(f"{self.name}: Could not run: {e}")
                # TODO: open
                pass

            logging.info(f"{self.name}: Finished")

            # TODO: Wait for start signal
            while True:
                await asyncio.sleep(1)


class TaskStartFailure(Exception):
    """Task could not be started"""

    def __init__(self, task: TaskDescription):
        super().__init__(self, f"could not start `{task.command}`")


class TaskMaster:
    tasks: dict[str, Task]
    configuration: Configuration

    def __init__(self, configuration: Configuration):
        self.configuration = configuration
        self.tasks = {}

    async def run(self):
        logging.info("Starting taskmaster")
        self.tasks = {
            name: Task(name, description)
            for name, description in self.configuration.tasks.items()
        }
        try:
            await asyncio.gather(*[task.run() for task in self.tasks.values()])
        except asyncio.CancelledError as e:
            # TODO: graceful shutdown
            logging.info(f"Stopping {e}...")
        except KeyboardInterrupt as e:
            # TODO: graceful shutdown
            logging.info(f"Stopping {e}...")
