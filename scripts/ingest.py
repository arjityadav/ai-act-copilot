"""Download (or read) the AI Act, ingest it into the store.   make ingest   /   make ingest FILE=data/raw/ai_act.html

Also saves the clean text to data/corpus/ai_act.txt, which CI's eval gate uses to build an
in-memory index (commit that file after your first ingest).
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings  # noqa: E402
from app.ingest.fetch import ACT_URL, fetch_html, html_to_text  # noqa: E402
from app.ingest.pipeline import ingest_text  # noqa: E402
from app.retrieval.embed import OllamaEmbedder  # noqa: E402
from app.retrieval.store import get_store  # noqa: E402

CORPUS = os.path.join("data", "corpus", "ai_act.txt")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", help="a saved EUR-Lex HTML page (if the download is blocked)")
    ap.add_argument("--url", default=ACT_URL)
    args = ap.parse_args()
    html = open(args.file, encoding="utf-8").read() if args.file else fetch_html(args.url)
    text = html_to_text(html)
    os.makedirs(os.path.dirname(CORPUS), exist_ok=True)
    open(CORPUS, "w", encoding="utf-8").write(text)
    s = get_settings()
    stats = ingest_text(text, get_store(s), OllamaEmbedder(s))
    print(
        f"{stats.provisions} provisions · {stats.chunks} chunks · {stats.changed} new/changed · {stats.seconds:.0f}s"
    )


if __name__ == "__main__":
    main()
