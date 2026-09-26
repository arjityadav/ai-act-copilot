`make ingest` writes the cleaned text of the AI Act here as `ai_act.txt`. Commit it after your
first ingest: CI's eval gate builds an in-memory index from it (`evals/run_evals.py --in-memory`).
