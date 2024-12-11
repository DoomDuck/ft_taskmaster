#!/usr/bin/env python3

import os
import asyncio
import logging
import config

import rpc
from echo_server import EchoServer
from argparse import ArgumentParser, Namespace
from runner import TaskMaster


cla = ArgumentParser(
    description='sum the integers at the command line')

cla.add_argument(
    "config_file",
    type=str,
    help="Yaml task configuration",
    default="./configs/default.yaml",
)

cla.add_argument(
    "-l",
    "--log-file",
    type=str,
    help="Log file",
    default=None
)

cla.add_argument(
    "-p",
    "--port",
    type=int,
    help="rpc server port",
    default=50051,
)

cla.add_argument(
    "--allow-root",
    action="store_true",
    help="Log file",
    default=False,
)


def main():
    "Program entry point"

    arguments = cla.parse_args()

    logging.basicConfig(
        filename=arguments.log_file,
        level=logging.INFO,
    )

    try:
        asyncio.run(start(arguments))
    except KeyboardInterrupt:
        pass
    except Exception as exception:
        logging.error(f"Error starting: {exception}")


def raise_exception_if_root_user():
    "Check if user is root."
    if os.geteuid() == 0:
        raise Exception("""
            Taskmaster being run as root /!\\
            To allow use the `--allow-root` flag
        """)


async def start(arguments: Namespace):

    # Forbid use from being root
    if not arguments.allow_root:
        raise_exception_if_root_user()

    try:
        configuration = config.load(arguments.config_file)
    except Exception as e:
        logging.error(f"Could not load configuration: {e}")
        return

    task_master = TaskMaster(configuration)
    echo_server = EchoServer(task_master)
    rpc_server = rpc.Server(task_master)

    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(task_master.run())
            tg.create_task(echo_server.serve(4242))
            tg.create_task(rpc_server.serve(arguments.port))
    except ExceptionGroup as exception_group:
        for exception in exception_group.exceptions:
            logging.error(exception)


if __name__ == "__main__":
    main()
