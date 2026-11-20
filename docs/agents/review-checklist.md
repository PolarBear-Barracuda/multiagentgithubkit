# Review checklist

Use on every PR. Each "no" is a candidate `[blocking]` comment only if it falls under the
blocking criteria in `AGENTS.md` §6. Otherwise it's a `[suggestion]` or nothing.

## Correctness
- [ ] Every acceptance criterion in the linked issue is implemented.
- [ ] Each changed behavior has a test that would fail without the change.
- [ ] Error paths handled: invalid input, empty/null, timeouts, partial failure.
- [ ] Boundaries: off-by-one, max sizes, pagination ends, time zones, unicode.
- [ ] Concurrency: shared state, retries that aren't idempotent, race conditions.
- [ ] No silent behavior change for existing callers.

## Scope and architecture
- [ ] Every changed file is needed for this issue.
- [ ] Dependency direction and module boundaries in `ARCHITECTURE.md` respected.
- [ ] No new public interface the issue didn't ask for.
- [ ] No duplicated abstraction (a second way to do something there's already a way to do).

## Security
- [ ] All external input validated at the boundary.
- [ ] No injection risk (SQL, shell, path traversal, template, deserialization).
- [ ] No secrets, tokens or personal data in code, logs, fixtures or error messages.
- [ ] Authorization checked where data is read or changed, not only where it's displayed.
- [ ] No new network calls, file writes or subprocesses the issue didn't call for.

## Tests
- [ ] Tests check behavior, not implementation details.
- [ ] No tests removed, loosened, or skipped (CI also checks this).
- [ ] Tests are deterministic: no real network, no sleeps for timing, fixed seeds and clocks.

## Operability
- [ ] Failures are logged with enough context to debug, without sensitive data.
- [ ] Migrations are forward-only and safe to run on live data.
- [ ] Config changes documented.
