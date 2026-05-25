# Finance KB Provenance

This document identifies the Codex-built version of the private A-share finance knowledge-base experiment.

## Codex Version

- Branch: `finance-kb-experiment`
- Initial commit: `feaf0bc Add private finance KB experiment scaffold`
- Model/agent: `Codex based on GPT-5`
- Created: `2026-05-25`
- Scope: local-first finance knowledge-base scaffold for timestamped NGA analyst posts, including normalization, SQLite export, query, and monthly review drafts.

## Separation From Other Experiments

Neal may also have another implementation built by `dsv4pro`. Treat that as a separate experiment unless explicitly merged by Neal.

When comparing versions, use these identifiers:

- Codex version: this branch and this provenance file.
- dsv4pro version: whatever branch, folder, or provenance marker Neal assigns to that work.

Do not assume files from one experiment belong to the other. If both versions touch the same module, compare behavior and data contracts before combining them.

## Data Boundary

Generated private KB data should remain outside git or under ignored paths such as `finance-kb/`. Do not commit real positions, private notes, cookies, API keys, Feishu secrets, or account credentials.
