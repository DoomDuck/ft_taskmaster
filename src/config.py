from enum import Enum
from typing import Optional
from datetime import timedelta
from dataclasses import dataclass, field


class RestartType(Enum):
    ALWAYS = 1
    NEVER = 2
    ONFAILURE = 3


def default_success_exit_codes() -> list[int]:
    return [0]


class Signal:
    pass


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
    replicas: int = 1
    start_on_launch: bool = True
    restart: RestartType = RestartType.ONFAILURE
    success_exit_codes: list[int] = \
        field(default_factory=default_success_exit_codes)
    success_start_delay: timedelta = timedelta(seconds=3)
    restart_attempts: int = 3
    # TODO(Dorian): Make the `Signal` class
    gracefull_shutdown_signal: Optional[Signal] = None
    gracefull_shutdown_success_delay: timedelta = timedelta(seconds=3)
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    environment: dict[str, str] = field(default_factory=dict)
    pwd: Optional[str] = None
    umask: Optional[int] = None


@dataclass
class Configuration:
    tasks: dict[str, TaskDescription]


def example() -> Configuration:
    return Configuration({
        "sleep": TaskDescription("sleep 10s"),
        "crasher": TaskDescription("./scripts/random_crash.sh"),
        # "hello": TaskDescription("echo hello"),
        # "bye": TaskDescription("echo bye"),
    })


def parse() -> TaskDescription:
    raise Exception("Unimplemented")
