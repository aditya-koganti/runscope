# Event Contracts

## Envelope v1

All Kafka-compatible messages use UTF-8 JSON and the following stable envelope:

```json
{
  "event_id": "uuid",
  "event_version": 1,
  "event_type": "run.submitted",
  "occurred_at": "2026-01-01T00:00:00Z",
  "correlation_id": "uuid-or-request-id",
  "run_id": "uuid-or-null",
  "worker_id": "uuid-or-null",
  "payload": {}
}
```

Unknown additive payload fields are ignored. Unsupported envelope versions are
rejected to a bounded dead-letter path and logged without secret values.
Partition keys use `run_id` for run events and `worker_id` for worker events.

## Event catalog

| Event type | Producer | Required payload |
| --- | --- | --- |
| `run.submitted` | API | template key/version, requested resources, priority |
| `run.scheduling` | Scheduler | attempt, scheduling timestamp |
| `run.assigned` | Scheduler | lease token, lease expiry, requested resources |
| `run.started` | Worker | attempt number, template version |
| `run.progress` | Worker | progress in `[0,1]`, optional phase |
| `run.log` | Worker | sequence, level, message |
| `run.metric` | Worker | name, numeric value, step |
| `run.succeeded` | Worker | artifact count, duration |
| `run.failed` | Worker | stable failure code, safe message, retryable flag |
| `run.cancel.requested` | API | requested by, requested at |
| `run.cancelled` | Worker | acknowledged at |
| `worker.registered` | Worker | name and total capacity |
| `worker.heartbeat` | Worker | available capacity, count, status |

No envelope carries credentials, tokens, full model artifacts, or unbounded logs.
Consumers insert `(event_id, consumer_name)` before applying side effects in the
same transaction. Repeated events become successful no-ops.

