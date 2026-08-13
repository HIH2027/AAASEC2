"""Fill the input slots from an uploaded document or image.

The extractor is deliberately a whitelist, not a parser of everything it sees.
It emits only fields it recognises; every other line is counted and discarded.

That is a privacy control, not a shortcut. A real medication list carries a
patient name, a record number, a date of birth. If this module copied the
document through, the identifier guardrail in :mod:`analysis` would reject the
whole upload and the feature would be useless. Dropping unrecognised text at
the boundary means the identifiers never enter the pipeline at all.

The cost is false negatives: a medicine outside the vocabulary is not silently
swallowed but reported in ``unrecognised`` so the pharmacist can add it by
hand. For a safety tool, a visible gap beats an invisible one.
"""

from __future__ import annotations

import csv
import io
import json
import os
import re
from typing import Any

from pydantic import BaseModel, Field

from .rules import BLEEDING_RISK_WITH_WARFARIN, BRADYCARDIA_TRIPLE, PAIR_RULES

TEXT_SUFFIXES = {".txt", ".md", ".csv", ".json"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
DOCUMENT_SUFFIXES = {".pdf", ".docx"}
MAX_UPLOAD_BYTES = 2 * 1024 * 1024
MAX_LINES = 500

# Every medicine named by the rule table, plus common co-prescriptions that a
# real list is likely to contain. Anything outside this set is reported, never
# guessed at.
_SUPPLEMENTARY = {
    "atorvastatin", "rosuvastatin", "pravastatin", "metformin", "insulin",
    "lisinopril", "ramipril", "losartan", "valsartan", "amlodipine",
    "bisoprolol", "atenolol", "carvedilol", "furosemide", "hydrochlorothiazide",
    "apixaban", "rivaroxaban", "dabigatran", "enoxaparin", "omeprazole",
    "pantoprazole", "levothyroxine", "paracetamol", "acetaminophen",
    "naproxen", "diclofenac", "celecoxib", "sertraline", "citalopram",
    "escitalopram", "venlafaxine", "mirtazapine", "gabapentin", "pregabalin",
    "allopurinol", "colchicine", "prednisolone", "salbutamol", "vitamin d",
    "calcium carbonate", "ferrous sulfate", "diltiazem", "verapamil", "sotalol",
    "flecainide", "clarithromycin", "erythromycin", "fluconazole",
    "itraconazole", "ciprofloxacin", "trimethoprim",
}

KNOWN_MEDICATIONS: frozenset[str] = frozenset(
    {med for rule in PAIR_RULES for med in rule["meds"]}
    | set(BLEEDING_RISK_WITH_WARFARIN)
    | set(BRADYCARDIA_TRIPLE)
    | {"warfarin"}
    | _SUPPLEMENTARY
)

# label -> (regex, caster). Each pattern anchors on the label so a bare number
# elsewhere in the document is never adopted as a clinical value.
_NUMBER = r"(-?\d+(?:\.\d+)?)"
PARAM_PATTERNS: dict[str, tuple[str, type]] = {
    "age": (rf"\bage\b\D{{0,12}}{_NUMBER}", int),
    "inr": (rf"\binr\b\D{{0,12}}{_NUMBER}", float),
    "egfr": (rf"\begfr\b\D{{0,12}}{_NUMBER}", float),
    "crcl": (rf"\b(?:crcl|creatinine clearance)\b\D{{0,12}}{_NUMBER}", float),
    "serum_creatinine": (
        rf"\b(?:serum creatinine|scr)\b\D{{0,12}}{_NUMBER}", float
    ),
    "potassium": (rf"\b(?:potassium|k\+)\b\D{{0,12}}{_NUMBER}", float),
    "magnesium": (rf"\b(?:magnesium|mg\+\+)\b\D{{0,12}}{_NUMBER}", float),
    "qtc_ms": (rf"\bqtc\b\D{{0,12}}{_NUMBER}", int),
    "heart_rate": (
        rf"\b(?:heart rate|pulse|hr)\b\D{{0,12}}{_NUMBER}", int
    ),
    "digoxin_level": (rf"\bdigoxin level\b\D{{0,12}}{_NUMBER}", float),
    "cbc_hemoglobin": (
        rf"\b(?:h(?:a)?emoglobin|hb|hgb)\b\D{{0,12}}{_NUMBER}", float
    ),
}

_DOSE = re.compile(
    r"(\d+(?:\.\d+)?\s?(?:mg|mcg|g|ml|units?|iu))", re.IGNORECASE
)
_FREQUENCY = re.compile(
    r"("
    r"once daily|twice daily|three times daily|four times daily|"
    r"every \d+ hours?|at bedtime|as needed|prn|"
    r"o\.?d\.?|b\.?i\.?d\.?|t\.?i\.?d\.?|q\.?d\.?s\.?|nocte"
    r")",
    re.IGNORECASE,
)
_ROUTE = re.compile(
    r"\b(oral|orally|po|iv|intravenous|subcutaneous|sc|topical|inhaled)\b",
    re.IGNORECASE,
)


class ExtractionResult(BaseModel):
    """What the extractor was willing to take from a document."""

    profile: dict[str, Any]
    recognised: list[str] = Field(default_factory=list)
    unrecognised: list[str] = Field(default_factory=list)
    ignored_lines: int = 0
    source: str
    notes: list[str] = Field(default_factory=list)


def _looks_like_medication_line(line: str) -> bool:
    """A line worth reporting as a possible medicine we did not recognise."""
    return bool(_DOSE.search(line)) and len(line) < 160


def _match_medication(line: str) -> dict[str, str] | None:
    lowered = line.lower()
    # Longest name first so "metoprolol succinate" wins over "metoprolol".
    for name in sorted(KNOWN_MEDICATIONS, key=len, reverse=True):
        if re.search(rf"\b{re.escape(name)}\b", lowered):
            medication: dict[str, str] = {"name": name}
            dose = _DOSE.search(line)
            if dose:
                medication["dose"] = " ".join(dose.group(1).split())
            frequency = _FREQUENCY.search(line)
            if frequency:
                medication["frequency"] = frequency.group(1).lower()
            route = _ROUTE.search(line)
            if route:
                medication["route"] = route.group(1).lower()
            return medication
    return None


def _extract_parameters(text: str, profile: dict, recognised: list[str]) -> None:
    lowered = text.lower()
    for field, (pattern, cast) in PARAM_PATTERNS.items():
        match = re.search(pattern, lowered, flags=re.IGNORECASE)
        if not match:
            continue
        try:
            profile[field] = cast(float(match.group(1)))
        except (TypeError, ValueError):
            continue
        recognised.append(f"{field} = {profile[field]}")

    if re.search(r"\bdialysis\b", lowered):
        on_dialysis = not re.search(
            r"\b(no|not on|denies|without)\s+(\w+\s+){0,2}dialysis\b", lowered
        )
        profile["dialysis"] = bool(on_dialysis)
        recognised.append(f"dialysis = {profile['dialysis']}")

    if re.search(r"\bdvt\b", lowered) and re.search(r"warfarin", lowered):
        profile["warfarin_indication"] = "DVT"
        recognised.append("warfarin_indication = DVT")


def extract_from_text(text: str, *, source: str = "text") -> ExtractionResult:
    """Pull recognised medications and parameters out of free text."""
    profile: dict[str, Any] = {}
    recognised: list[str] = []
    unrecognised: list[str] = []
    medications: list[dict[str, str]] = []
    seen: set[str] = set()
    ignored = 0

    lines = [line.strip() for line in text.splitlines()[:MAX_LINES]]
    for line in lines:
        if not line:
            continue
        medication = _match_medication(line)
        if medication:
            if medication["name"] in seen:
                continue
            seen.add(medication["name"])
            medications.append(medication)
            recognised.append(medication["name"])
        elif _looks_like_medication_line(line):
            unrecognised.append(line[:120])
        else:
            ignored += 1

    _extract_parameters(text, profile, recognised)
    profile["medications"] = medications

    notes = []
    if unrecognised:
        notes.append(
            f"{len(unrecognised)} line(s) look like medications but are not in "
            "the recognised vocabulary. Add them by hand before running."
        )
    if ignored:
        notes.append(
            f"{ignored} unrecognised line(s) were discarded and never leave the "
            "server, so any identifier in the document is not carried forward."
        )
    if not medications:
        notes.append("No recognised medication was found in this document.")

    return ExtractionResult(
        profile=profile,
        recognised=recognised,
        unrecognised=unrecognised,
        ignored_lines=ignored,
        source=source,
        notes=notes,
    )


def extract_from_csv(data: str) -> ExtractionResult:
    """Read a name/dose/frequency/route table."""
    medications: list[dict[str, str]] = []
    recognised: list[str] = []
    unrecognised: list[str] = []

    reader = csv.DictReader(io.StringIO(data))
    for row in list(reader)[:MAX_LINES]:
        normalised = {
            (key or "").strip().lower(): (value or "").strip()
            for key, value in row.items()
        }
        name = normalised.get("name") or normalised.get("medication") or ""
        if not name:
            continue
        medication = {"name": name}
        for field in ("dose", "frequency", "route"):
            if normalised.get(field):
                medication[field] = normalised[field]

        if name.lower() in KNOWN_MEDICATIONS:
            recognised.append(name)
        else:
            # A named column is an explicit claim, so keep it, but say so.
            unrecognised.append(name)
        medications.append(medication)

    profile: dict[str, Any] = {"medications": medications}
    notes = []
    if unrecognised:
        notes.append(
            f"{len(unrecognised)} medication(s) are outside the recognised "
            "vocabulary; no verified rule covers them."
        )
    if not medications:
        notes.append("No medication rows were found. Expected a 'name' column.")

    return ExtractionResult(
        profile=profile,
        recognised=recognised,
        unrecognised=unrecognised,
        source="csv",
        notes=notes,
    )


def extract_from_json(data: str) -> ExtractionResult:
    """Accept a profile object, keeping only fields the slots know about."""
    try:
        payload = json.loads(data)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc.msg}") from exc

    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object describing one profile")

    allowed = set(PARAM_PATTERNS) | {
        "dialysis",
        "liver_status",
        "warfarin_indication",
        "dvt_timing",
        "aspirin_clopidogrel_indication",
    }
    profile: dict[str, Any] = {}
    recognised: list[str] = []
    dropped: list[str] = []

    for key, value in payload.items():
        if key == "medications":
            continue
        if key in allowed:
            profile[key] = value
            recognised.append(f"{key} = {value}")
        else:
            # Unknown keys are dropped here rather than rejected later.
            dropped.append(key)

    medications = []
    for item in payload.get("medications", [])[:MAX_LINES]:
        if isinstance(item, dict) and item.get("name"):
            medications.append(
                {
                    field: item[field]
                    for field in ("name", "dose", "frequency", "route")
                    if item.get(field)
                }
            )
            recognised.append(str(item["name"]))
        elif isinstance(item, str):
            medications.append({"name": item})
            recognised.append(item)
    profile["medications"] = medications

    notes = []
    if dropped:
        notes.append(
            f"{len(dropped)} unsupported field(s) were dropped: "
            + ", ".join(sorted(dropped)[:8])
        )
    return ExtractionResult(
        profile=profile, recognised=recognised, source="json", notes=notes
    )


def extract_from_pdf(data: bytes) -> ExtractionResult:
    """Read the text layer of a PDF, then apply the usual whitelist."""
    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            # An empty password unlocks many "protected" clinical exports.
            try:
                reader.decrypt("")
            except Exception as exc:  # noqa: BLE001 - pypdf raises several types
                raise ValueError("This PDF is password protected") from exc
        pages = [page.extract_text() or "" for page in reader.pages[:50]]
    except ValueError:
        raise
    except Exception as exc:  # noqa: BLE001 - a malformed PDF fails many ways
        raise ValueError(f"Could not read this PDF: {type(exc).__name__}") from exc

    text = "\n".join(pages)
    if not text.strip():
        raise ValueError(
            "This PDF has no text layer, so it is probably a scan. Upload it as "
            "an image instead, or export a text version."
        )

    result = extract_from_text(text, source="pdf")
    result.notes.insert(0, f"Read the text layer of {len(pages)} page(s).")
    return result


def extract_from_docx(data: bytes) -> ExtractionResult:
    """Read a Word document, including table cells."""
    import docx

    try:
        document = docx.Document(io.BytesIO(data))
    except Exception as exc:  # noqa: BLE001 - python-docx raises several types
        raise ValueError(
            f"Could not read this Word document: {type(exc).__name__}. "
            "Only .docx is supported, not the older .doc format."
        ) from exc

    lines = [paragraph.text for paragraph in document.paragraphs]

    # Medication lists are very often tables, and paragraph text alone misses
    # every cell, so walk the tables too.
    tables = 0
    for table in document.tables:
        tables += 1
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            # Join the row so "Warfarin | 5 mg | once daily" reads as one line.
            joined = " ".join(part for part in cells if part)
            if joined:
                lines.append(joined)

    text = "\n".join(lines)
    if not text.strip():
        raise ValueError("This Word document contains no readable text")

    result = extract_from_text(text, source="word")
    if tables:
        result.notes.insert(0, f"Read {tables} table(s) as well as the body text.")
    return result


def extract_from_image(data: bytes, media_type: str) -> ExtractionResult:
    """Read a photographed or scanned list through a vision model.

    The model's reply is parsed by :func:`extract_from_json`, so it is held to
    the same whitelist as every other source: it can populate known slots and
    nothing else.
    """
    model_name = os.getenv("OPENROUTER_VISION_MODEL")
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not model_name:
        raise ValueError(
            "Image upload needs a vision model. Set OPENROUTER_VISION_MODEL in "
            ".env, or upload the list as .txt, .csv, .md or .json."
        )
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is required to read an image")

    import base64

    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_openai import ChatOpenAI

    encoded = base64.b64encode(data).decode("ascii")
    model = ChatOpenAI(
        model=model_name,
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        temperature=0,
        max_tokens=900,
        timeout=90,
        max_retries=1,
    )
    response = model.invoke(
        [
            SystemMessage(
                content=(
                    "Transcribe the medication list in the image into JSON with "
                    "keys 'medications' (array of {name, dose, frequency, route}) "
                    "and any of age, inr, egfr, crcl, serum_creatinine, "
                    "potassium, magnesium, qtc_ms, heart_rate, digoxin_level, "
                    "cbc_hemoglobin, dialysis, liver_status. "
                    "Copy no patient name, record number or date of birth. "
                    "Omit anything you cannot read. Reply with JSON only."
                )
            ),
            HumanMessage(
                content=[
                    {"type": "text", "text": "Transcribe this medication list."},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{media_type};base64,{encoded}"},
                    },
                ]
            ),
        ]
    )

    raw = str(response.content).strip()
    match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    if not match:
        raise ValueError("The vision model did not return readable JSON")

    result = extract_from_json(match.group(0))
    result.source = "image"
    result.notes.insert(
        0,
        "Transcribed from an image by a language model. Check every row against "
        "the original before running the review.",
    )
    return result


def extract_upload(filename: str, media_type: str, data: bytes) -> ExtractionResult:
    """Dispatch an uploaded file to the right extractor."""
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError("File is larger than the 2 MB limit")
    if not data:
        raise ValueError("The uploaded file is empty")

    suffix = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""

    if suffix in IMAGE_SUFFIXES or media_type.startswith("image/"):
        return extract_from_image(data, media_type or "image/png")

    if suffix == ".pdf" or media_type == "application/pdf":
        return extract_from_pdf(data)

    if suffix == ".docx" or media_type.endswith("wordprocessingml.document"):
        return extract_from_docx(data)

    if suffix == ".doc":
        raise ValueError(
            "The legacy .doc format is not supported. Save it as .docx or PDF."
        )

    if suffix not in TEXT_SUFFIXES:
        raise ValueError(
            "Unsupported file type. Upload a PDF, Word .docx, .txt, .md, .csv, "
            ".json or an image."
        )

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("File is not valid UTF-8 text") from exc

    if suffix == ".json":
        return extract_from_json(text)
    if suffix == ".csv":
        return extract_from_csv(text)
    return extract_from_text(text, source="markdown" if suffix == ".md" else "text")
