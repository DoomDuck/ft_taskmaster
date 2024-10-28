import datetime 
import yaml
from typing import Optional  # Pour les annotations de type
from enum import Enum
from dataclasses import dataclass, field
from schema import Schema, And, Or,Optional as SchemaOptional, SchemaError


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
    name: str
    command: list[str]
    start_on_launch: bool
    process_count: int
    restart: RestartType
    success_exit_codes: list[int]
    success_start_delay: datetime.timedelta
    restart_attempts: int
    gracefull_shutdown_signal: Signal
    gracefull_shutdown_success_delay: datetime.timedelta
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    environment: dict[str, str] = field(default_factory=dict)
    pwd: Optional[str] = None
    umask: Optional[int] = None


program_schema = Schema({
    'command': [str],
    'process_count': And(int, lambda n: n > 0),
    'start_on_launch': bool,
    'restart': And(str, lambda s: s in ['always', 'onfailure']),
    'success_exit_codes': [int],
    'success_start_delay': And(int, lambda n: n >= 0),
    'restart_attempts': And(int, lambda n: n >= 0),
    'gracefull_shutdown_signal': str,
    'gracefull_shutdown_success_delay': And(int, lambda n: n >= 0),
    'stdout': str,
    'stderr': str,
    SchemaOptional('environment'): Or([str], None, []),
    'pwd': str,
    'umask': str
})

main_schema = Schema({
    'programs': And(
        {str: Schema(program_schema)},  # Validation des programmes
        lambda d: len(d) > 0  # S'assurer qu'il y a au moins un programme
    )
})


def parse_configuration(program_name: str, program_data: dict) -> Configuration:
    print(f"program_data: {program_data}")
    return Configuration(
        name=program_name,
        command=program_data.get('command', []),
        process_count=program_data.get('process_count', 1),
        start_on_launch=program_data.get('start_on_launch', True),
        restart=RestartType[program_data.get('restart', 'always').upper()],
        success_exit_codes=program_data.get('success_exit_codes', [0]),
        success_start_delay=datetime.timedelta(seconds=program_data.get('success_start_delay', 0)),
        restart_attempts=program_data.get('restart_attempts', 3),
        gracefull_shutdown_signal=Signal(program_data.get('gracefull_shutdown_signal', 'SIGTERM').upper()),
        gracefull_shutdown_success_delay=datetime.timedelta(seconds=program_data.get('gracefull_shutdown_success_delay', 10)),
        stdout=Path(program_data.get('stdout')) if program_data.get('stdout') else None,
        stderr=Path(program_data.get('stderr')) if program_data.get('stderr') else None,
        environment=program_data.get('environment', []),
        pwd=Path(program_data.get('pwd', '/')),
        umask=Umask(program_data.get('umask', '022'))
    )


def read_and_parse_yaml(filename: str) -> list:
    try:
        with open(f'{filename}.yaml', 'r') as f:
            data = yaml.load(f, Loader=yaml.SafeLoader)
        main_schema.validate(data)
        program_list = data.get('programs', {})
        configurations = []
        for program_name, program_data in program_list.items():
            configurations.append(parse_configuration(program_name, program_data))      
        return configurations

    except (FileNotFoundError, IOError):
        print(f"Erreur : Le fichier '{filename}.yaml' est introuvable ou inaccessible.")
    except SchemaError as e:
        print("Erreur de validation du schéma YAML:", e)
    except ValueError as e:
        print("Erreur de contenu YAML:", e)
    except Exception as e:
        print("Une erreur inattendue s'est produite:", e)
    return []


configurations = read_and_parse_yaml('test')
if not configurations:
    print("something wrong with the configutation")
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
------- Environment: {config.environment}
------- Working directory (pwd): {config.pwd}
------- Umask: {config.umask}
""")
