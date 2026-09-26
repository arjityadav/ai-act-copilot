# Interview Questions — EU AI Act Copilot

Practice questions per phase, with model answers. Rewrite the answers in your own words; interviewers can tell when an answer is memorised.

---

## Phase 1 · Parsing, chunking, ingestion

### 1. Why did you chunk by articles and numbered paragraphs instead of fixed-size windows (e.g. 500 characters with overlap)?

**Answer.** Legal text has a structure that people and the model cite: "Article 5(1)", "Annex III point 4". Fixed windows ignore it:

- They cut through the middle of a paragraph, so an obligation ("the provider shall…") ends up split from its conditions ("…where the system is intended for…").
- A chunk can mix the end of Article 5 with the start of Article 6, so its embedding blurs two topics and its citation is ambiguous.
- Overlap only partly fixes this and costs extra storage and embedding time.

Structure-aware chunking parses the Act into provisions (article/annex, number, title, chapter), splits at numbered paragraphs and packs whole paragraphs up to a size limit. Only a paragraph that is too long on its own is split, at sentence ends. Every chunk maps to exactly one provision, so it carries an exact citation that Phase 3 can check in code.

**Trade-off to mention:** chunk sizes vary, and very short articles become small chunks. That's acceptable because precise citations matter more here than uniform sizes.

### 2. Each chunk starts with a header like `EU AI Act · Article 5 · Prohibited AI practices · CHAPTER II…`. Why put it inside the embedded text instead of only storing it as metadata?

**Answer.** Metadata doesn't affect the embedding; only the text does. A paragraph such as "2. The use of those systems shall be subject to…" means little on its own. With the header, the vector also encodes *which* article and topic it belongs to, so a question like "what are the prohibited practices?" matches it better, and keyword search can match "Article 5" literally. This is a cheap form of **contextual retrieval** (Anthropic's technique adds an LLM-written context sentence to each chunk; a deterministic header gets much of the benefit at no cost). The metadata is still stored separately for filtering and for building citations.

### 3. Your ingestion is idempotent. What does that mean, how is it achieved here, and why does it matter?

**Answer.** Idempotent means running it again on the same input leaves the system in the same state and does no unnecessary work. Here:

- Chunk ids are **deterministic** (`art-5-0`, `art-5-1`), derived from the structure rather than random UUIDs, so re-ingesting produces the same ids.
- Each chunk has a **content hash** (SHA-256 of its text). On upsert, a chunk is re-embedded only if its hash changed. A second run reports `0 new/changed`.

Why it matters: the AI Act is being amended (e.g. the 2026 Digital Omnibus). When a consolidated version comes out, re-running ingestion re-embeds only the changed provisions. That's faster and cheaper, it avoids duplicate chunks, and it's safe to retry after a crash or run on a schedule in CI.

---

## Phase 2 · Hybrid retrieval and metrics

**My results on the real Act (25 eval questions):**

| method  | recall@5 | MRR   |
|---------|----------|-------|
| vector  | 0.900    | 0.771 |
| keyword | 0.420    | 0.311 |
| hybrid  | 0.900    | 0.788 |

### 1. Why combine vector search and keyword search instead of using embeddings alone? Give an example where each fails on its own.

**Answer.** They fail in different ways:

- **Vector search** captures meaning: "Can I use AI to screen job applicants?" finds Annex III point 4 (employment) even though the words differ. It is weak on exact identifiers and numbers ("Article 50", "EUR 35 000 000", "CE marking"), which embeddings treat as fuzzy tokens.
- **Keyword search** (BM25 / Postgres full-text) matches exact terms, so "fines EUR 35 000 000" lands on Article 99. But it misses paraphrases and synonyms: "screen job applicants" shares few words with "recruitment or selection of natural persons".

Legal questions mix both kinds, so hybrid search covers both. On my eval set hybrid kept vector's recall@5 (0.90) and raised MRR from 0.771 to 0.788: the right chunk moves up when both searches agree on it.

**Honest follow-up:** keyword search alone is weak here (0.42 recall). Natural-language questions rarely use the exact wording of the regulation, so the gain from hybrid is small on this eval set. It matters most on identifier-heavy queries, which I should add more of to the eval set.

### 2. Explain Reciprocal Rank Fusion. Why fuse ranks instead of adding the scores, and what does the constant 60 do?

**Answer.** For every document: `score = Σ 1 / (k + rank)` over the result lists that contain it (rank starts at 1, k = 60). Then sort by that score.

- **Why ranks:** cosine similarity lies in 0–1 and BM25 scores are unbounded and depend on the query. Adding them would let one scale dominate, and normalising them is fragile. Ranks are always comparable, and RRF needs no weights or training.
- **Agreement wins:** a document ranked #2 and #1 (1/62 + 1/61 ≈ 0.0325) beats one ranked #1 in only one list (1/61 ≈ 0.0164).
- **The constant 60** damps the difference between top ranks. With k = 60, rank 1 (1/61) and rank 5 (1/65) score almost the same, so one list's top result can't outweigh consistent agreement. A small k makes the result depend heavily on each list's #1. 60 is the value from the original paper (Cormack et al., 2009) and works well without tuning.
- **Pitfall I hit:** RRF's `k` is this damping constant, not a top-k cutoff. RRF returns every id, and the cut happens afterwards.

### 3. Recall@5 vs MRR: what does each tell you, and which matters more when the top 5 chunks go into the LLM prompt?

**Answer.**

- **Recall@k:** the fraction of relevant chunks that appear in the top k. It answers "did the right evidence reach the LLM at all?"
- **MRR (Mean Reciprocal Rank):** the average of 1/rank of the first relevant chunk. It answers "how near the top was the first right answer?" Rank 1 → 1.0, rank 2 → 0.5, not found → 0.

When the top 5 go into the prompt, **recall@5 matters most**: if the right article isn't in the context, the LLM can't answer from it (and may hallucinate). MRR is the secondary metric, because LLMs pay more attention to content near the start of the context ("lost in the middle"), and a high MRR means you could shrink k to cut tokens and latency without losing recall.

Both metrics only mean something with a **labelled eval set** (here 25 questions with their correct provisions). That's what turns "retrieval feels better" into a number you can gate CI on.

**Next improvement to discuss:** add a cross-encoder reranker over the 30 fused candidates and measure whether MRR goes up without hurting recall@5.
