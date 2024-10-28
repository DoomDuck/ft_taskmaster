import sys
from schema import Schema, And, Or, Use, Optional
import argparse

# @dataclass
# class Command:
#     name: str
#     argument: str
#     option: str

# statusCommandSchema = Schema({
#     'name': str,
#     'argument': [str],
#     'option': [str],
# })


# stopCommandSchema = Schema({

# })

# restartCommandSchema = Schema({

# })


class Command:
    name: str
    argument: [str]
    option: [str]
    


startCommandSchema = Schema({
    'name': str,
    'task': Or("nginx", "prout"),
    Optional('option'): [str],
})


def start_task(task_name):
    print("start :", task_name)


command_dict = {
    "status": start_task,
    "start": start_task,
    "stop": start_task,
    "reload" : start_task
}


def check_command(command: str) -> bool:
    if command.__len__() > 1:
        if command[0] in command_dict:
            print("command", command)
            command_tmp = {}
            command_tmp["name"] = command[0]
            command_tmp["task"] = command[1]
            return print("validate:", startCommandSchema.is_valid(command_tmp))
      

while True:
    line = sys.stdin.readline()

    command = line.split()
    print(command.__len__())
    if check_command(command):
        command_dict[command[0]](command[1])
    else:
        print("Command invalid")