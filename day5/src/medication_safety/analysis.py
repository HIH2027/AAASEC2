"""Deterministic contraindication analysis and untrusted-data guardrails.

Every clinical determination in this module is a pure function of the validated
profile. No generative model decides whether a risk exists, how severe it is, or
how it ranks. That boundary is the whole point of the design: a language model
that fabricates a citation or invents a severity would be indistinguishable from
a correct one at the point of use.
"""

import re
from typing import Any

from .models import (
    SEVERITY_PRIORITY,
    Finding,
    PatientProfile,
    SafetyAssessment,
)
from .rules import (
    BLEEDING_CLUSTER_RULE,
    BLEEDING_RISK_WITH_WARFARIN,
    BRADYCARDIA_RULE,
    BRADYCARDIA_TRIPLE,
    PAIR_RULES,
)

# Instruction-like text arriving through a data field is never a medicine name.
INJECTION_PATTERNS = (
    r"ignore\s+(all\s+)?previous",
    r"disregard\s+(all\s+)?(prior|previous)",
    r"system\s+prompt",
    r"developer\s+message",
    r"execute\s+(this|the following|command)",
    r"read\s+.*\.ssh",
    r"reveal\s+.*(secret|token|key)",
    r"you\s+are\s+now",
    r"new\s+instructions",
)

# Direct identifiers must never enter the pipeline. This is a de-identified tool.
IDENTIFIER_PATTERNS = (
    (r"\b\d{10}\b", "a national ID or record number"),
    (r"\bMRN\b", "a medical record number"),
    (r"\bmedical\s+record\s+number\b", "a medical record number"),
    (r"\bpatient\s+name\b", "a patient name"),
    (r"\b\d{2}[/-]\d{2}[/-]\d{4}\b", "a date of birth"),
)

BOUNDARY = (
    "This output supports, but does not replace, a licensed pharmacist and the "
    "treating prescriber, who retain clinical responsibility.",
    "The patient must not independently start, stop or change any medicine.",
    "Verify every action against current policy, formulary, the authorised "
    "interaction reference and current product labelling.",
    "Educational and research prototype. Not an authorised medical device and "
    "not for clinical use.",
)

PROFILE_LABELS = {
    "patient_description": "Description",
    "age": "Age",
    "warfarin_indication": "Indication for warfarin",
    "dvt_timing": "DVT timing",
    "inr": "INR",
    "egfr": "eGFR",
    "crcl": "CrCl",
    "serum_creatinine": "Serum creatinine",
    "dialysis": "Dialysis",
    "liver_status": "Liver status",
}

# Parameters a pharmacist needs before any finding can be confirmed.
REQUESTED_FIELDS = {
    "potassium": "Potassium",
    "magnesium": "Magnesium",
    "qtc_ms": "QTc",
    "heart_rate": "Heart rate",
    "digoxin_level": "Digoxin level",
    "liver_status": "Liver status/tests",
    "cbc_hemoglobin": "CBC/hemoglobin",
    "aspirin_clopidogrel_indication": "Aspirin/clopidogrel indication",
}

NOT_PROVIDED = "Not provided"


def _normalise(name: str) -> str:
    return " ".join(name.lower().strip().split())


def _render(value: Any) -> str:
    """Render a value, never imputing a missing one as normal."""
    if value is None:
        return NOT_PROVIDED
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _scan_untrusted_text(text: str) -> None:
    """Reject instruction-like or identifying content in a data field."""
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            raise ValueError(
                "Medication data failed the prompt-injection guardrail"
            )
    for pattern, description in IDENTIFIER_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            raise ValueError(
                f"Input rejected: it appears to contain {description}. "
                "This tool accepts de-identified profiles only."
            )


def _finding_from_rule(rule: dict, medications: list[str]) -> Finding:
    sources = [url for url in rule["sources"] if url.startswith("https://")]
    if not sources:
        # A clinical claim with no resolvable source is never displayed.
        raise ValueError(f"Rule {rule['rule_id']} has no resolvable source")
    return Finding(
        rule_id=rule["rule_id"],
        medications=medications,
        severity=rule["severity"],
        action_class=rule["action_class"],
        reason=rule["reason"],
        action=rule["action"],
        sources=sources,
    )


def _patient_modifiers(profile: PatientProfile) -> list[str]:
    """Patient-specific weighting, kept separate from baseline severity."""
    modifiers: list[str] = []
    if profile.age is not None and profile.age >= 75:
        modifiers.append(
            f"Age {profile.age} (75 or older) increases vulnerability to "
            "adverse drug effects."
        )
    if profile.egfr is not None and profile.egfr < 60:
        modifiers.append(
            f"Reduced eGFR ({_render(profile.egfr)}) increases renal and "
            "toxicity monitoring needs."
        )
    if profile.liver_status is None:
        modifiers.append(
            "Liver status is missing and is not assumed to be normal."
        )
    if profile.dialysis:
        modifiers.append("Patient is on dialysis; clearance assumptions change.")
    if not modifiers:
        modifiers.append("No patient-specific modifier was triggered.")
    return modifiers


def _inr_context(profile: PatientProfile) -> list[str]:
    if profile.warfarin_indication is None or profile.inr is None:
        return []
    if _normalise(profile.warfarin_indication) != "dvt":
        return []
    if profile.inr >= 2:
        return []
    return [
        f"INR {profile.inr:g} is below the usual 2.0-3.0 warfarin range for DVT.",
        "Do not increase warfarin automatically; first verify INR trend, "
        "adherence, diet, treatment plan and interacting medicines.",
    ]


def assess_profile(raw_profile: dict[str, Any]) -> SafetyAssessment:
    """Validate an untrusted profile and apply the verified rule set."""
    profile = PatientProfile.model_validate(raw_profile)

    for medication in profile.medications:
        _scan_untrusted_text(medication.name)
        for extra in (medication.dose, medication.frequency, medication.route):
            if extra:
                _scan_untrusted_text(extra)
    for free_text in (
        profile.patient_description,
        profile.warfarin_indication,
        profile.dvt_timing,
        profile.liver_status,
        profile.aspirin_clopidogrel_indication,
    ):
        if free_text:
            _scan_untrusted_text(free_text)

    names = {_normalise(item.name) for item in profile.medications}
    findings: list[Finding] = []

    for rule in PAIR_RULES:
        if rule["meds"].issubset(names):
            findings.append(_finding_from_rule(rule, sorted(rule["meds"])))

    if "warfarin" in names:
        bleeding_agents = sorted(names & BLEEDING_RISK_WITH_WARFARIN)
        if bleeding_agents:
            findings.append(
                _finding_from_rule(
                    BLEEDING_CLUSTER_RULE, ["warfarin", *bleeding_agents]
                )
            )

    if BRADYCARDIA_TRIPLE.issubset(names):
        findings.append(
            _finding_from_rule(BRADYCARDIA_RULE, sorted(BRADYCARDIA_TRIPLE))
        )

    findings.sort(key=lambda item: SEVERITY_PRIORITY[item.severity])

    severity_counts = {level: 0 for level in SEVERITY_PRIORITY}
    for finding in findings:
        severity_counts[finding.severity] += 1

    profile_summary = {
        label: _render(getattr(profile, field))
        for field, label in PROFILE_LABELS.items()
    }

    missing = [
        label
        for field, label in REQUESTED_FIELDS.items()
        if getattr(profile, field) is None
    ]

    return SafetyAssessment(
        profile_summary=profile_summary,
        findings=findings,
        patient_modifiers=_patient_modifiers(profile),
        inr_context=_inr_context(profile),
        missing_information=missing,
        severity_counts=severity_counts,
        boundary=list(BOUNDARY),
    )
