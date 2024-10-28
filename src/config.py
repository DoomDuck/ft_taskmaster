import datetime
import yaml
from typing import Optional  # Pour les annotations de type
from enum import Enum
from dataclasses import dataclass, field
from schema import Schema, And, Or, Optional as SchemaOptional, SchemaError
from datetime import timedelta


class RestartCondition(Enum):
    ALWAYS = 1
    NEVER = 2
    ONFAILURE = 3


def default_success_exit_codes() -> set[int]:
    return set([0])


class Signal(str):
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
    restart: RestartCondition = RestartCondition.ONFAILURE
    success_exit_codes: set[int] = \
        field(default_factory=default_success_exit_codes)
    success_start_delay: timedelta = timedelta(seconds=1)
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


program_schema = Schema({
    'command': [str],
    'replicas': And(int, lambda n: n > 0),
    'start_on_launch': bool,
    'restart': And(str, lambda s: s in ['always', 'onfailure']),
    'success_exit_codes': [int],
    'success_start_delay': And(int, lambda n: n >= 0),
    'restart_attempts': And(int, lambda n: n >= 0),
    'gracefull_shutdown_signal': str,
    'gracefull_shutdown_success_delay': And(int, lambda n: n >= 0),
    SchemaOptional('stdout'): str,
    SchemaOptional('stderr'): str,
    SchemaOptional('environment'): Or([str], None, []),
    SchemaOptional('pwd'): str,
    SchemaOptional('umask'): str
})

main_schema = Schema({
    'programs': And(
        {str: Schema(program_schema)},  # Validation des programmes
        lambda d: len(d) > 0  # S'assurer qu'il y a au moins un programme
    )
})


def parse_configuration(program_data: dict) -> TaskDescription:
    print(f"program_data: {program_data}")
    return TaskDescription(
        command=program_data.get('command', []),
        replicas=program_data.get('replicas', 1),
        start_on_launch=program_data.get('start_on_launch', True),
        restart=program_data.get('restart', 'always').upper(),
        success_exit_codes=program_data.get('success_exit_codes', [0]),
        success_start_delay=datetime.timedelta(seconds=program_data.get('success_start_delay', 0)),
        restart_attempts=program_data.get('restart_attempts', 3),
        gracefull_shutdown_signal=Signal(program_data.get('gracefull_shutdown_signal', 'SIGTERM').upper()),
        gracefull_shutdown_success_delay=datetime.timedelta(seconds=program_data.get('gracefull_shutdown_success_delay', 10)),
        stdout=program_data.get('stdout') if program_data.get('stdout') else None,
        stderr=program_data.get('stderr') if program_data.get('stderr') else None,
        environment=program_data.get('environment', []),
        pwd=program_data.get('pwd', '/'),
        umask=program_data.get('umask', '022')
    )


def read_and_parse_yaml(filename: str) -> dict:
    try:
        with open(f'{filename}.yaml', 'r') as f:
            data = yaml.load(f, Loader=yaml.SafeLoader)
        main_schema.validate(data)
        configuration_from_yaml = data.get('programs', {})
        configuration_dict = {}
        for task_name, task in configuration_from_yaml.items():
            configuration_dict[task_name] = parse_configuration(task)
        return configuration_dict

    except (FileNotFoundError, IOError):
        print(f"Error : '{filename}.yaml' not found")
    except SchemaError as e:
        print("Error Validation schema YAML:", e)
    except ValueError as e:
        print("Value Errro in this yaml file:", e)
    except Exception as e:
        print("Unexpected error:", e)
    return {}


try:
    configuration = Configuration
    configuration.tasks = read_and_parse_yaml("test")
    if configuration.tasks:
        print("conf task", configuration.tasks["nginx"].stdout)
except Exception as e:
    print("Check your .yaml file sommething is wrong with", e.args)
