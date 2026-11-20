# ARCHITECTURE.md

> Binding for every agent. Only the owner edits this file. The steward proposes changes
> through an issue. Keep it short: an agent reads it in every session.
> Replace every `TODO` below. Delete these quote lines when done.

## 1. What this system does
TODO: two or three sentences. Who uses it, what problem it solves, what it must never do.

## 2. Module map

| Area (matches `areas` in `.github/agents.yml`) | Path | Responsibility | May depend on |
|---|---|---|---|
| TODO `core` | `src/core/` | domain logic, no I/O | nothing |
| TODO `api` | `src/api/` | HTTP layer, request validation | `core` |
| TODO `storage` | `src/storage/` | persistence adapters | `core` |
| TODO `shared` | `src/shared/` | small utilities | nothing |

**Dependency direction:** TODO e.g. `api → core ← storage`. Arrows never point outward from `core`.

## 3. Invariants (violating one is always `[blocking]`)
1. TODO e.g. Domain logic in `core` performs no network, file or database I/O.
2. TODO e.g. All external input is validated at the boundary (`api`) before reaching `core`.
3. TODO e.g. Every database schema change ships as a forward-only migration with a rollback note.
4. TODO e.g. No secrets in code, config files or logs; read them from the environment.
5. TODO e.g. Public interfaces listed in §5 change only through an accepted ADR.

## 4. Conventions
- Language/runtime: TODO (version)
- Formatting/linting: TODO (tool + command) — style is never a review topic.
- Tests: TODO (framework, where they live, how to run: `TODO command`)
- Errors: TODO (e.g. typed errors in `core`, mapped to HTTP codes only in `api`)
- Logging: TODO (structured, no personal data)
- Configuration: TODO (env vars, documented in TODO)

## 5. Public interfaces (stable — changes need an ADR)
- TODO e.g. REST API under `/v1/` (spec: `docs/api/openapi.yaml`)
- TODO e.g. Database schema (migrations: `migrations/`)
- TODO e.g. CLI flags of `bin/tool`

## 6. Off-limits without the owner
- TODO e.g. `migrations/` (existing files are never edited)
- TODO e.g. `src/auth/`
- Anything listed as protected in `AGENTS.md` §1.

## 7. Accepted decisions
See `docs/adr/`. The most important ones:
- ADR-0001 — Multi-agent operating model
- TODO
