# RunScope Engineering Rules

These rules apply to the entire repository. More specific `AGENTS.md` files may
add constraints for a subtree but may not weaken these rules.

## Product boundaries

- RunScope is an educational, self-service platform for small CPU-based machine
  learning workloads.
- Execute only trusted, registered templates. Never accept arbitrary Python,
  shell commands, container images, or pickle uploads from users.
- Do not describe RunScope as a GPU scheduler, HPC system, distributed training
  platform, or production-scale cluster manager.
- Keep PostgreSQL, Redis, broker, storage, API, scheduler, and worker concerns
  behind explicit interfaces.

## Development workflow

- Read this file and the relevant files in `docs/` before each major phase.
- Build and test a working vertical slice before adding infrastructure around it.
- Use typed contracts and validate every external input.
- Keep modules small, cohesive, and explicit; prefer clarity over abstraction.
- Update documentation whenever behavior or architecture changes.
- Preserve unrelated user changes and never delete unrelated files.
- Never push code or open a pull request.
- Create a focused local commit only after a phase passes its relevant checks.

## Correctness and reliability

- Use real database-backed behavior after persistence is introduced.
- Centralize and test the run state machine.
- Use transactions for important state changes and optimistic concurrency for
  run transitions.
- Treat duplicate message delivery as normal and make consumers idempotent.
- Use finite timeouts and bounded retries.
- Workers must re-read durable state before executing or completing work.
- Never claim a test, build, benchmark, or manual workflow passed unless it was
  actually run successfully.
- Do not weaken tests to make them pass; fix root causes.

## Security and privacy

- Never commit `.env`, credentials, tokens, keys, or private user data.
- Do not log passwords, access tokens, authorization headers, or secret values.
- Use password hashing, short-lived JWT access tokens, and role checks.
- Treat local demonstration credentials as local-only and label them clearly.
- Store only artifact metadata in messages; never publish binary artifacts or
  secrets through the broker.

## Phase completion

Before committing a phase:

1. Run applicable formatting, linting, type checks, and tests.
2. Build the frontend when frontend code changed.
3. Validate Compose when infrastructure changed.
4. Review the diff and scan tracked files for secrets.
5. Update docs and record verification truthfully.

