#!/usr/bin/env python3

import asyncio
import runner
import config
import logging


async def main():
    # Configure root logger
    logging.basicConfig(level=logging.INFO)
    try:
        await runner.TaskMaster(config.example()).run()
    except runner.TaskStartFailure as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
