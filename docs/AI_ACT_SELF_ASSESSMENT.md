# AI Act self-assessment of this tool

*The copilot's own classification under the AI Act, reviewed by hand. It is not a legal opinion.*

## System description
The EU AI Act Compliance Copilot answers questions about the AI Act from its text and produces non-binding compliance assessments of AI systems described by users. It is decision support for product and compliance teams; a qualified person must review its outputs.

## Classification
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
- Inputs may contain personal data despite redaction (emails, IBANs and phone numbers are redacted; names and addresses are not). There is no automatic retention period yet: assessments, events and feedback are kept until deleted by the operator; deletion on request = delete the assessment, its events and related logs by id.
- Processors: the live demo sends redacted questions and descriptions to Groq (US) on its free tier, with no data processing agreement; it is intended for demo data only. A production deployment would use a provider with an EU region and a DPA, or a self-hosted model.

## Open points
- Define a retention period and automatic deletion for assessments, events and feedback.
- Replace the free-tier LLM API with a provider under a data processing agreement (or self-host) before handling real client data.
- Add rate limiting to the public UI.
- Detect names and addresses as personal data (NER-based redaction), not only emails, IBANs and phone numbers.
