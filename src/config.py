import datetime 
from enum import Enum
from dataclasses import dataclass
import yaml

from yaml.loader import SafeLoader

class RestartType(Enum):
    ALWAYS = 1
    NEVER = 2
    ONFAILURE = 3

class Duration:
    pass

class Signal(str):
    pass

class Path(str):
    pass

class Environment(list[str]):
    pass

class Umask(str):
    pass

@dataclass
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
    name : str
    command: list[str]
    start_on_launch: bool
    process_count: int
    restart: RestartType
    success_exit_codes: list[int]
    success_start_delay: datetime.timedelta
    restart_attempts: int
    gracefull_shutdown_signal: Signal
    gracefull_shutdown_success_delay: datetime.timedelta
    stdout: Path | None
    stderr: Path | None
    env: list[str] | None
    pwd: Path
    umask: Umask

def parse_configuration(program_name: str, program_data: dict) -> Configuration:
    print(f"program_data: {program_data}")
    return Configuration(
        name=program_name,
        command=program_data['command'],
        process_count=program_data['process_count'],
        start_on_launch=program_data['start_on_launch'],
        restart=RestartType[program_data['restart'].upper()],
        success_exit_codes=program_data['success_exit_codes'],
        success_start_delay=datetime.timedelta(seconds=program_data['success_start_delay']),
        restart_attempts=program_data['restart_attempts'],
        gracefull_shutdown_signal=Signal(program_data['gracefull_shutdown_signal'].upper()), 
        gracefull_shutdown_success_delay=datetime.timedelta(seconds=program_data['gracefull_shutdown_success_delay']),
        stdout=Path(program_data['stdout']) if program_data['stdout'] else None,
        stderr=Path(program_data['stderr']) if program_data['stderr'] else None,
        env=program_data['env'] if program_data['env'] else None,
        pwd=Path(program_data['pwd']),
        umask=Umask(program_data['umask']) 
    )

def read_and_parse_yaml(filename: str) -> list[Configuration]:
    with open(f'{filename}.yaml', 'r') as f:
        data = yaml.load(f, Loader=yaml.SafeLoader)
    
    program_list = data.get('programs')
    
    if not program_list:
        raise ValueError("programs key is missing")
    
    configurations = []
    
    for program_name, program_data in program_list.items():
        configurations.append(parse_configuration(program_name, program_data))
    
    return configurations

configurations = read_and_parse_yaml('test')
for config in configurations:
    print(f"""
----- Program: {config.name}
------- Command: {config.command}
------- Process count: {config.process_count}
------- Start on launch: {config.start_on_launch}
------- Restart policy: {config.restart}
------- Success exit codes: {config.success_exit_codes}
------- Success start delay: {config.success_start_delay}
------- Restart attempts: {config.restart_attempts}
------- Graceful shutdown signal: {config.gracefull_shutdown_signal}
------- Graceful shutdown success delay: {config.gracefull_shutdown_success_delay}
------- Stdout log path: {config.stdout}
------- Stderr log path: {config.stderr}
------- Env: {config.env}
------- Working directory (pwd): {config.pwd}
------- Umask: {config.umask}
""")
