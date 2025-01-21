import os
import logging
import asyncio
from asyncio.subprocess import Process
from enum import IntEnum
from typing import List, Optional, Any
from config import Configuration, TaskDescription, RestartCondition


class Status(IntEnum):
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


class Command(IntEnum):
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
        self.logger = logging.getLogger(f"task:{name}")

    def make_start_arguments(self) -> dict[str, Any]:
        arguments: dict[str, Any] = {}
        if self.description.environment is not None:
            env = os.environ.copy()
            env.update(self.description.environment)
            arguments["env"] = env

        if self.description.pwd is not None:
            # In the arguments it is called `cwd` for current working directory
            arguments["cwd"] = self.description.pwd

        if self.description.umask is not None:
            arguments["umask"] = self.description.umask

        try:
            if self.description.stdout is not None:
                arguments["stdout"] = open(self.description.stdout, mode="w+b")

            if self.description.stderr is not None:
                arguments["stderr"] = open(self.description.stderr, mode="w+b")
        except Exception:
            if arguments.get("stdout") is not None:
                arguments["stdout"].close()

            if arguments.get("stderr") is not None:
                arguments["stderr"].close()

            raise

        return arguments

    async def start(self):
        self.status = Status.STARTING
        self.logger.debug("Starting")
        self.process = await asyncio.create_subprocess_shell(
            self.description.command, **self.make_start_arguments()
        )
        await self.wait_successful_start()

    async def wait_successful_start(self):
        self.logger.debug("Waiting for successful start")
        delay = self.description.start_timeout.total_seconds()
        if delay == 0:
            return
        try:
            async with asyncio.timeout(delay):
                await self.wait()
                self.logger.debug("Start failed")
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
        self.logger.info("Starting")
        for attempt_number in range(self.description.restart_attempts + 1):
            try:
                return await self.start()
            except TaskStartFailure:
                self.logger.debug("Task did not run long enough")
                continue
            except asyncio.CancelledError:
                raise
            except Exception as e:
                self.logger.error(f"Starting process: {e}")
                self.status = Status.FATAL
                return
            self.logger.debug(f"Try to start again {attempt_number + 1}")
        self.logger.warning("Could not start process")
        self.status = Status.BACKOFF

    async def gracefull_shutdown(self):
        self.logger.info("Shutting down")
        signal = self.description.shutdown_signal
        if signal is None:
            return

        if self.process is not None:
            self.process.send_signal(signal)

        await asyncio.wait_for(
            self.wait(), self.description.shutdown_timeout.total_seconds()
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

                match self.description.restart:
                    case RestartCondition.NEVER:
                        continue
                    case RestartCondition.ON_FAILURE:
                        if successful_exit:
                            continue
                    case RestartCondition.ALWAYS:
                        pass

            # Try to start the program
            await self.try_successive_starts()

    async def manage_running(self) -> bool:
        process_update = None
        incomming_command = None
        while True:
            # Create tasks
            if not process_update:
                process_update = asyncio.create_task(self.wait())
            if not incomming_command:
                incomming_command = asyncio.create_task(
                    self.command_queue.get()
                )

            # Wait for at least one
            await asyncio.wait(
                (process_update, incomming_command),
                return_when=asyncio.FIRST_COMPLETED,
            )

            # Handle command
            if incomming_command.done():
                match incomming_command.result():
                    case Command.START:
                        self.logger.info("Task already running")
                    case Command.STOP:
                        await self.gracefull_shutdown()
                # Commands can get lost
                incomming_command = asyncio.create_task(
                    self.command_queue.get()
                )

            # Handle process update
            if process_update.done():
                exit_code = process_update.result()
                success_exit_codes = self.description.success_exit_codes
                successful_exit = exit_code in success_exit_codes
                status_message = "success" if successful_exit else "failure"
                self.logger.info(
                    (f"exited with code {exit_code} " f"({status_message})")
                )
                return successful_exit

    async def manage_idle(self):
        self.logger.debug("Going to idle")
        while True:
            match await self.command_queue.get():
                case Command.START:
                    self.logger.debug("Starting")
                    break
                case Command.STOP:
                    self.logger.debug("Program already stopped")
        self.logger.info("Stopped being idle")


class TaskStartFailure(Exception):
    """Task could not be started"""

    def __init__(self, task: TaskDescription):
        super().__init__(self, f"could not start `{task.command}`")


class TaskMasterCommand:
    pass


class Reload(TaskMasterCommand):
    pass


class Shutdown(TaskMasterCommand):
    pass


class TaskMaster:
    tasks: dict[str, Task]
    # TODO: rename
    coroutines: List[asyncio.Task]
    configuration: Configuration
    command_queue: asyncio.Queue[TaskMasterCommand]
    logger: logging.Logger

    def __init__(self, configuration: Configuration):
        self.tasks = {}
        self.coroutines = []
        self.configuration = configuration
        self.command_queue = asyncio.Queue()
        # TODO: find a better name
        self.logger = logging.getLogger("TaskMaster")

    async def start(self):
        logging.info("Starting taskmaster")
        for name, desc in self.configuration.tasks.items():
            task = Task(name, desc)
            self.tasks[name] = task
            self.coroutines.append(
                asyncio.create_task(task.manage(), name=f"Manage {name}")
            )

    async def handle_commands(self):
        while True:
            command = await self.command_queue.get()
            if isinstance(command, Reload):
                self.logger.info("Reloading")
            elif isinstance(command, Shutdown):
                self.logger.info("Shutting down")
                break

    async def wait(self):
        wait_for_tasks = asyncio.create_task(
            asyncio.wait(
                self.coroutines,
                return_when=asyncio.FIRST_EXCEPTION,
            )
        )
        handle_commands = asyncio.create_task(self.handle_commands())

        await asyncio.wait(
            [
                wait_for_tasks,
                # wait_for_shutdown,
                handle_commands,
            ],
            return_when=asyncio.FIRST_COMPLETED,
        )

        for coro in self.coroutines:
            # Exception can only have happened if a task is done
            if not coro.done():
                continue

            ex = coro.exception()
            if ex is not None:
                logging.error(f"{coro.get_name()}: {ex}")

        if wait_for_tasks.done():
            return

        # Shutdown
        for coro in self.coroutines:
            coro.cancel()

        await wait_for_tasks
