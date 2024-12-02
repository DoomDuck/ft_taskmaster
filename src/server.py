#!/usr/bin/env python3

import sys
import signal
import asyncio
import logging

import config

from typing import Optional, AsyncGenerator, Generator
from argparse import ArgumentParser, Namespace
from runner import TaskMaster, TaskStartFailure
from config import Configuration
from asyncio import StreamReader, StreamWriter
from asyncio.events import AbstractServer


cla = ArgumentParser(
    description='sum the integers at the command line')

cla.add_argument(
    "config_file",
    type=str,
    help="Yaml task configuration",
    default="./configs/default.yaml",
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
            task = asyncio.create_task(connection.handle())
            self.connection_tasks.append(task)

        async with await asyncio.start_server(on_connection, port=4242) as server:
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

    def __init__(self, server: Server, reader: StreamReader, writer: StreamWriter):
        self.server = server
        self.reader = reader
        self.writer = writer

    async def handle(self):
        try:
            async for line in self.reader:
                self.writer.write(line)
                await self.writer.drain()
        except asyncio.CancelledError:
            # Connection task doesn't stop if connection is not closed
            print("Closing connection")
            self.writer.close()
            raise


def main():
    "Program entry point"

    arguments = cla.parse_args()

    try:
        asyncio.run(start(arguments))
    except KeyboardInterrupt:
        pass


async def start(arguments: Namespace):
    logging.basicConfig(level=logging.INFO)

    try:
        configuration = config.load(arguments.config_file)
    except Exception as e:
        logging.error(f"Could not load configuration: {e}")
        return

    task_master = TaskMaster(configuration)
    server = Server(task_master)

    async with asyncio.TaskGroup() as tg:
        task_master_task = tg.create_task(task_master.run())
        serve_task = tg.create_task(server.serve())


if __name__ == "__main__":
    main()
