#!/usr/bin/env python3

import os
import asyncio
import logging
import json
import config

from argparse import ArgumentParser, Namespace
from runner import TaskMaster
from asyncio import StreamReader, StreamWriter

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
    "--allow-root",
    action="store_true",
    help="Log file",
    default=False,
)


class Server:
    task_master: TaskMaster
    connection_tasks: list[asyncio.Task]

    def __init__(self, task_master: TaskMaster):
        self.task_master = task_master
        self.connection_tasks = []

    async def serve(self):
        async def on_connection(reader: StreamReader, writer: StreamWriter):
            connection = Connection(self, reader, writer)
            task = asyncio.create_task(connection.handleJson())
            self.connection_tasks.append(task)

        start_server_task = asyncio.start_server(on_connection, port=4242)
        async with await start_server_task as server:
            try:
                # TODO: see why I cannot use server.serve_forever()
                await server.start_serving()
                await server.wait_closed()
            except asyncio.CancelledError:
                for task in self.connection_tasks:
                    task.cancel()
                raise


class Connection:
    server: Server
    reader: StreamReader
    writer: StreamWriter

    def __init__(
            self,
            server: Server,
            reader: StreamReader,
            writer: StreamWriter
            ):
        self.server = server
        self.reader = reader
        self.writer = writer

    # async def handle(self):
    #     try:
    #         async for line in self.reader:
    #             self.writer.write(line)
    #             await self.writer.drain()
    #     except asyncio.CancelledError:
    #         # Connection task doesn't stop if connection is not closed
    #         print("Closing connection")
    #         self.writer.close()
    #         raise
    async def handleJson(self):
        try:
            async for line in self.reader:

                # Write response
                self.writer.write(line)
                await self.writer.drain()
        finally:
            self.writer.close()

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
    server = Server(task_master)

    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(task_master.run())
            tg.create_task(server.serve())
    except ExceptionGroup as exception_group:
        for exception in exception_group.exceptions:
            logging.error(exception)


if __name__ == "__main__":
    main()
