import datetime
from enum import Enum


class RestartType(Enum):
    ALWAYS = 1
    NEVER = 2
    ONFAILURE = 3


class Duration:
    pass


class Signal:
    pass


class Path(str):
    pass


class Environment:
    pass


class Umask:
    pass


class Configuration:
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

    command: list[str]
    process_count: int
    start_on_launch: bool
    restart: RestartType
    success_exit_codes: list[int]
    success_start_delay: datetime.timedelta
    restart_attempts: int
    gracefull_shutdown_signal: Signal
    gracefull_shutdown_success_delay: datetime.timedelta
    stdout: Path | None
    stderr: Path | None
    environment: Environment
    pwd: Path
    umask: Umask


def parse() -> Configuration:
    raise "Unimplemented"
