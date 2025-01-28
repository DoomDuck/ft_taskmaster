from __future__ import annotations

import os
import asyncio

from typing import Any
from logging import Logger
from signal import Signals
from datetime import datetime
from config import TaskDescription, RestartCondition
from abc import ABC, abstractmethod
from asyncio.subprocess import Process, create_subprocess_shell


async def create_subprocess(desc: TaskDescription) -> Process:
    arguments: dict[str, Any] = {}
    if desc.environment is not None:
        env = os.environ.copy()
        env.update(desc.environment)
        arguments["env"] = env

    if desc.pwd is not None:
        # In the arguments it is called `cwd` for current working directory
        arguments["cwd"] = desc.pwd

    if desc.umask is not None:
        arguments["umask"] = desc.umask

    try:
        if desc.stdout is not None:
            arguments["stdout"] = open(desc.stdout, mode="w+b")

        if desc.stderr is not None:
            arguments["stderr"] = open(desc.stderr, mode="w+b")
    except Exception:
        if arguments.get("stdout") is not None:
            arguments["stdout"].close()

        if arguments.get("stderr") is not None:
            arguments["stderr"].close()

        raise

    return await create_subprocess_shell(desc.command, **arguments)


class Stage(ABC):
    """Absctract base status class for polymorphism."""

    desc: TaskDescription
    should_start: asyncio.Event
    should_stop: asyncio.Event

    def __init__(self, desc: TaskDescription):
        self.desc = desc
        self.should_start = asyncio.Event()
        self.should_stop = asyncio.Event()

    async def next(self) -> Stage:
        """Go to next stage."""

        await self.should_start.wait()

        return await self.attempt_start()

    async def attempt_start(self, attempt: int = 1) -> Stage:
        """Try to make the start stage and fallback to Fatal otherwise."""
        if self.desc.start_attempts < attempt:
            return OutOfStartAttempts(self.desc)

        subprocess_creation = asyncio.create_task(create_subprocess(self.desc))
        should_stop_task = asyncio.create_task(self.should_stop.wait())
        await asyncio.wait(
            (subprocess_creation, should_stop_task),
            return_when=asyncio.FIRST_COMPLETED,
        )

        if not should_stop_task.done():
            should_stop_task.cancel()

        if subprocess_creation.done():
            exception = subprocess_creation.exception()
            if isinstance(exception, Exception):
                return Fatal(self.desc, exception)
            process = subprocess_creation.result()
            return Starting(self.desc, process, attempt)

        # Process creation was interrupted
        return NotStarted(self.desc)

    @abstractmethod
    def __repr__(self) -> str:
        raise NotImplementedError()


class StageWithProcess(Stage):
    """Stage with a running process attached to it"""

    process: Process

    def __init__(self, desc: TaskDescription, process: Process):
        super().__init__(desc)
        self.process = process

    def stop(self):
        try:
            self.process.send_signal(self.desc.shutdown_signal)
        except ProcessLookupError:
            pass


class NotStarted(Stage):
    """Task has not been started yet."""

    def __init__(self, desc: TaskDescription):
        super().__init__(desc)

    async def next(self) -> Stage:
        if not self.desc.start_on_launch:
            await self.should_start.wait()

        return await self.attempt_start()

    def __repr__(self) -> str:
        return "not started"


class Starting(StageWithProcess):
    """Task is attempting to start."""

    attempt: int
    start_time: datetime

    def __init__(self, desc: TaskDescription, process: Process, attempt: int):
        super().__init__(desc, process)
        self.attempt = attempt
        self.start_time = datetime.now()

    async def next(self) -> Stage:
        # Check if time has already elapsed
        elapsed = datetime.now() - self.start_time
        if self.desc.start_timeout < elapsed:
            return Running(self.desc, self.process)

        remainig_wait = (self.desc.start_timeout - elapsed).total_seconds()
        process_stopped = asyncio.create_task(self.process.wait())
        wait_start = asyncio.create_task(asyncio.sleep(remainig_wait))
        should_stop_task = asyncio.create_task(self.should_stop.wait())

        await asyncio.wait(
            (
                wait_start,
                process_stopped,
                should_stop_task,
            ),
            return_when=asyncio.FIRST_COMPLETED,
        )

        if not should_stop_task.done():
            should_stop_task.cancel()

        if process_stopped.done():
            if self.should_stop.is_set():
                return Exited(self.desc, process_stopped.result())
            return await self.attempt_start(self.attempt + 1)

        if self.should_stop.is_set():
            self.stop()
            return Exiting(self.desc, self.process)

        return Running(self.desc, self.process)

    def __repr__(self) -> str:
        return f"starting attempt n˚{self.attempt}"


class OutOfStartAttempts(Stage):
    """Task has been attempted to start too many unsuccessful times."""

    def __init__(self, desc: TaskDescription):
        super().__init__(desc)

    def __repr__(self) -> str:
        return "out of start attempts"


class Running(StageWithProcess):
    """Task is running as it should be."""

    def __init__(self, desc: TaskDescription, process: Process):
        super().__init__(desc, process)

    async def next(self) -> Stage:
        process_wait = asyncio.create_task(self.process.wait())
        should_stop_task = asyncio.create_task(self.should_stop.wait())
        await asyncio.wait(
            (process_wait, should_stop_task),
            return_when=asyncio.FIRST_COMPLETED,
        )

        if not should_stop_task.done():
            should_stop_task.cancel()

        if process_wait.done():
            exit_code = process_wait.result()
            match self.desc.restart:
                case RestartCondition.NEVER:
                    return Exited(self.desc, exit_code)
                case RestartCondition.ON_FAILURE:
                    if exit_code in self.desc.success_exit_codes:
                        return Exited(self.desc, exit_code)

        if self.should_stop.is_set():
            self.stop()
            return Exiting(self.desc, self.process)

        # Conditions are met to restart
        return await self.attempt_start()

    def __repr__(self) -> str:
        return f"running (pid: {self.process.pid})"


class Exiting(StageWithProcess):
    """Task is exciting."""

    start_exiting_time: datetime

    def __init__(self, desc: TaskDescription, process: Process):
        super().__init__(desc, process)
        self.start_exiting_time = datetime.now()

    # TODO: support events
    # TODO: manage stdout & stderr (maybe)
    async def next(self) -> Stage:
        # Check if time has already elapsed
        elapsed = datetime.now() - self.start_exiting_time
        if self.desc.start_timeout < elapsed:
            return Running(self.desc, self.process)

        to_wait = (self.desc.shutdown_timeout - elapsed).total_seconds()

        try:
            exit_code = await asyncio.wait_for(self.process.wait(), to_wait)
        except asyncio.TimeoutError:
            # Forceful exit
            self.process.kill()
            exit_code = await self.process.wait()

        return Exited(self.desc, exit_code)

    def __repr__(self) -> str:
        return f"exiting (pid: {self.process.pid})"


class Exited(Stage):
    """Task has excited, gracefully or forcefully."""

    exit_code: int

    def __init__(self, desc: TaskDescription, exit_code: int):
        super().__init__(desc)
        self.exit_code = exit_code

    def __repr__(self) -> str:
        try:
            signal = Signals(-self.exit_code)
            return f"exited by {signal.name}"
        except Exception:
            return f"exited with {self.exit_code}"


class Fatal(Stage):
    """Faced a fatal error trying to start."""

    exception: Exception

    def __init__(self, desc: TaskDescription, exception: Exception):
        super().__init__(desc)
        self.exception = exception

    def __repr__(self) -> str:
        return f"fatal ({self.exception})"


class Instance:
    stage: Stage
    shutting_down: bool
    finished: asyncio.Event
    logger: Logger

    def __init__(self, desc: TaskDescription, logger: Logger):
        self.stage = NotStarted(desc)
        self.logger = logger
        self.shutting_down = False
        self.finished = asyncio.Event()

    def start(self):
        if self.shutting_down:
            self.logger.warn("Asked to stop while shutting down")
        else:
            self.logger.info("Starting")
            self.stage.should_start.set()

    def stop(self):
        self.logger.info("Stopping")
        self.stage.should_stop.set()

    def shutdown(self):
        self.logger.info("Shutting down")
        self.shutting_down = True
        self.stop()
        self.update_finished()

    def update_finished(self):
        has_no_process = not isinstance(self.stage, StageWithProcess)
        if self.shutting_down and has_no_process:
            self.finished.set()

    def update_description(self, desc: TaskDescription):
        self.stage.desc = desc

    async def run(self) -> None:
        wait_until_finished = asyncio.create_task(self.finished.wait())
        wait_for_next_stage = asyncio.create_task(self.stage.next())
        while not self.finished.is_set():
            await asyncio.wait(
                (wait_until_finished, wait_for_next_stage),
                return_when=asyncio.FIRST_COMPLETED,
            )

            if wait_for_next_stage.done():
                self.stage = wait_for_next_stage.result()
                wait_for_next_stage = asyncio.create_task(self.stage.next())
                self.logger.info(f"{self.stage}")

            self.update_finished()

        self.logger.debug("Quitting loop")
