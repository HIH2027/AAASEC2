"""The language layer must never widen its remit."""

from medication_safety.agent import (
    _deterministic_summary,
    _deterministic_verdict,
    _known_medications,
    _parse_verdict_and_summary,
    _safe_summary,
    _safe_verdict,
    _valid_plan_item,
    format_report,
    generate_ai_plan,
)
from medication_safety.analysis import assess_profile
from medication_safety.models import QUICK_VERDICT_VALUES

ASSESSMENT = assess_profile(
    {
        "age": 78,
        "egfr": 42,
        "medications": [
            {"name": "Ketoconazole"},
            {"name": "Simvastatin"},
        ],
    }
)

NO_FINDINGS = assess_profile(
    {"age": 40, "medications": [{"name": "Paracetamol"}, {"name": "Vitamin D"}]}
)


def test_clean_model_phrasing_is_accepted() -> None:
    candidate = (
        "One contraindicated interaction was identified between ketoconazole "
        "and simvastatin. Pharmacist confirmation is required."
    )
    summary, source = _safe_summary(ASSESSMENT, candidate)
    assert summary == candidate
    assert source == "model"


def test_directive_phrasing_falls_back_to_deterministic() -> None:
    summary, source = _safe_summary(
        ASSESSMENT, "The patient should stop taking simvastatin immediately."
    )
    assert source == "deterministic"
    assert summary == _deterministic_summary(ASSESSMENT)


def test_reassuring_phrasing_falls_back() -> None:
    summary, source = _safe_summary(
        ASSESSMENT, "There is no interaction of concern here."
    )
    assert source == "deterministic"


def test_invented_severity_falls_back() -> None:
    # No MODERATE finding exists, so the model may not claim one.
    _, source = _safe_summary(ASSESSMENT, "A moderate interaction was found.")
    assert source == "deterministic"


def test_model_supplied_url_falls_back() -> None:
    _, source = _safe_summary(
        ASSESSMENT, "See https://example.com/interaction for details."
    )
    assert source == "deterministic"


def test_reasoning_leak_falls_back() -> None:
    _, source = _safe_summary(
        ASSESSMENT, "Here is my thinking process: analyze user input step-by-step."
    )
    assert source == "deterministic"


def test_empty_and_overlong_output_falls_back() -> None:
    assert _safe_summary(ASSESSMENT, "   ")[1] == "deterministic"
    assert _safe_summary(ASSESSMENT, "word " * 200)[1] == "deterministic"


def test_deterministic_summary_states_the_top_finding() -> None:
    summary = _deterministic_summary(ASSESSMENT)
    assert "contraindicated" in summary
    assert "ketoconazole + simvastatin" in summary
    assert "licensed pharmacist" in summary


def test_deterministic_summary_never_gives_an_all_clear() -> None:
    summary = _deterministic_summary(NO_FINDINGS)
    assert "does not mean no interaction exists" in summary


def test_report_includes_sources_severity_and_boundary() -> None:
    report = format_report(ASSESSMENT, _deterministic_summary(ASSESSMENT))
    assert "Severity: CONTRAINDICATED" in report
    assert "Action: AVOID" in report
    assert "https://dailymed.nlm.nih.gov" in report
    assert "does not replace" in report
    assert "Liver status: Not provided" in report


# ---------- quick verdict: constrained-vocabulary guardrail ----------


def test_deterministic_verdict_matches_the_top_finding() -> None:
    assert _deterministic_verdict(ASSESSMENT) == "STOP AND CONFIRM"  # CONTRAINDICATED
    assert _deterministic_verdict(NO_FINDINGS) == "NO ACTION NEEDED"


def test_deterministic_verdict_is_always_in_the_closed_vocabulary() -> None:
    for case in (ASSESSMENT, NO_FINDINGS):
        assert _deterministic_verdict(case) in QUICK_VERDICT_VALUES


def test_exact_allowed_phrase_is_accepted_case_insensitively() -> None:
    assert _safe_verdict("monitor closely") == "MONITOR CLOSELY"
    assert _safe_verdict("  URGENT REVIEW  ") == "URGENT REVIEW"


def test_near_miss_phrase_is_rejected_not_coerced() -> None:
    # A close paraphrase is not "close enough" — the vocabulary is closed.
    assert _safe_verdict("URGENT REVIEW NEEDED") is None
    assert _safe_verdict("Stop & Confirm") is None
    assert _safe_verdict("") is None


def test_parse_verdict_and_summary_splits_the_two_lines() -> None:
    raw = "VERDICT: MONITOR CLOSELY\nSUMMARY: One finding requires monitoring."
    verdict, summary = _parse_verdict_and_summary(raw)
    assert verdict == "MONITOR CLOSELY"
    assert summary == "One finding requires monitoring."


def test_parse_tolerates_a_model_that_ignores_the_format() -> None:
    verdict, summary = _parse_verdict_and_summary("just some free text")
    assert verdict is None
    assert summary == "just some free text"


# ---------- AI-suggested plan: genuinely generated, so guarded harder ----------


def test_known_medications_come_only_from_findings() -> None:
    assert _known_medications(ASSESSMENT) == {"ketoconazole", "simvastatin"}


def test_grounded_suggestion_is_accepted() -> None:
    known = _known_medications(ASSESSMENT)
    assert _valid_plan_item(
        "Consider an alternative statin given the ketoconazole interaction", known
    )


def test_suggestion_naming_an_unlisted_medication_is_rejected() -> None:
    known = _known_medications(ASSESSMENT)
    # "lisinopril" is not part of this case; a suggestion should not introduce it.
    assert not _valid_plan_item(
        "Consider switching the patient to lisinopril instead", known
    )


def test_suggestion_with_a_specific_dose_is_rejected() -> None:
    known = _known_medications(ASSESSMENT)
    assert not _valid_plan_item("Give simvastatin 10 mg once daily", known)


def test_suggestion_with_directive_phrasing_is_rejected() -> None:
    known = _known_medications(ASSESSMENT)
    assert not _valid_plan_item("Stop taking simvastatin immediately", known)


def test_overlong_suggestion_is_rejected() -> None:
    known = _known_medications(ASSESSMENT)
    assert not _valid_plan_item("x" * 200, known)


def test_generate_ai_plan_without_findings_is_declined() -> None:
    result = generate_ai_plan(NO_FINDINGS)
    assert result.accepted is False
    assert result.plan is None


def test_generate_ai_plan_requires_an_api_key(monkeypatch) -> None:
    import pytest

    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
        generate_ai_plan(ASSESSMENT)


def test_placeholder_suggestion_is_rejected() -> None:
    # A model that echoes the prompt's example shape back ("...") is not a
    # suggestion, and passed every content-based check before this guard.
    known = _known_medications(ASSESSMENT)
    assert not _valid_plan_item("...", known)
    assert not _valid_plan_item("N/A", known)
    assert not _valid_plan_item("TBD", known)
