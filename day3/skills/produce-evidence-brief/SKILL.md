---
name: produce-evidence-brief
description: Create concise, decision-ready evidence briefs from user-supplied sources, notes, or excerpts. Use for research summaries, clinical or technical evidence synthesis, source comparison, uncertainty assessment, safety-aware recommendations, and Markdown report artifacts.
---

# Produce an Evidence Brief

Create a structured synthesis without overstating what the supplied evidence
supports. Prefer a useful limitation statement over invented completeness.

## Workflow

1. Restate the decision question in one sentence.
2. Inventory the supplied sources or excerpts. Do not invent citations.
3. Extract claims and label each as sourced fact, interpretation, or proposal.
4. Note agreement, disagreement, evidence gaps, and material uncertainty.
5. Draft the brief using the required structure below.
6. If an artifact is requested, call `save_evidence_brief` with a descriptive
   filename and the complete Markdown brief.

## Required structure

- `# Evidence Brief: <topic>`
- `## Question`
- `## Executive summary`
- `## Evidence supplied`
- `## Key findings`
- `## Uncertainty and limitations`
- `## Recommended next steps`
- `## Sources` when source identifiers or URLs were supplied

Keep the executive summary to three to five sentences. Make recommendations
proportional to the evidence and identify who should verify consequential ones.

## Safety and integrity

- Never fabricate a source, quotation, statistic, or consensus claim.
- Distinguish missing evidence from evidence of no effect.
- For health topics, state that the brief is informational and not a diagnosis
  or treatment recommendation.
- Flag claims requiring professional, legal, security, or clinical review.
- Preserve meaningful disagreement instead of averaging it away.
- Say when current or external research tools were unavailable.
