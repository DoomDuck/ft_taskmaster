# Allow referencing a class within its own body
from __future__ import annotations

import yaml
import schema
from signal import Signals
from typing import Optional
from enum import Enum
from dataclasses import dataclass
from schema import Schema, And, Or, Use
from datetime import timedelta


class RestartCondition(Enum):
    ALWAYS = "always"
    NEVER = "never"
    ON_FAILURE = "on_failure"


PositiveInt = And(int, lambda n: 0 <= n)
StriclyPositiveInt = And(int, lambda n: 0 < n)
Signal = Use(Signals.__getitem__)
RestartSchema = Use(RestartCondition)
Path = str
Environment = Or({str: str})
Umask = And(str, Use(lambda u: int(u, base=8)))


@dataclass
class TaskDescription:
    """
    - Start command
    - Number of process to start and keep alive
    - If program is started at launch or not
    - If program should restart
        - always
        - never
        - on unexpected exits
    - What return code are "unexpected exists"
    - How long a program should run for to be considered "successfully started"
    - How many restart should be attempted before aborting
    - Which signals should be used for a gracefull shutdown
    - How long to wait for a gracefull shutdown before killing it
    - Optional redirections of stdout/stderr files
    - Environment variables
    - The working directory
    - The umask used by the program
    """

    command: str
    replicas: int
    start_on_launch: bool
    restart: RestartCondition
    success_exit_codes: set[int]
    start_timeout: timedelta
    start_attempts: int
    shutdown_signal: Signals
    shutdown_timeout: timedelta
    stdout: Optional[str]
    stderr: Optional[str]
    environment: dict[str, str]
    pwd: Optional[str]
    umask: Optional[int]

    schema = Schema(
        {
            "command": str,
            schema.Optional("replicas"): StriclyPositiveInt,
            schema.Optional("start_on_launch"): bool,
            schema.Optional("restart"): RestartSchema,
            schema.Optional("success_exit_codes"): [int],
            schema.Optional("start_timeout"): PositiveInt,
            schema.Optional("start_attempts"): StriclyPositiveInt,
            schema.Optional("shutdown_signal"): Signal,
            schema.Optional("shutdown_timeout"): PositiveInt,
            schema.Optional("stdout"): Path,
            schema.Optional("stderr"): Path,
            schema.Optional("environment"): Environment,
            schema.Optional("pwd"): Path,
            schema.Optional("umask"): Umask,
        }
    )

    @staticmethod
    def build(d: dict) -> TaskDescription:
        return TaskDescription(
            command=d["command"],
            replicas=d.get("replicas", 1),
            start_on_launch=d.get("start_on_launch", True),
            restart=RestartCondition(d.get("restart", "on_failure")),
            success_exit_codes=set(d.get("success_exit_codes", [0])),
            start_timeout=timedelta(seconds=d.get("start_timeout", 3)),
            start_attempts=d.get("start_attempts", 3),
            shutdown_signal=Signals[d.get("shutdown_signal", "SIGTERM")],
            shutdown_timeout=timedelta(seconds=d.get("shutdown_timeout", 10)),
            stdout=d.get("stdout"),
            stderr=d.get("stderr"),
            environment=d.get("environment", {}),
            pwd=d.get("pwd"),
            umask=int(d.get("umask", "644"), base=8),
        )

    def __eq__(self, other) -> bool:
        return (
            self.command == other.command
            and self.replicas == other.replicas
            and self.start_on_launch == other.start_on_launch
            and self.restart == other.restart
            and self.success_exit_codes == other.success_exit_codes
            and self.start_timeout == other.start_timeout
            and self.start_attempts == other.start_attempts
            and self.shutdown_signal == other.shutdown_signal
            and self.shutdown_timeout == other.shutdown_timeout
            and self.stdout == other.stdout
            and self.stderr == other.stderr
            and self.environment == other.environment
            and self.pwd == other.pwd
            and self.umask == other.umask
        )


@dataclass
class Configuration:
    tasks: dict[str, TaskDescription]

    schema = Schema(
        {
            "tasks": {str: Schema(TaskDescription.schema)},
        }
    )

    @staticmethod
    def build(d: dict) -> Configuration:
        tasks = {}
        for name, desc in d["tasks"].items():
            tasks[name] = TaskDescription.build(desc)
        return Configuration(tasks)

    @staticmethod
    def load(file_path: str) -> Configuration:
        with open(file_path, "r") as file:
            data_dictionnary = yaml.load(file, Loader=yaml.SafeLoader)
        Configuration.schema.validate(data_dictionnary)
        return Configuration.build(data_dictionnary)

    def __eq__(self, other) -> bool:
        return self.tasks == other.tasks
