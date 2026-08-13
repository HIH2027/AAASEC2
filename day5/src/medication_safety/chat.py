"""Grounded follow-up chat over a completed assessment.

The chat can explain findings that already exist. It cannot produce new clinical
determinations, and it is not a general medical assistant: a question whose
answer is not in the assessment is answered with "not in this assessment"
rather than from model knowledge. Free-text chat about medicines is exactly
where a decision-support tool starts to *drive* management instead of informing
it, so the same output validation used for the summary applies here too.
"""

import json
import os

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from .agent import DIRECTIVE_PHRASES, LEAK_PHRASES
from .analysis import _scan_untrusted_text
from .models import ChatReply, SafetyAssessment

load_dotenv()

MAX_QUESTION_LENGTH = 400
MAX_HISTORY_TURNS = 6

SYSTEM_PROMPT = """You answer a licensed pharmacist's questions about ONE
completed medication safety assessment, supplied as JSON.

Hard rules:
- Answer only from the JSON. If it does not contain the answer, say that the
  assessment does not cover it and suggest which parameter or reference would.
- Never introduce a medication, interaction, severity or number not in the JSON.
- Never advise starting, stopping or changing a medicine or dose. State what the
  assessment found and that the pharmacist decides.
- Do not include URLs; sources are displayed separately.
- At most four sentences, plain professional English."""

REFUSAL = (
    "I can only explain what is in this assessment, and I could not answer that "
    "safely. Please review the findings, their sources, and the missing "
    "information list above, and confirm with the treating prescriber."
)


def _deterministic_answer(assessment: SafetyAssessment, question: str) -> str:
    """Answer common questions from the assessment without a model."""
    text = question.lower()
    findings = assessment.findings

    if any(word in text for word in ("missing", "need", "required", "parameter")):
        if not assessment.missing_information:
            return "All requested parameters were supplied for this profile."
        return (
            "The assessment lists "
            f"{len(assessment.missing_information)} parameters as not provided: "
            + ", ".join(assessment.missing_information)
            + ". Each is reported as absent rather than assumed normal."
        )

    if any(
        word in text
        for word in (
            "urgent",
            "worst",
            "highest",
            "most severe",
            "priority",
            "critical",
            "first",
            "top finding",
            "biggest",
        )
    ):
        if not findings:
            return "No verified rule matched this medication list."
        top = findings[0]
        return (
            f"The highest-severity finding is {' + '.join(top.medications)} "
            f"({top.severity}, action class {top.action_class}, rule "
            f"{top.rule_id}). {top.reason}"
        )

    if any(word in text for word in ("source", "citation", "reference", "evidence")):
        urls = {url for finding in findings for url in finding.sources}
        return (
            f"This assessment cites {len(urls)} source(s) from product labelling, "
            "listed under each finding above."
        )

    if any(word in text for word in ("modifier", "age", "renal", "kidney", "egfr")):
        return " ".join(assessment.patient_modifiers)

    if any(word in text for word in ("how many", "count", "number of finding")):
        counts = ", ".join(
            f"{count} {level.lower()}"
            for level, count in assessment.severity_counts.items()
            if count
        )
        return f"{len(findings)} verified finding(s): {counts or 'none'}."

    # Named-medication lookup.
    for finding in findings:
        if any(name in text for name in finding.medications):
            return (
                f"{' + '.join(finding.medications)} is flagged {finding.severity} "
                f"(action class {finding.action_class}). {finding.reason} "
                f"{finding.action}"
            )

    return (
        "That is not covered by this assessment. It contains "
        f"{len(findings)} finding(s), patient-specific modifiers, and a list of "
        "parameters that were not provided. A licensed pharmacist should confirm "
        "anything beyond that against the authorised interaction reference."
    )


def _validate_answer(assessment: SafetyAssessment, candidate: str) -> tuple[str, str]:
    """Apply the same remit checks used for the summary."""
    normalized = " ".join(candidate.split())
    lowered = normalized.lower()

    rejected = (
        not normalized
        or len(normalized) > 800
        or "http" in lowered
        or any(phrase in lowered for phrase in DIRECTIVE_PHRASES)
        or any(phrase in lowered for phrase in LEAK_PHRASES)
    )

    if not rejected:
        for level, count in assessment.severity_counts.items():
            if count == 0 and level.lower() in lowered:
                rejected = True
                break

    if rejected:
        return REFUSAL, "refused"
    return normalized, "model"


def answer_question(
    assessment: SafetyAssessment,
    question: str,
    history: list[dict] | None = None,
    *,
    offline: bool = False,
) -> ChatReply:
    """Answer one grounded follow-up question about the assessment."""
    question = " ".join(question.split())
    if not question:
        raise ValueError("Question must not be empty")
    if len(question) > MAX_QUESTION_LENGTH:
        raise ValueError(
            f"Question must be {MAX_QUESTION_LENGTH} characters or fewer"
        )

    # The question is untrusted input like any other field.
    _scan_untrusted_text(question)

    if offline:
        return ChatReply(
            answer=_deterministic_answer(assessment, question),
            source="deterministic",
        )

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required unless offline mode is used")

    model = ChatOpenAI(
        model=os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3.5-lightning:free"),
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        temperature=0,
        max_tokens=300,
        timeout=60,
        max_retries=1,
    )

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(
            content="ASSESSMENT JSON:\n" + json.dumps(assessment.model_dump(), indent=2)
        ),
    ]
    for turn in (history or [])[-MAX_HISTORY_TURNS:]:
        role = turn.get("role")
        content = " ".join(str(turn.get("content", "")).split())[:MAX_QUESTION_LENGTH]
        if not content:
            continue
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))
    messages.append(HumanMessage(content=question))

    response = model.invoke(messages)
    answer, source = _validate_answer(assessment, str(response.content))
    if source == "refused":
        # Still give the pharmacist something useful, from the trusted layer.
        answer = _deterministic_answer(assessment, question)
        source = "deterministic"
    return ChatReply(answer=answer, source=source)
