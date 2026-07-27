import argparse
import asyncio

from runscope_api.db import SessionFactory
from runscope_api.seed import seed_demo_data


async def seed() -> None:
    async with SessionFactory() as session:
        users, templates = await seed_demo_data(session)
    print(f"Seed complete: {users} demonstration users and {templates} training templates created")


def main() -> None:
    parser = argparse.ArgumentParser(description="RunScope maintenance commands")
    parser.add_argument("command", choices=["seed"])
    args = parser.parse_args()
    if args.command == "seed":
        asyncio.run(seed())


if __name__ == "__main__":
    main()
