"""Download the AI Act from EUR-Lex and turn the HTML into clean lines of text (given).

EUR-Lex sometimes blocks automated downloads. If fetch fails, open ACT_URL in your browser,
save the page as data/raw/ai_act.html, and run the ingest script with --file.
When a consolidated version including the 2026 AI Omnibus amendments is published on EUR-Lex,
switch ACT_URL to it and re-run ingestion (the pipeline only re-embeds changed chunks).
"""

import re

import httpx

ACT_URL = "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=OJ:L_202401689"


def fetch_html(url: str = ACT_URL) -> str:
    r = httpx.get(url, timeout=60, follow_redirects=True, headers={"User-Agent": "ai-act-copilot/0.1 (study project)"})
    r.raise_for_status()
    return r.text


def html_to_text(html: str) -> str:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()
    text = soup.get_text("\n")
    lines = [re.sub(r"\s+", " ", ln.replace("\xa0", " ")).strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln)
