#!/usr/bin/env python3

import os
import asyncio
import logging
import config

import rpc
from echo_server import EchoServer
from argparse import ArgumentParser, Namespace
from runner import TaskMaster, TaskMasterShutdown


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


def raise_exception_if_root_user():
    "Check if user is root."
    if os.geteuid() == 0:
        raise Exception("""
            Taskmaster being run as root /!\\
            To allow use the `--allow-root` flag
        """)


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


async def start(arguments: Namespace):
    # Forbid use root user
    if not arguments.allow_root:
        raise_exception_if_root_user()

    try:
        configuration = config.load(arguments.config_file)
    except Exception as e:
        logging.error(f"Could not load configuration: {e}")
        return

    task_master = TaskMaster(configuration)

    # Wait for taskmaster to start
    await task_master.start()

    rpc_server = rpc.Server(task_master)
    
    task_master_wait = asyncio.create_task(task_master.wait())
    serve_rpc = asyncio.create_task(rpc_server.serve(arguments.port))
    (done, pending) = await asyncio.wait(
        [ task_master_wait, serve_rpc ],
        return_when=asyncio.FIRST_COMPLETED
    )

    if not task_master_wait.done():
        task_master_wait.cancel()

    if not serve_rpc.done():
        serve_rpc.cancel()

    await asyncio.wait(pending)


if __name__ == "__main__":
    main()
