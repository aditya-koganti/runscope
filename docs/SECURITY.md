# Security

## Demonstration identity

RunScope uses locally seeded users, one-way password hashing, JWT bearer access
tokens, and viewer/researcher/administrator roles. Tokens are held in browser
memory for the initial implementation and cleared on sign-out. This is not an
enterprise identity system: there is no SSO, MFA, account recovery, refresh-token
rotation, organization isolation, or centralized policy engine.

Passwords use Argon2 through `pwdlib`. Access tokens are HS256 JWTs with issuer,
subject, role, issued-at, and expiration claims and a 30-minute local default.
The three documented `@runscope.dev` accounts and passwords exist only after the
explicit local seed command.

## Authorization

Every protected API query resolves the current user and performs server-side
role/ownership checks. Hiding a frontend control is convenience, not a security
boundary. Artifact access is authorized through its run.

## Execution boundary

Workers resolve a template key/version through a static trusted registry. User
input is validated against a Pydantic model and passed as data. Run parameters
cannot select modules, code, shell commands, filesystem paths, container images,
or arbitrary datasets.

## Secrets and sensitive data

- Configuration is environment-based; `.env` is ignored and `.env.example`
  contains placeholders only.
- Logs redact authorization, cookie, password, token, and secret fields.
- Structured exception logs retain the exception type for diagnosis but omit
  exception text that could contain connection strings or other sensitive data.
- Broker payloads and metrics labels contain no credentials.
- MinIO keys and database credentials are never returned by public endpoints.
- Artifact names are normalized and downloads use safe attachment headers.
- Public 500 responses use a stable message and correlation ID rather than
  exposing internal exception details.

## Known risks

The local credential model, bearer-token browser storage, shared project
visibility, demonstration infrastructure credentials, and non-HA dependencies
are unsuitable for untrusted production tenants. Production work would require
OIDC, TLS everywhere, secret management, tenant isolation, rate limiting,
malware/content controls, network policy, audit export, and independent review.

The 2026-07-27 frontend dependency review upgraded the application to React
19.2.7, React Router 8.3.0, Vite 7.3.6, and a Node 22.22 baseline. The latest
executed `npm audit --audit-level=high` reported zero vulnerabilities. The
frontend container rebuild uses `npm ci`, so the audited lockfile is also the
build input.

Python dependency auditing is configured as a blocking CI job. A local
`pip-audit` execution was not performed because this environment did not permit
sending the dependency inventory to an external vulnerability service. Local
Docker Scout image scans were not executed for the same disclosure reason.
GitHub Actions performs Trivy high/critical image scans plus repository
misconfiguration and secret scans; those remote jobs are configured but have
not been claimed as locally passing.
