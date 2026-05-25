# Private A-Share Finance Knowledge Base Plan

This branch is an experiment and should not be merged into the upstream project until the workflow feels useful.

Version marker: this is the `codex-gpt5-finance-kb` experiment. See `docs/finance_kb_codex_provenance.md` before comparing or merging with any dsv4pro implementation.

## Goal

Build a private, local-first A-share research knowledge base from monitored NGA analysts such as 狼大. The system should preserve the original timestamped posts, extract structured theses, attach market context as it becomes available, and support later hindsight reviews without mixing future data into the original context.

## Principles

- Keep raw posts immutable.
- Separate what was knowable at post time from future outcomes.
- Store private context locally; do not commit positions, cookies, app secrets, or account credentials.
- Prefer simple files plus SQLite before adding vector databases.
- Let this project keep doing collection and notifications; keep research artifacts under a separate KB directory.

## Data Model

### Post

- `id`: stable event key.
- `analyst`: human label, for example `狼大`.
- `author_id`: NGA author id.
- `post_time`: timestamp from the post.
- `captured_at`: local capture timestamp.
- `subject`, `url`, `floor`.
- `content`: original text.
- `symbols`: stock codes and names inferred from text.
- `topics`: sectors, styles, and market themes inferred from text.

### Thesis

- `post_id`.
- `analyst`.
- `created_at`.
- `view_type`: `bullish`, `bearish`, `risk`, `watch`, `mixed`, or `unknown`.
- `horizon`: `intraday`, `short`, `swing`, `medium`, or `unknown`.
- `claim`: concise structured hypothesis.
- `conditions`: required conditions.
- `invalidation`: what would make the thesis wrong.

### Market Snapshot

- `as_of`: timestamp.
- `index_state`: major index context at post time.
- `hot_sectors`.
- `limit_up_count`.
- `turnover`.
- `notes`.

### Outcome

- `post_id`.
- `window`: `1d`, `3d`, `5d`, `20d`.
- `index_return`.
- `sector_return`.
- `mentioned_symbol_return`.
- `outcome_label`: for example `right_direction_early`, `right`, `wrong`, `unclear`.
- `review`.

## Folder Layout

```text
finance-kb/
  raw/
    nga/
    market/
  normalized/
    posts.jsonl
    theses.jsonl
  reviews/
    狼大/
  context/
    analyst_profiles.md
    watchlist.md
    positions.example.json
  finance_kb.sqlite
```

## Workflow

1. The watcher records posts under `AI_WORK_DIR/events/by_source/author_<id>.jsonl`.
2. `finance_kb/build_kb.py ingest` normalizes posts into `finance-kb/normalized/posts.jsonl` and SQLite.
3. `finance_kb/build_kb.py review` creates analyst review drafts grouped by month.
4. A later market-data step fills market snapshots and outcome windows.
5. Manual or AI review updates the review files, explicitly separating `at_post_context` and `future_outcome`.

## First Experiment Scope

- Build a local CLI with no new dependencies.
- Support source labels such as `狼大`.
- Read source history JSONL produced by this project.
- Generate normalized JSONL, SQLite tables, and monthly Markdown review drafts.
- Include a tiny sample fixture so the workflow can be tested without private data.

## Later Enhancements

- Market data connector for A-share daily and intraday snapshots.
- Trading calendar awareness for 1d/3d/5d/20d windows.
- Symbol name dictionary and sector taxonomy.
- Vector search over raw posts and review notes.
- Feishu command: `/kb 狼大 CPO 2026-05`.
- Scheduled post-close review job.
