# API Design

## Conventions

The prefix is `/api/v1`. JSON uses snake_case. Collection responses contain
`items`, `page`, `page_size`, `total`, and `pages`. Sorting uses allow-listed
`sort` and `direction` values. Errors use:

```json
{
  "error": {
    "code": "run_invalid_transition",
    "message": "Run cannot transition from SUCCEEDED to RUNNING",
    "details": {},
    "correlation_id": "..."
  }
}
```

The API returns 400 for malformed commands, 401 for missing/invalid identity,
403 for denied roles, 404 for absent resources, 409 for state/version conflicts,
422 for contract validation, and 503 when required dependencies are unavailable.

## Endpoints

| Area | Endpoints |
| --- | --- |
| Authentication | `POST /auth/sign-in`, `GET /auth/me` |
| Projects | `GET/POST /projects`, `GET/PATCH/DELETE /projects/{id}` |
| Experiments | `GET/POST /experiments`, `GET/PATCH/DELETE /experiments/{id}` |
| Templates | `GET /templates`, `GET /templates/{key}` |
| Runs | `GET/POST /runs`, `GET /runs/{id}`, `POST /runs/{id}/cancel`, `POST /runs/{id}/retry`, `PATCH /runs/{id}/metadata`, `POST /runs/compare` |
| Run data | `GET /runs/{id}/logs`, `/metrics`, `/events`, `/artifacts`, `/stream`; `GET /runs/{id}/artifacts/{artifact_id}/download` |

`GET /runs/{id}/stream` is an authenticated `text/event-stream` response. The
web client uses streaming fetch rather than putting JWTs in query strings. Live
event IDs are deduplicated client-side; REST resources remain the recovery
contract.
| Workers | `GET /workers`, `GET /workers/{id}`, `POST /workers/register`, `POST /workers/{id}/heartbeat` |
| Platform | `GET /health`, `/ready`, `/platform/dependencies`, `/platform/summary`, `/metrics` |

## Command rules

- Run creation validates the selected enabled template schema and resource bounds.
- Mutation endpoints require researcher or administrator roles.
- Researchers may cancel/retry runs they created; administrators may control all.
- Viewers receive no mutation controls in the UI and remain blocked by the API.
- Artifact downloads authorize the parent run before streaming content and use
  attachment-safe filenames.
- Compare accepts two to five distinct visible run IDs and returns aligned
  parameters, final metrics, and series data.

## Live stream

`GET /runs/{id}/stream` is `text/event-stream`. Each frame has an event ID,
event kind, and versioned JSON body. The client sends `Last-Event-ID` on
reconnect. Redis accelerates fan-out; a cursor-based REST refresh recovers gaps.
