"""Phase 1 · Ingestion.   make test-phase P=1"""

from app.ingest.chunk import chunk_provision, header_for, split_paragraphs
from app.ingest.parse import Provision, parse_act
from app.ingest.pipeline import ingest_text
from app.retrieval.embed import HashEmbedder
from app.retrieval.store import InMemoryStore
from tests.helpers import sample_text


def test_parse_finds_provisions_in_order_and_skips_recitals():
    ids = [p.id for p in parse_act(sample_text())]
    assert ids == ["art-1", "art-3", "art-5", "art-6", "art-50", "art-99", "annex-iii"], ids


def test_parse_titles_and_chapters():
    by_id = {p.id: p for p in parse_act(sample_text())}
    assert by_id["art-5"].title == "Prohibited AI practices"
    assert by_id["art-5"].chapter == "CHAPTER II · PROHIBITED AI PRACTICES"
    assert by_id["art-6"].chapter == "CHAPTER III · HIGH-RISK AI SYSTEMS"
    assert by_id["annex-iii"].kind == "annex" and by_id["annex-iii"].number == "III" and by_id["annex-iii"].chapter == ""
    assert by_id["annex-iii"].title == "High-risk AI systems referred to in Article 6(2)"


def test_parse_body_lines_exclude_title_and_keep_cross_references():
    by_id = {p.id: p for p in parse_act(sample_text())}
    assert by_id["art-1"].lines[0] == "1."
    assert "Subject matter" not in by_id["art-1"].lines
    assert any("Article 6(2)" in ln for ln in by_id["art-5"].lines), "a cross-reference inside text is body text"


def test_parse_duplicate_keeps_the_one_with_content():
    art99 = [p for p in parse_act(sample_text()) if p.id == "art-99"]
    assert len(art99) == 1 and art99[0].lines and "35 000 000" in art99[0].text


def test_split_paragraphs():
    lines = ["Intro line", "1.", "First paragraph.", "(a) point a;", "2. Second paragraph."]
    assert split_paragraphs(lines) == ["Intro line", "1. First paragraph. (a) point a;", "2. Second paragraph."]
    assert split_paragraphs(["no numbers", "here either"]) == ["no numbers", "here either"]
    assert split_paragraphs([]) == []


def test_chunk_provision_headers_ids_metadata():
    p = Provision(id="art-5", kind="article", number="5", title="Prohibited AI practices",
                  chapter="CHAPTER II · PROHIBITED AI PRACTICES",
                  lines=["1. " + "a" * 100, "2. " + "b" * 100, "3. " + "c" * 100])
    chunks = chunk_provision(p, max_chars=250)
    assert [c.id for c in chunks] == ["art-5-0", "art-5-1"], [c.id for c in chunks]
    assert chunks[0].text.startswith(header_for(p) + "\n\n1. ")
    assert "2. " in chunks[0].text and "3. " in chunks[1].text
    assert chunks[1].metadata == {"chunk_index": 1, "n_chunks": 2}
    assert all(c.provision_id == "art-5" and c.citation == "Article 5" for c in chunks)


def test_chunk_long_paragraph_is_split_at_sentences():
    long_para = " ".join(f"Sentence number {i} is here." for i in range(60))
    p = Provision(id="art-9", kind="article", number="9", title="Risk management system", lines=["1. " + long_para])
    chunks = chunk_provision(p, max_chars=400)
    assert len(chunks) > 1
    header_len = len(header_for(p)) + 2
    assert all(len(c.text) - header_len <= 400 for c in chunks), "each body should respect max_chars"
    joined = " ".join(c.text[header_len:] for c in chunks)
    assert "Sentence number 59 is here." in joined, "no text may be lost"


def test_chunk_empty_provision_uses_title():
    p = Provision(id="art-2", kind="article", number="2", title="Scope", lines=[])
    chunks = chunk_provision(p)
    assert len(chunks) == 1 and chunks[0].text.endswith("Scope")


def test_ingest_is_idempotent():
    store, emb = InMemoryStore(), HashEmbedder()
    first = ingest_text(sample_text(), store, emb)
    assert first.provisions == 7 and first.chunks >= 7 and first.changed == first.chunks
    second = ingest_text(sample_text(), store, emb)
    assert second.changed == 0, "unchanged text must not be re-embedded"
    assert store.count() == first.chunks
