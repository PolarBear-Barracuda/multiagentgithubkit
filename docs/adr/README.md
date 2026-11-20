# Architecture Decision Records

An ADR records one decision that is expensive to reverse, affects more than one module,
or sets a precedent. Accepted ADRs bind every agent, the steward included.

## Process
1. Open an **ADR proposal** issue (template) describing the problem and options.
2. The steward (or any agent asked to) opens a PR that **adds** `docs/adr/NNNN-short-title.md`
   copied from `0000-template.md`, with `Status: Proposed`. Use the next free number.
3. The owner reviews. Only the owner changes the status to `Accepted` or `Rejected`.
4. Existing ADRs are never edited except by the owner. To change a decision, write a
   new ADR that says `Supersedes: ADR-NNNN`, and the owner marks the old one `Superseded`.

## Index
| # | Title | Status |
|---|---|---|
| 0001 | Multi-agent operating model | Accepted |
