# Model card — Annex III area classifier

*Fill this in during Phase 6 and keep it up to date with every promoted version.*

## Overview
- **Model:** TF-IDF (1–2-grams) + logistic regression (class-balanced), scikit-learn.
- **Purpose:** fast second opinion on which Annex III area (if any) an AI system description belongs to. Used as a pre-screen inside the assessment pipeline; disagreement with the LLM classifier raises a review flag.
- **Not for:** making compliance decisions on its own; descriptions in languages other than English (not trained).
- **Current champion:** version __ (MLflow `models:/annex3-classifier@champion`), promoted on ____.

## Data
- **Seed:** 52 hand-written descriptions across 9 labels (`data/training/annex3_seed.csv`).
- **Synthetic:** 270 rows generated with `llama3.1:8b` via Ollama (`scripts/generate_training_data.py --per-label 30`), then reviewed row by row: **43 relabelled**, **72 removed** (32 ambiguous or nonsensical, 40 near-duplicates at TF-IDF cosine ≥ 0.7). Final dataset: **250 rows** (52 seed + 198 synthetic). The pre-review file is kept locally as `data/training/annex3.csv.bak` (gitignored).
- **Final label counts:** none 78 · essential_services 33 · education 29 · employment 27 · law_enforcement 21 · critical_infrastructure 20 · justice_democracy 15 · migration 14 · biometrics 13. Training uses `class_weight="balanced"` to compensate.
- **Main relabelling rules applied** (following the Act's own exclusions):
  - biometric **verification** (1:1 authentication) → `none` (excluded from Annex III 1(a)); emotion analysis of **text** → `none` (not biometric data); fatigue detection → `none` (physical states are not emotions, recital 18); medical image analysis → `none` (Annex I route)
  - components used **solely for cybersecurity** → `none` (recital 55); building HVAC, EV charging and irrigation → `none` (not critical infrastructure supply)
  - course/content **recommendations** → `none` (not admission or evaluation); student analytics mislabelled as employment → `education`
  - private loss prevention, insurance claims and healthcare evidence → `none` (not law enforcement)
  - tools helping **applicants** (not authorities), customs of goods, and travel-document verification (excluded in Annex III 7(d)) → `none`
  - election **forecasting** and administration (registration, ballot design) → `none` (only influencing voting behaviour is in Annex III 8(b))
- **Label definitions:** Annex III areas of Regulation (EU) 2024/1689 as amended; "none" for systems outside Annex III.
- **Known gaps:**
  - Almost all data is LLM-generated: a narrow, marketing-like writing style ("Our AI-powered X streamlines…"). Real user descriptions are messier; scores on this test set likely **overestimate** real-world performance. A hand-written test set of real descriptions is the most valuable next step.
  - `biometrics`, `migration` and `justice_democracy` have only 13–15 examples each after review; per-class F1 for them is noisy.
  - Hard boundary cases were **removed** rather than labelled (e.g. place-based crime forecasting, workflow optimisation, corporate training), so the model has not learned those boundaries and may be unreliable on them.
  - The review was done with AI assistance (Claude) against the text of the Act, not by a legal expert; a qualified person should audit the labels. `data/training/review_2026-09-27.py` records every relabel and deletion with its reason (the audit trail).

## Evaluation (held-out 25%, stratified)
| Label | F1 |
|---|---|
| macro average | |
| none | |
| biometrics | |
| critical_infrastructure | |
| education | |
| employment | |
| essential_services | |
| law_enforcement | |
| migration | |
| justice_democracy | |

## Promotion gate
Macro F1 ≥ 0.70, at least 0.01 better than the champion, and no class drops by more than 0.10.

## Monitoring
Weekly PSI on description length and predicted-label distribution (`.github/workflows/drift.yml`). PSI > 0.25 opens an issue → review recent inputs, label, retrain.

## Limitations and risks
- Synthetic data can share the generator's blind spots and phrasing.
- Short or vague descriptions are unreliable; the LLM classifier and a human remain responsible.
- ____________________
