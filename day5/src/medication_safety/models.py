"""Validated data contracts for patient profiles and safety findings.

A missing parameter is represented as ``None`` and rendered as "Not provided".
It is never imputed as a normal value, because a silently normalised absent
value is the failure mode this project exists to avoid.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

NOT_PROVIDED = "Not provided"

Severity = Literal["CONTRAINDICATED", "MAJOR", "MODERATE", "MINOR"]

# What the pharmacist is being asked to do, kept separate from severity.
ActionClass = Literal["AVOID", "MONITOR", "CONSULT"]

SEVERITY_PRIORITY: dict[str, int] = {
    "CONTRAINDICATED": 0,
    "MAJOR": 1,
    "MODERATE": 2,
    "MINOR": 3,
}


def _blank_to_none(value: Any) -> Any:
    """Treat empty and sentinel values as genuinely absent."""
    if isinstance(value, str) and value.strip().lower() in {
        "",
        "not provided",
        "unknown",
        "n/a",
    }:
        return None
    if value == []:
        return None
    return value


class Medication(BaseModel):
    """One medication line from a de-identified profile."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    dose: str | None = Field(default=None, max_length=60)
    frequency: str | None = Field(default=None, max_length=80)
    route: str | None = Field(default=None, max_length=40)

    @field_validator("dose", "frequency", "route", mode="before")
    @classmethod
    def _normalise_optional(cls, value: Any) -> Any:
        return _blank_to_none(value)


class PatientProfile(BaseModel):
    """A de-identified clinical profile.

    ``extra="forbid"`` is a privacy control, not a style choice: a stray
    ``patient_name`` or ``mrn`` key is rejected instead of quietly carried.
    """

    model_config = ConfigDict(extra="forbid")

    medications: list[Medication] = Field(min_length=1, max_length=50)

    age: int | None = Field(default=None, ge=0, le=120)
    warfarin_indication: str | None = Field(default=None, max_length=80)
    dvt_timing: str | None = Field(default=None, max_length=80)
    inr: float | None = Field(default=None, ge=0, le=20)
    egfr: float | None = Field(default=None, ge=0, le=250)
    crcl: float | None = Field(default=None, ge=0, le=250)
    serum_creatinine: float | None = Field(default=None, ge=0, le=30)
    dialysis: bool | None = None
    liver_status: str | None = Field(default=None, max_length=120)
    potassium: float | None = Field(default=None, ge=0, le=15)
    magnesium: float | None = Field(default=None, ge=0, le=10)
    qtc_ms: int | None = Field(default=None, ge=0, le=900)
    heart_rate: int | None = Field(default=None, ge=0, le=300)
    digoxin_level: float | None = Field(default=None, ge=0, le=20)
    cbc_hemoglobin: float | None = Field(default=None, ge=0, le=30)
    aspirin_clopidogrel_indication: str | None = Field(default=None, max_length=120)

    @field_validator("*", mode="before")
    @classmethod
    def _normalise_sentinels(cls, value: Any) -> Any:
        return _blank_to_none(value)


class Finding(BaseModel):
    """A rule match. Severity is baseline labelling, not patient-adjusted."""

    model_config = ConfigDict(extra="forbid")

    rule_id: str
    medications: list[str] = Field(min_length=2)
    severity: Severity
    action_class: ActionClass
    reason: str
    action: str
    sources: list[str] = Field(min_length=1)


class SafetyAssessment(BaseModel):
    """The complete deterministic result. No LLM contributes to any field."""

    profile_summary: dict[str, str]
    findings: list[Finding]
    patient_modifiers: list[str]
    inr_context: list[str]
    missing_information: list[str]
    severity_counts: dict[str, int]
    boundary: list[str]


class AgentResult(BaseModel):
    """Workflow output shared by the CLI and the web dashboard."""

    assessment: SafetyAssessment
    summary: str
    summary_source: Literal["model", "deterministic"]
    mode: str
