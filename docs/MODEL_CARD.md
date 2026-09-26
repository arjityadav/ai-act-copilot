# Model card — Annex III area classifier

*Fill this in during Phase 6 and keep it up to date with every promoted version.*

## Overview
- **Model:** TF-IDF (1–2-grams) + logistic regression (class-balanced), scikit-learn.
- **Purpose:** fast second opinion on which Annex III area (if any) an AI system description belongs to. Used as a pre-screen inside the assessment pipeline; disagreement with the LLM classifier raises a review flag.
- **Not for:** making compliance decisions on its own; descriptions in languages other than English (not trained).
- **Current champion:** version __ (MLflow `models:/annex3-classifier@champion`), promoted on ____.

## Data
- **Seed:** 52 hand-written descriptions across 9 labels (`data/training/annex3_seed.csv`).
- **Synthetic:** __ rows generated with ______ (`scripts/generate_training_data.py`), then reviewed by hand: __ corrected, __ removed.
- **Label definitions:** Annex III areas of Regulation (EU) 2024/1689 as amended; "none" for systems outside Annex III.
- **Known gaps:** ________________________________

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
