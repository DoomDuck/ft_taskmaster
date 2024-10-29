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

    # parser.add_argument(
    #     'integers', metavar='int', nargs='+', type=int,
    #     help='an integer to be summed')

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

async def main():
    try:
        configuration = setup()
    except Exception as e:
        print("Check your .yaml file sommething is wrong with", e.args)
        sys.exit(1)

    try:
        await runner.TaskMaster(configuration).run()
        pass
    except runner.TaskStartFailure as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
