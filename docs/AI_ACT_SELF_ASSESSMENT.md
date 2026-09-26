# AI Act self-assessment of this tool

*Dogfooding: run the copilot on itself, then review and complete this document by hand. Interviewers love this.*

## System description
The EU AI Act Compliance Copilot answers questions about the AI Act from its text and produces non-binding compliance assessments of AI systems described by users. It is decision support for product and compliance teams; a qualified person must review its outputs.

## Classification (draft — verify)
| Question | Answer | Basis |
|---|---|---|
| Prohibited practice (Art. 5)? | No | No manipulation, social scoring, biometrics or emotion recognition |
| General-purpose AI model? | No — it *uses* GPAI models via APIs | Art. 3, Art. 53 apply to the model providers |
| High-risk (Art. 6, Annex I/III)? | No | Not a safety component; not an Annex III use case; it does not make decisions about natural persons |
| Transparency (Art. 50)? | Yes | Interacts with people and generates text → disclose that it is an AI system |
| Role | Provider (if offered to others) / deployer (internal use) | Art. 3 definitions |

## Measures in place
- UI and API responses state that output is AI-generated decision support, not legal advice.
- Citations to the regulation are verified in code; unverifiable answers are flagged.
- Human-in-the-loop: clarifying questions; reports must be reviewed before use.
- AI literacy (Art. 4): README and UI explain limitations.
- Logging of model calls (llm_calls) for traceability; PII redaction before model calls.

## GDPR notes
- Inputs may contain personal data despite redaction; retention: ____ days; deletion on request: delete assessments, events and logs by id.
- Processors: LLM API provider (EU region / data processing agreement: ____).

## Open points
- ________________________________
