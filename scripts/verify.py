"""Run the supported local RunScope verification gates."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "web"


@dataclass(frozen=True)
class Gate:
    name: str
    command: tuple[str, ...]
    cwd: Path = ROOT


def executable(name: str) -> str:
    resolved = shutil.which(name)
    if resolved is None:
        raise RuntimeError(f"Required executable was not found: {name}")
    return resolved


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run formatting, lint, type, unit, build, and Compose configuration gates. "
            "Use --with-e2e after the seeded Compose stack is running."
        )
    )
    parser.add_argument(
        "--with-e2e",
        action="store_true",
        help="also run the Chromium workflow against the running Compose stack",
    )
    return parser.parse_args()


def gates(with_e2e: bool) -> list[Gate]:
    npm = executable("npm")
    docker = executable("docker")
    checks = [
        Gate("Python format", (sys.executable, "-m", "ruff", "format", "--check", ".")),
        Gate("Python lint", (sys.executable, "-m", "ruff", "check", ".")),
        Gate("Python types", (sys.executable, "-m", "mypy")),
        Gate("Python tests", (sys.executable, "-m", "pytest")),
        Gate("Frontend lint", (npm, "run", "lint"), WEB),
        Gate("Frontend types", (npm, "run", "typecheck"), WEB),
        Gate("Frontend tests", (npm, "test"), WEB),
        Gate("Frontend build", (npm, "run", "build"), WEB),
        Gate("Compose configuration", (docker, "compose", "config", "--quiet")),
    ]
    if with_e2e:
        checks.append(Gate("Chromium end to end", (npm, "run", "e2e"), WEB))
    return checks


def main() -> int:
    args = parse_args()
    try:
        checks = gates(args.with_e2e)
    except RuntimeError as exc:
        print(f"Verification cannot start: {exc}")
        return 2

    for index, gate in enumerate(checks, start=1):
        print(f"\n[{index}/{len(checks)}] {gate.name}")
        result = subprocess.run(gate.command, cwd=gate.cwd, check=False)
        if result.returncode != 0:
            print(f"\nFAILED: {gate.name} (exit {result.returncode})")
            return result.returncode
    print(f"\nAll {len(checks)} verification gates passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
