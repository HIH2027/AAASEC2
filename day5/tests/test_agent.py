"""The language layer must never widen its remit."""

from medication_safety.agent import (
    _deterministic_summary,
    _safe_summary,
    format_report,
)
from medication_safety.analysis import assess_profile

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
