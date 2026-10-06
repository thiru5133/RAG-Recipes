# Traces

`*.jsonl` files in this folder are **local only** (see `.gitignore`). They are the live log from `scripts/collect_traces.py` and the Streamlit UI.

Rebuild:

```bash
python scripts/collect_traces.py --n 120 --rpm 25
```

The write-up of what we read lives in `taxonomy.md`, `notes.md`, and `WEEK5.md` at the repo root — not in the JSONL.
