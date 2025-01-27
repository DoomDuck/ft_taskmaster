#!/usr/bin/env python3

import os
import rpc
import asyncio
import logging

from signal import Signals
from task_master import TaskMaster
from argparse import ArgumentParser, Namespace


cla = ArgumentParser(description="sum the integers at the command line")

cla.add_argument(
    "config_file",
    type=str,
    help="Yaml task configuration",
    default="./configs/default.yaml",
)

cla.add_argument("-l", "--log-file", type=str, help="Log file", default=None)

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


cla.add_argument(
    "-L",
    "--log-level",
    type=str,
    choices=logging.getLevelNamesMapping().keys(),
    help="log level",
    default="INFO",
)


def raise_exception_if_root_user():
    "Check if user is root."
    if os.geteuid() == 0:
        # fmt: off
        raise Exception("""
            Taskmaster being run as root /!\\
            To allow use the `--allow-root` flag
        """)


def main():
    "Program entry point"

    arguments = cla.parse_args()

    logging.basicConfig(
        filename=arguments.log_file,
        level=arguments.log_level,
        format="[%(levelname)s] %(name)s: %(message)s",
    )

    try:
        asyncio.run(start(arguments))
    except Exception as exception:
        logging.error(f"Error starting: {exception}")


async def start(arguments: Namespace):
    # Forbid use root user
    if not arguments.allow_root:
        raise_exception_if_root_user()

    logger = logging.getLogger()

    task_master = TaskMaster(
        logger,
        arguments.config_file,
    )

    event_loop = asyncio.get_event_loop()

    def on_sigint():
        event_loop.create_task(task_master.shutdown())

    def on_sigusr1():
        event_loop.create_task(task_master.reload())

    event_loop.add_signal_handler(Signals.SIGINT, on_sigint)
    event_loop.add_signal_handler(Signals.SIGUSR1, on_sigusr1)

    rpc_server = rpc.Server(task_master)

    task_master_wait = event_loop.create_task(task_master.run())
    serve_rpc = event_loop.create_task(rpc_server.serve(arguments.port))
    (done, pending) = await asyncio.wait(
        (task_master_wait, serve_rpc),
        return_when=asyncio.FIRST_COMPLETED,
    )

    if not task_master_wait.done():
        task_master_wait.cancel()

    if not serve_rpc.done():
        serve_rpc.cancel()

    await asyncio.wait(pending)


if __name__ == "__main__":
    main()
