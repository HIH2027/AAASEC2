# Medication Safety Agent

A pharmacist-facing drug–drug contraindication and interaction checker.
Capstone project for **Advanced Agentic AI Systems Engineering** at
**SDAIA Academy**, August 9–13, 2026.

> **Educational and research prototype.** Not an authorised medical device and
> not for clinical use. It supports, and does not replace, a licensed pharmacist
> and the treating prescriber. Accepts de-identified profiles only. Zero clinical
> evaluations have been performed and zero patient records processed.

## Problem

Polypharmacy in older adults generates more interaction alerts than any
pharmacist can meaningfully act on. Conventional checkers detect drug pairs well
but issue the same warning regardless of the patient's age, renal function or
laboratory values — and, worse, treat a missing value as a normal one.

The consequences are measured. Around 6% of patients experience preventable
harm, 12% of it severe or fatal, with drug-related incidents the largest single
category at 25% (Panagioti, *BMJ* 2019). In Saudi Arabia, 67.2% of
community-dwelling adults aged ≥60 had at least one potential drug–drug
interaction and 23.2% of those were severe (Khawagi, *Front Pharmacol* 2026).
Meanwhile alert override rates run at 46.2–96.2%, and the categories overridden
least appropriately are precisely the geriatric and renal ones most relevant to
this population (Poly, *JMIR Med Inform* 2020).

## Purpose

This agent separates two things conventional tools conflate:

- **Baseline severity** — comes from product labelling and is identical for
  every patient.
- **Patient-specific modifiers** — age, renal function, unknown liver status,
  dialysis — reported alongside, never folded silently into the severity.

Absent parameters are declared "Not provided" and collected into an explicit
request list rather than imputed as normal. Every clinical statement is bound to
a resolvable source. The workflow stops at a licensed pharmacist.

## Agent Design

The agent is a hybrid workflow, not a prompt-forwarding wrapper:

1. Authenticate to a scope-protected MCP service.
2. Retrieve a de-identified profile through `get_patient_profile`.
3. Validate the schema; reject instruction-like content and direct identifiers.
4. Apply seven verified deterministic rules in Python.
5. Rank findings by severity and attach sources.
6. Give only the finished findings to the LLM, for phrasing alone.
7. Validate that phrasing, or fall back to a deterministic summary.

**No generative model decides anything clinical.** Whether a risk exists, how
severe it is, which action applies and how findings rank are pure functions of
the validated profile. The model is confined to wording, and its output is
checked before display. `--offline` removes the model entirely; every other
stage runs unchanged.

## The Rule Set

Seven rules, each bound to DailyMed labelling. Severity is baseline; the action
class states what the pharmacist is being asked to do.

| ID | Medications | Severity | Action |
| --- | --- | --- | --- |
| PAIR-01 | ketoconazole + simvastatin | CONTRAINDICATED | AVOID |
| PAIR-02 | amiodarone + simvastatin | MAJOR | CONSULT |
| PAIR-03 | amiodarone + warfarin | MAJOR | MONITOR |
| PAIR-04 | amiodarone + digoxin | MAJOR | MONITOR |
| PAIR-05 | spironolactone + ibuprofen | MAJOR | MONITOR |
| CLUSTER-01 | warfarin + any of aspirin, clopidogrel, ibuprofen, fluoxetine | MAJOR | CONSULT |
| CLUSTER-02 | amiodarone + digoxin + metoprolol succinate | MAJOR | MONITOR |

An unmatched pair means "no verified rule fired", never "no interaction
exists". The interface says so explicitly rather than implying an all-clear.

## Architecture

```mermaid
flowchart LR
    U[Pharmacist] --> W[Browser dashboard]
    U --> C[CLI]
    W -->|POST /api/analyze| B[Starlette backend]
    B --> A[Agent workflow]
    C --> A
    A -->|Bearer token, read:patient| M[Scope-protected FastMCP service]
    M -->|De-identified profile| V[Schema, injection and identifier guardrails]
    V --> D[Seven deterministic rules]
    D --> R[Findings, severity, sources, missing data]
    R --> L[LLM phrasing only]
    L --> G[Output validation]
    G -->|accepted| O[Review]
    G -->|rejected| F[Deterministic summary]
    F --> O
    A -. trace .-> S[LangSmith]
```

## Source Tree

```text
day5/
|-- README.md
|-- GUARDRAILS.md
|-- CAPSTONE.md
|-- pyproject.toml
|-- .env.example
|-- src/
|   `-- medication_safety/
|       |-- agent.py       # workflow and constrained AI phrasing
|       |-- analysis.py    # deterministic engine and guardrails
|       |-- rules.py       # the seven verified rules
|       |-- models.py      # validated data contracts
|       |-- client.py      # authenticated MCP client
|       |-- server.py      # scope-protected MCP tools
|       |-- check_auth.py  # authentication evidence matrix
|       |-- cli.py         # command-line interface
|       |-- web.py         # Starlette dashboard backend
|       `-- static/        # dashboard HTML, CSS, JavaScript
`-- tests/
    |-- test_analysis.py   # detection, severity, sources, guardrails
    |-- test_agent.py      # the language layer's remit
    `-- test_web.py        # routes and secret containment
```

## Agent Stack

| Layer | Technology | Reason |
| --- | --- | --- |
| Agent workflow | Python and LangChain messages | Explicit, testable control over every step |
| Clinical logic | Pure Python rule table | Reproducible and inspectable; no model involvement |
| Model access | OpenRouter | One API across compatible models |
| Protected tool | FastMCP | Standard tool protocol with scope-based authorization |
| Validation | Pydantic | Strict contracts before untrusted data reaches the model |
| Dashboard | Starlette + plain HTML/CSS/JS | Server-side execution, no build step, no browser-side secrets |
| Observability | LangSmith | Traces the live phrasing call |
| Tests | pytest | 38 tests over rules, guardrails, and routes |

## Installation

```powershell
cd day5
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Edit `.env` and add your real keys. Never commit it.

## Configuration

```env
OPENROUTER_API_KEY=your-openrouter-key
OPENROUTER_MODEL=your-model-id
LANGSMITH_API_KEY=your-langsmith-key
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=AAASEC2-Capstone
MCP_URL=http://localhost:8010/mcp
MCP_PORT=8010
MCP_STUDENT_TOKEN=replace-with-a-student-token
MCP_CLINICAL_TOKEN=replace-with-a-clinical-token
```

The static tokens are for a local course demonstration only.

## Usage

Terminal 1 — the protected MCP service:

```powershell
.\.venv\Scripts\python.exe -m medication_safety.server
```

Terminal 2 — the review:

```powershell
.\.venv\Scripts\python.exe -m medication_safety.cli --offline
```

Terminal 3 — the browser dashboard at <http://127.0.0.1:8080>:

```powershell
.\.venv\Scripts\python.exe -m medication_safety.web
```

Tests, and the authentication evidence matrix:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

```powershell
.\.venv\Scripts\python.exe -m medication_safety.check_auth
```

## Browser Dashboard

| Route | Method | Purpose |
| --- | --- | --- |
| `/` | GET | Dashboard page |
| `/health` | GET | Liveness check, returns status and rule count |
| `/api/analyze` | POST | Runs the agent, returns the assessment as JSON |

`POST /api/analyze` accepts `{"mode": "offline"}` or `{"mode": "live"}` and
defaults to `offline`, so opening the page never spends an LLM request. The page
shows the profile, each finding with severity, action class, reasoning and
sources, patient-specific modifiers, INR context, missing information, and the
boundary statement.

The browser only sends a mode and receives the assessment. The OpenRouter key
and MCP token stay in the server process. Agent failures return a generic `502`
so credentials cannot leak through an exception message, and all values are
rendered with `textContent` so untrusted data cannot become markup.

Note that `/mcp` is a machine-to-machine endpoint; a browser gets `401` there,
which is correct. Port 8080 is the only page meant to be opened.

## Example Output

```text
VERIFIED FINDINGS: 7

1. ketoconazole + simvastatin  [PAIR-01]
Severity: CONTRAINDICATED
Action: AVOID
Reason: Oral ketoconazole is a strong CYP3A4 inhibitor and can markedly
increase simvastatin exposure, myopathy and rhabdomyolysis risk.
Sources:
- https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=57e81e13-...

MISSING INFORMATION NEEDED FOR CONFIRMATION
- Potassium: Not provided
- Magnesium: Not provided
...
```

## Demonstration Evidence

Verified on August 13, 2026 against the running MCP service:

```text
38 passed

FAIL no token -> patient profile: HTTPStatusError
FAIL wrong token -> patient profile: HTTPStatusError
PASS student token -> service info
FAIL student token -> patient profile: ToolError
PASS clinical token -> patient profile
```

The middle three rows are the point: the student credential authenticates
successfully and reads public metadata, yet the patient profile stays hidden
from it. Authentication and authorization are demonstrably separate.

On the sample profile the agent returns 7 findings — 1 contraindicated, 6
major — with `ketoconazole + simvastatin` ranked first, 8 parameters listed as
missing, and no value imputed. Both dashboard modes were checked in a browser
at <http://127.0.0.1:8080>.

**Output validation fired against a real model.** In live mode the configured
free model (`nvidia/nemotron-3.5-lightning:free`) returned 973 characters
beginning "Here's a thinking process: 1. Analyze User Input…", leaking its raw
chain-of-thought. The guardrail rejected it and the deterministic summary was
displayed instead, with the interface reporting the source as "Deterministic".
This is the guardrail working as designed, but it also means live mode never
displays model phrasing with this particular model — see Limitations.

## Limitations

- Seven rules is a deliberately small, auditable set, not clinical coverage.
- Zero clinical evaluations performed; sensitivity, specificity, PPV and
  false-negative rate are unmeasured and no performance figure is claimed.
- The configured free reasoning model leaks chain-of-thought, so the output
  guardrail rejects it every time and live mode always falls back to the
  deterministic summary. Set `OPENROUTER_MODEL` to a non-reasoning model to see
  model phrasing accepted.
- LangSmith tracing was intermittently unreachable during verification
  (read timeouts to `api.smith.langchain.com`); the agent runs correctly
  regardless, since tracing is out-of-band.
- Sample profile is in-memory rather than a real record system; no EHR
  integration.
- Static tokens suit a local demonstration only.
- The dashboard binds to localhost and has no sign-in of its own.

## Future Work

- Expand the rule table with a structured false-negative search.
- Replace static tokens with OIDC and short-lived credentials.
- Retrospective validation on de-identified cases under ethics approval, then
  silent prospective evaluation with no influence on care.
- Add sign-in and per-user roles to the dashboard.
- Add evaluation datasets and alert-quality metrics in LangSmith.

## Team

| Member | GitHub | Contribution |
| --- | --- | --- |
| Repository owner | `@HIH2027` | Agent design, rule set, MCP security, dashboard, tests, documentation |

## Course Information

Developed for **Advanced Agentic AI Systems Engineering** at **SDAIA Academy**,
August 9–13, 2026. SDAIA Academy GitHub: https://github.com/SDAIAAcademy

*Evidence sources: Panagioti M, et al. BMJ 2019;366:l4185 · Khawagi WY, et al.
Front Pharmacol 2026;17:1830900 · Poly TN, et al. JMIR Med Inform 2020;8(7):e15653.*
