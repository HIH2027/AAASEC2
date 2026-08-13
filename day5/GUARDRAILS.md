# Guardrails and Threat Model

This agent produces clinical text. The failure that matters is not a crash; it
is a confident, well-formatted, wrong statement that a busy pharmacist accepts.
Every control below exists to make that specific failure hard.

## The central boundary

**No generative model decides anything clinical.** Whether a risk exists, how
severe it is, which action class applies, and how findings rank are all pure
functions of the validated profile in `analysis.py` and the rule table in
`rules.py`. The model receives findings that are already final and is asked
only to phrase them.

This is an empirical choice, not a stylistic one. A language model that
fabricates a citation or invents a severity is indistinguishable from a correct
one at the point of use, so it is never given the opportunity.

## Untrusted input

The MCP response is untrusted even though the service is authenticated.
Authentication establishes who may call the tool; it does not prove that every
stored value is safe to place in a prompt.

- Scope-based MCP authorization: `read:public` reaches service metadata,
  `read:patient` is required for the profile itself.
- Pydantic validates every type, range, and length; `extra="forbid"` rejects
  unexpected keys rather than carrying them.
- Instruction-like text in any data field (medicine name, dose, frequency,
  route, free-text status) is rejected before model use.
- Direct identifiers are rejected: long digit runs, `MRN`, "medical record
  number", "patient name", and date-of-birth patterns. The tool accepts
  de-identified profiles only.

## Missing data is never imputed

An absent parameter becomes `None`, renders as "Not provided", and is added to
the missing-information list. It is never silently treated as normal. Treating
a missing potassium or eGFR as normal is the exact behaviour this project was
written to avoid.

Patient-specific modifiers (age 75+, eGFR below 60, unknown liver status,
dialysis) are reported separately from baseline severity, so that labelling-
derived severity is never quietly rewritten per patient.

## Citations

Every finding carries at least one `https://` source drawn from the rule table.
A rule with no resolvable source raises rather than displaying an unsourced
clinical claim. The model is forbidden from emitting URLs, and any output
containing `http` is rejected — citations come only from the deterministic
layer.

## Output validation

The model's phrasing is accepted only if it stays within its remit. It is
replaced by a deterministic summary when it is empty, longer than 600
characters, contains a URL, leaks reasoning, names a severity level that has a
zero count, or contains a directive phrase such as "stop taking", "discontinue",
"increase the dose", "is safe to", or "no interaction".

The interface always shows which layer produced the text, so a reader can tell
model phrasing from the deterministic fallback.

## Secrets

The browser posts a mode and receives an assessment. The OpenRouter key and the
MCP bearer token stay in the server process. Agent exceptions are returned as a
generic `502` so a credential cannot leak through an exception message, and a
test asserts that a key embedded in an exception never reaches the response.

Item text is rendered with `textContent`, never `innerHTML`, so untrusted data
cannot become markup.

## Known limits

- Seven rules is a deliberately small, auditable set. An unmatched pair means
  "no verified rule fired", never "no interaction exists"; the interface says so
  explicitly rather than implying an all-clear.
- Static tokens suit a local course demonstration only. Production needs OIDC,
  short-lived credentials, and audit logging.
- Zero clinical evaluations have been performed and zero patient records
  processed. Sensitivity, specificity, PPV and false-negative rate are
  unmeasured; no performance figure is claimed.
- The free model endpoint's terms permit prompt logging. It is unsuitable for
  identifiable patient data, none has been sent to it, and it must be replaced
  before any real use.
