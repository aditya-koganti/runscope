# Security

## Demonstration identity

RunScope uses locally seeded users, one-way password hashing, JWT bearer access
tokens, and viewer/researcher/administrator roles. Tokens are held in browser
memory for the initial implementation and cleared on sign-out. This is not an
enterprise identity system: there is no SSO, MFA, account recovery, refresh-token
rotation, organization isolation, or centralized policy engine.

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
- Broker payloads and metrics labels contain no credentials.
- MinIO keys and database credentials are never returned by public endpoints.
- Artifact names are normalized and downloads use safe attachment headers.

## Known risks

The local credential model, bearer-token browser storage, shared project
visibility, demonstration infrastructure credentials, and non-HA dependencies
are unsuitable for untrusted production tenants. Production work would require
OIDC, TLS everywhere, secret management, tenant isolation, rate limiting,
malware/content controls, network policy, audit export, and independent review.

