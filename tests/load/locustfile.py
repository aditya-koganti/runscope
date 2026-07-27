import os
import random
import time
from typing import Any

from locust import HttpUser, between, events, tag, task
from locust.exception import StopUser

ASSIGNED_OR_LATER = {
    "SCHEDULING",
    "RUNNING",
    "SUCCEEDED",
    "FAILED",
    "CANCELLING",
    "CANCELLED",
}


class RunScopeUser(HttpUser):
    """Authenticated control-plane workload with opt-in mutating scenarios."""

    wait_time = between(1, 3)

    def on_start(self) -> None:
        email = os.getenv("RUNSCOPE_LOAD_EMAIL", "researcher@runscope.dev")
        password = os.getenv("RUNSCOPE_LOAD_PASSWORD", "ResearcherDemo123!")
        with self.client.post(
            "/auth/sign-in",
            json={"email": email, "password": password},
            name="/auth/sign-in",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure("Load-test sign-in failed")
                raise StopUser()
            token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {token}"}
        self.experiment_id = os.getenv("RUNSCOPE_LOAD_EXPERIMENT_ID")
        self.run_ids: list[str] = []
        self._refresh_context()
        if not self.experiment_id:
            raise StopUser("Seed at least one experiment or set RUNSCOPE_LOAD_EXPERIMENT_ID")

    def _refresh_context(self) -> None:
        if not self.experiment_id:
            response = self.client.get(
                "/experiments?page=1&page_size=1&sort=created_at&direction=desc",
                headers=self.headers,
                name="/experiments",
            )
            if response.ok:
                items = response.json().get("items", [])
                if items:
                    self.experiment_id = items[0]["id"]
        response = self.client.get(
            "/runs?page=1&page_size=20&sort=created_at&direction=desc",
            headers=self.headers,
            name="/runs",
        )
        if response.ok:
            self.run_ids = [item["id"] for item in response.json().get("items", [])]

    def _submit_slow_run(self) -> str | None:
        if not self.experiment_id:
            return None
        payload: dict[str, Any] = {
            "experiment_id": self.experiment_id,
            "template_key": "slow-demonstration",
            "template_version": "1.0.0",
            "parameters": {
                "duration_seconds": 2,
                "interval_seconds": 0.25,
                "fail_intentionally": False,
            },
            "requested_cpu": 0.5,
            "requested_memory_mb": 256,
            "priority": 0,
            "tags": ["load-test"],
        }
        with self.client.post(
            "/runs",
            headers=self.headers,
            json=payload,
            name="/runs (submit)",
            catch_response=True,
        ) as response:
            if response.status_code != 201:
                response.failure(f"Run submission returned {response.status_code}")
                return None
            run_id = str(response.json()["id"])
            self.run_ids.append(run_id)
            return run_id

    @tag("read")
    @task(4)
    def list_projects_and_experiments(self) -> None:
        self.client.get(
            "/projects?page=1&page_size=20&sort=created_at&direction=desc",
            headers=self.headers,
            name="/projects",
        )
        self.client.get(
            "/experiments?page=1&page_size=20&sort=created_at&direction=desc",
            headers=self.headers,
            name="/experiments",
        )

    @tag("read")
    @task(4)
    def read_run_detail(self) -> None:
        if not self.run_ids:
            self._refresh_context()
            return
        run_id = random.choice(self.run_ids)
        self.client.get(
            f"/runs/{run_id}",
            headers=self.headers,
            name="/runs/:id",
        )

    @tag("read")
    @task(2)
    def read_platform_summary(self) -> None:
        self.client.get(
            "/platform/summary",
            headers=self.headers,
            name="/platform/summary",
        )

    @tag("sse")
    @task(1)
    def open_live_update_connection(self) -> None:
        if not self.run_ids:
            self._refresh_context()
            return
        run_id = random.choice(self.run_ids)
        with self.client.get(
            f"/runs/{run_id}/stream",
            headers=self.headers,
            name="/runs/:id/stream",
            stream=True,
            timeout=(3, 3),
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"SSE returned {response.status_code}")
                return
            first_line = next(response.iter_lines(), b"")
            if first_line not in (b"retry: 2000", "retry: 2000"):
                response.failure("SSE retry preamble was not received")
            response.close()

    @tag("submission")
    @task(1)
    def submit_run(self) -> None:
        if os.getenv("RUNSCOPE_LOAD_ENABLE_MUTATIONS", "false").lower() == "true":
            self._submit_slow_run()

    @tag("scheduler")
    @task(1)
    def measure_scheduler_assignment(self) -> None:
        if os.getenv("RUNSCOPE_LOAD_ENABLE_MUTATIONS", "false").lower() != "true":
            return
        run_id = self._submit_slow_run()
        if run_id is None:
            return
        started = time.perf_counter()
        deadline = started + 15
        while time.perf_counter() < deadline:
            response = self.client.get(
                f"/runs/{run_id}",
                headers=self.headers,
                name="/runs/:id (assignment poll)",
            )
            if response.ok and response.json().get("status") in ASSIGNED_OR_LATER:
                events.request.fire(
                    request_type="CUSTOM",
                    name="submission-to-assignment",
                    response_time=(time.perf_counter() - started) * 1000,
                    response_length=0,
                    exception=None,
                    context={},
                )
                return
            time.sleep(0.2)
        events.request.fire(
            request_type="CUSTOM",
            name="submission-to-assignment",
            response_time=(time.perf_counter() - started) * 1000,
            response_length=0,
            exception=TimeoutError("Run remained queued for more than 15 seconds"),
            context={},
        )
