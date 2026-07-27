"""Run a bounded RunScope demonstration through the public API."""

from __future__ import annotations

import argparse
import os
import time
from datetime import UTC, datetime
from typing import Any

import httpx

TERMINAL_STATUSES = {"SUCCEEDED", "FAILED", "CANCELLED"}


class DemoError(RuntimeError):
    """A safe, user-facing demonstration failure."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create a project and experiment, submit the registered Iris template, "
            "and wait for its durable terminal state."
        )
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("RUNSCOPE_DEMO_BASE_URL", "http://localhost:8000/api/v1"),
        help="RunScope API prefix (default: %(default)s)",
    )
    parser.add_argument(
        "--email",
        default=os.getenv("RUNSCOPE_DEMO_EMAIL", "researcher@runscope.dev"),
        help="Seeded local demonstration user (default: %(default)s)",
    )
    parser.add_argument(
        "--password",
        default=os.getenv("RUNSCOPE_DEMO_PASSWORD", "ResearcherDemo123!"),
        help="Seeded local password or RUNSCOPE_DEMO_PASSWORD",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=60.0,
        help="Maximum time to wait for execution (default: %(default)s)",
    )
    parser.add_argument(
        "--poll-seconds",
        type=float,
        default=0.5,
        help="REST polling interval (default: %(default)s)",
    )
    args = parser.parse_args()
    if args.timeout_seconds <= 0 or args.poll_seconds <= 0:
        parser.error("timeouts and polling intervals must be positive")
    return args


def require_json(response: httpx.Response, action: str) -> Any:
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        try:
            body = response.json()
            message = body.get("error", {}).get("message", response.text)
        except ValueError:
            message = response.text
        raise DemoError(f"{action} failed ({response.status_code}): {message}") from exc
    return response.json()


def require_object(response: httpx.Response, action: str) -> dict[str, Any]:
    data = require_json(response, action)
    if not isinstance(data, dict):
        raise DemoError(f"{action} returned an unexpected response")
    return data


def require_list(response: httpx.Response, action: str) -> list[Any]:
    data = require_json(response, action)
    if not isinstance(data, list):
        raise DemoError(f"{action} returned an unexpected response")
    return data


def run_demo(args: argparse.Namespace) -> None:
    base_url = str(args.base_url).rstrip("/")
    client_timeout = httpx.Timeout(10.0)
    with httpx.Client(base_url=base_url, timeout=client_timeout) as client:
        token_response = require_object(
            client.post(
                "/auth/sign-in",
                json={"email": args.email, "password": args.password},
            ),
            "Sign in",
        )
        token = token_response.get("access_token")
        if not isinstance(token, str):
            raise DemoError("Sign in did not return an access token")
        client.headers["Authorization"] = f"Bearer {token}"

        suffix = datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")
        project = require_object(
            client.post(
                "/projects",
                json={
                    "name": f"API demo {suffix}",
                    "description": "Created by the bounded scripts/demo.py workflow",
                },
            ),
            "Project creation",
        )
        experiment = require_object(
            client.post(
                "/experiments",
                json={
                    "project_id": project["id"],
                    "name": "Iris baseline",
                    "description": "Real scikit-learn execution through the public API",
                    "tags": ["demo", "iris"],
                },
            ),
            "Experiment creation",
        )
        run = require_object(
            client.post(
                "/runs",
                json={
                    "experiment_id": experiment["id"],
                    "template_key": "sklearn-iris-classification",
                    "template_version": "1.0.0",
                    "parameters": {
                        "n_estimators": 40,
                        "test_size": 0.2,
                        "random_state": 42,
                        "max_depth": 5,
                    },
                    "requested_cpu": 1.0,
                    "requested_memory_mb": 512,
                    "priority": 0,
                    "notes": "Created by scripts/demo.py",
                    "tags": ["demo"],
                },
            ),
            "Run submission",
        )
        run_id = run["id"]
        print(f"Submitted run {run_id}")

        deadline = time.monotonic() + args.timeout_seconds
        previous_status: str | None = None
        while time.monotonic() < deadline:
            run = require_object(client.get(f"/runs/{run_id}"), "Run status read")
            status = str(run["status"])
            if status != previous_status:
                print(f"  status: {status}")
                previous_status = status
            if status in TERMINAL_STATUSES:
                break
            time.sleep(args.poll_seconds)
        else:
            raise DemoError(
                f"Run {run_id} did not reach a terminal state within "
                f"{args.timeout_seconds:.1f} seconds"
            )

        if run["status"] != "SUCCEEDED":
            raise DemoError(
                f"Run {run_id} ended in {run['status']}: "
                f"{run.get('failure_message') or 'no safe failure message'}"
            )

        metrics = require_list(client.get(f"/runs/{run_id}/metrics"), "Metric read")
        artifacts = require_list(
            client.get(f"/runs/{run_id}/artifacts"),
            "Artifact metadata read",
        )
        print(f"Completed run: {base_url}/runs/{run_id}")
        print(f"Metrics recorded: {len(metrics)}")
        print(f"Artifacts recorded: {len(artifacts)}")
        print("Open the browser UI at http://localhost:5173 to inspect the run.")


def main() -> int:
    args = parse_args()
    try:
        run_demo(args)
    except (DemoError, httpx.RequestError, KeyError, TypeError, ValueError) as exc:
        print(f"Demo failed: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
