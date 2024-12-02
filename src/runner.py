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


class Command(Enum):
    START = 0
    STOP = 1


class Task:
    name: str
    status: Status
    description: TaskDescription
    process: Optional[Process]
    command_queue: asyncio.Queue[Command]
    logger: logging.Logger

    def __init__(self, name: str, description: TaskDescription):
        self.name = name
        self.description = description
        self.status = Status.STOPPED
        self.process = None
        self.command_queue = asyncio.Queue()
        self.logger = logging.getLogger(name)

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
        self.logger.info("Starting")
        self.process = await asyncio.create_subprocess_shell(
                self.description.command,
                **self.make_start_arguments())
        await self.wait_successful_start()

    async def wait_successful_start(self):
        self.logger.info("Waiting for successful start")
        delay = self.description.success_start_delay.total_seconds()
        try:
            async with asyncio.timeout(delay):
                await self.wait()
                self.logger.info("Start failed")
                raise TaskStartFailure(self.description)
        except asyncio.TimeoutError:
            self.logger.info("Successful start")
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

    async def try_successive_starts(self):
        self.logger.info("Starting task")
        for attempt_number in range(self.description.restart_attempts):
            self.logger.info(f"Start number {attempt_number + 1}")
            try:
                return await self.start()
            except TaskStartFailure:
                # TODO: log error
                self.logger.info("Task did not run long enough")
                continue
            except Exception as e:
                self.logger.error(f"Starting process: {e}")
                self.status = Status.FATAL
                return
        self.logger.warning("Could not start process")
        self.status = Status.BACKOFF

    async def graceful_shutdown(self):
        self.logger.info("Shutting down")
        signal = self.description.graceful_shutdown_signal
        if signal is None:
            return

        self.process.send_signal(signal)

        asyncio.wait_for(
            self.wait(),
            self.description.gracefull_shutdown_success_delay
        )

    async def manage(self):
        """Manage the execution of this task"""

        if self.description.start_on_launch:
            await self.try_successive_starts()

        while True:
            if self.process is None:
                await self.manage_idle()
            else:
                successful_exit = await self.manage_running()

                restarts_on_failure = (
                    self.description.restart == RestartCondition.ONFAILURE
                )
                # TODO: fix the condition
                if restarts_on_failure and not successful_exit:
                    continue

                await self.try_successive_starts()

    async def manage_running(self) -> bool:
        process_update = None
        incomming_command = None
        while True:
            # Create tasks
            if not process_update:
                process_update = asyncio.create_task(self.wait())
            if not incomming_command:
                incomming_command = (
                    asyncio.create_task(self.command_queue.get())
                )

            # Wait for at least one
            await asyncio.wait(
                (process_update, incomming_command),
                return_when=asyncio.FIRST_COMPLETED
            )

            # Handle command
            if incomming_command.done():
                match incomming_command.result():
                    case Command.START:
                        self.logger.info("Task already running")
                    case Command.STOP:
                        self.graceful_shutdown()
                # Commands can get lost
                incomming_command = (
                    asyncio.create_task(self.command_queue.get())
                )

            # Handle process update
            if process_update.done():
                exit_code = process_update.result()
                success_exit_codes = self.description.success_exit_codes
                successful_exit = exit_code in success_exit_codes
                status_message = "success" if successful_exit else "failure"
                self.logger.info((
                    f"exited with code {exit_code} "
                    f"({status_message})"
                ))
                return successful_exit

    async def manage_idle(self):
        while True:
            match await self.command_queue.get():
                case Command.START:
                    self.logger.info("Starting")
                    break
                case Command.STOP:
                    self.logger.info("Program already stopped")


class TaskStartFailure(Exception):
    """Task could not be started"""

    def __init__(self, task: TaskDescription):
        super().__init__(self, f"could not start `{task.command}`")


class TaskMaster:
    tasks: dict[str, Task]
    configuration: Configuration

    def __init__(self, configuration: Configuration):
        self.tasks = {}
        self.configuration = configuration

    async def run(self):
        logging.info("Starting taskmaster")
        try:
            async with asyncio.TaskGroup() as tg:
                for name, desc in self.configuration.tasks.items():
                    task = Task(name, desc)
                    self.tasks[name] = task
                    tg.create_task(task.manage())
        finally:
            # TODO: graceful shutdown
            logging.info("Stopping...")
