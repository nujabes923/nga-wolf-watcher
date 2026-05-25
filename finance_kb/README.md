# Finance KB Experiment

This folder is an experimental private A-share knowledge-base scaffold.

It is intentionally independent from the watcher runtime. The watcher still collects NGA posts; this module reads the saved AI history and builds research artifacts.

Version marker: `codex-gpt5-finance-kb`. See `VERSION.md` and `docs/finance_kb_codex_provenance.md`. Keep this separate from any dsv4pro experiment until Neal explicitly decides to merge ideas.

## Quick Sample

```powershell
python -m finance_kb.build_kb sample
python -m finance_kb.build_kb ingest --source finance-kb/raw/nga/sample_wolf_history.jsonl
python -m finance_kb.build_kb review
python -m finance_kb.build_kb query CPO
```

Outputs:

- `finance-kb/normalized/posts.jsonl`
- `finance-kb/normalized/theses.jsonl`
- `finance-kb/finance_kb.sqlite`
- `finance-kb/reviews/狼大/YYYY-MM.md`

## With Real Watcher Data

Use the source history produced by the AI work directory:

```powershell
python -m finance_kb.build_kb ingest --source "C:\path\to\.ai_agent_workspace\events\by_source\author_150058.jsonl" --kb-dir "C:\Users\Neal\Documents\Codex\finance-kb"
python -m finance_kb.build_kb review --kb-dir "C:\Users\Neal\Documents\Codex\finance-kb"
```

On Windows PowerShell, prefer the default analyst label when it is `狼大`; passing non-ASCII command-line arguments can be console-encoding dependent.

Keep the generated KB private. Do not commit real positions or private notes.
