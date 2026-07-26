import argparse
import asyncio

from runscope_api.db import SessionFactory
from runscope_api.seed import seed_demo_users


async def seed() -> None:
    async with SessionFactory() as session:
        created = await seed_demo_users(session)
    print(f"Seed complete: {created} demonstration users created")


def main() -> None:
    parser = argparse.ArgumentParser(description="RunScope maintenance commands")
    parser.add_argument("command", choices=["seed"])
    args = parser.parse_args()
    if args.command == "seed":
        asyncio.run(seed())


if __name__ == "__main__":
    main()
