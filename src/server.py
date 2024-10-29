#!/usr/bin/env python3

import asyncio
import runner
import config
import logging
import sys
import argparse


def setup() -> config.Configuration:
    parser = argparse.ArgumentParser(
        description='sum the integers at the command line')

    parser.add_argument(
        "config_file",
        default="./configs/default.yaml",
        type=str,
        help="Yaml task configuration"
    )

    args = parser.parse_args()

    # Configure root logger
    logging.basicConfig(level=logging.INFO)

    return config.Configuration(
        config.read_and_parse_yaml(args.config_file)
    )
 


async def handle_connections():
    async def on_connection(reader, writer):
        print("Got net client")
        while True:
            line = await reader.readline()
            if not line:
                break
            writer.write(line)
            await writer.drain()
        print("Connnection closed")

    server = await asyncio.start_server(on_connection, port=4242)

    await server.serve_forever()

async def main():
    "Program entry point"
    try:
        configuration = setup()
    except Exception as e:
        print("Check your .yaml file sommething is wrong with", e.args)
        sys.exit(1)

    try:
        task_master = runner.TaskMaster(configuration)
        await task_master.run()
    except runner.TaskStartFailure as e:
        logging.error(f"could not start {e}")


if __name__ == "__main__":
    asyncio.run(handle_connections())
    # asyncio.run(main())
