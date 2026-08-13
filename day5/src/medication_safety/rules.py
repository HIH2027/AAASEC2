"""The seven verified deterministic interaction rules.

Every rule is a pure data record bound to authorised product labelling. Adding
a rule means adding a source. Severity here is *baseline* severity, taken from
labelling and identical for every patient; patient-specific weighting happens
separately in :mod:`medication_safety.analysis`.

Scope is deliberately small and auditable. An unmatched pair means "no verified
rule fired", never "no interaction exists".

Each rule also carries ``tests`` and ``procedure``: a structured breakout of
the same clinical action already described in ``action``, so the dashboard can
show a "suggested plan" section built entirely from sourced content, with no
model involved.
"""

DAILYMED = "https://dailymed.nlm.nih.gov/dailymed"

PAIR_RULES: tuple[dict, ...] = (
    {
        "rule_id": "PAIR-01",
        "action_class": "AVOID",
        "meds": frozenset({"ketoconazole", "simvastatin"}),
        "severity": "CONTRAINDICATED",
        "reason": (
            "Oral ketoconazole is a strong CYP3A4 inhibitor and can markedly "
            "increase simvastatin exposure, myopathy and rhabdomyolysis risk."
        ),
        "action": (
            "Urgent pharmacist/prescriber reconciliation: confirm ketoconazole "
            "formulation, indication and duration, then use current authorized "
            "labeling and formulary. The patient must not change therapy alone."
        ),
        "tests": ("Creatine kinase (CK)", "Renal function panel"),
        "procedure": (
            "Confirm ketoconazole formulation, indication and duration",
            "Escalate to prescriber before the next simvastatin dose",
        ),
        "sources": (
            f"{DAILYMED}/drugInfo.cfm?setid=57e81e13-b395-4dbd-b660-3038de41a838",
            f"{DAILYMED}/fda/fdaDrugXsl.cfm?setid=a9b18c3c-9a3d-442a-be96-9c36c45b3558&type=display",
        ),
    },
    {
        "rule_id": "PAIR-02",
        "action_class": "CONSULT",
        "meds": frozenset({"amiodarone", "simvastatin"}),
        "severity": "MAJOR",
        "reason": (
            "Amiodarone increases simvastatin exposure and myopathy/"
            "rhabdomyolysis risk; labeling limits simvastatin to 20 mg/day "
            "when coadministered with amiodarone."
        ),
        "action": (
            "Pharmacist/prescriber should review statin choice and dose and "
            "assess muscle symptoms, CK and renal status when indicated."
        ),
        "tests": ("Creatine kinase (CK)", "Renal function panel"),
        "procedure": (
            "Review simvastatin dose against the 20 mg/day labelled limit",
            "Ask about new or worsening muscle pain or weakness",
        ),
        "sources": (
            f"{DAILYMED}/getFile.cfm?setid=d912a75a-ddac-4e7b-b5c4-321d4252ec05&type=pdf",
        ),
    },
    {
        "rule_id": "PAIR-03",
        "action_class": "MONITOR",
        "meds": frozenset({"amiodarone", "warfarin"}),
        "severity": "MAJOR",
        "reason": (
            "Amiodarone potentiates warfarin and may cause serious or fatal "
            "bleeding; the effect may persist and requires INR-based management."
        ),
        "action": (
            "Review INR trend, adherence, diet and interacting medicines. "
            "Do not adjust warfarin from one INR result alone."
        ),
        "tests": ("INR", "CBC/haemoglobin"),
        "procedure": (
            "Review INR trend rather than a single result",
            "Ask about diet, adherence and any new interacting medicine",
        ),
        "sources": (
            f"{DAILYMED}/getFile.cfm?setid=d912a75a-ddac-4e7b-b5c4-321d4252ec05&type=pdf",
            f"{DAILYMED}/drugInfo.cfm?setid=c0cc4511-e656-4b6d-96cd-e02e76173b9d",
        ),
    },
    {
        "rule_id": "PAIR-04",
        "action_class": "MONITOR",
        "meds": frozenset({"amiodarone", "digoxin"}),
        "severity": "MAJOR",
        "reason": (
            "Amiodarone can substantially increase digoxin concentration and "
            "clinical toxicity."
        ),
        "action": (
            "Confirm prior dose adjustment and assess heart rate/ECG, kidney "
            "trend, digoxin level and toxicity symptoms when clinically indicated."
        ),
        "tests": ("Digoxin level", "ECG", "Renal function panel"),
        "procedure": (
            "Confirm whether the digoxin dose was already adjusted",
            "Assess heart rate and ask about toxicity symptoms",
        ),
        "sources": (
            f"{DAILYMED}/getFile.cfm?setid=d912a75a-ddac-4e7b-b5c4-321d4252ec05&type=pdf",
        ),
    },
    {
        "rule_id": "PAIR-05",
        "action_class": "MONITOR",
        "meds": frozenset({"spironolactone", "ibuprofen"}),
        "severity": "MAJOR",
        "reason": (
            "NSAIDs may worsen renal function and reduce spironolactone's "
            "diuretic effect; impaired kidney function increases hyperkalemia risk."
        ),
        "action": (
            "Review NSAID exposure and spironolactone indication/dose; obtain "
            "potassium and repeat renal function promptly when clinically indicated."
        ),
        "tests": ("Potassium", "Renal function panel"),
        "procedure": (
            "Review how often the NSAID is actually being taken",
            "Reassess the spironolactone indication and dose",
        ),
        "sources": (
            f"{DAILYMED}/drugInfo.cfm?setid=10a5c989-66e3-494d-bfd8-b2d6df3be411",
        ),
    },
)

# Cluster rule 1: cumulative pharmacodynamic bleeding risk with warfarin.
BLEEDING_RISK_WITH_WARFARIN = frozenset(
    {"aspirin", "clopidogrel", "ibuprofen", "fluoxetine"}
)

BLEEDING_CLUSTER_RULE = {
    "rule_id": "CLUSTER-01",
    "action_class": "CONSULT",
    "severity": "MAJOR",
    "reason": (
        "Cumulative pharmacodynamic bleeding risk: warfarin labeling "
        "identifies antiplatelets, NSAIDs and serotonin-reuptake inhibitors "
        "as medicines that increase bleeding risk. INR does not measure all "
        "of these platelet/GI effects."
    ),
    "action": (
        "Confirm every antiplatelet/NSAID indication and intended duration; "
        "assess bleeding and CBC/hemoglobin, and reconcile promptly with the "
        "prescriber."
    ),
    "tests": ("CBC/haemoglobin",),
    "procedure": (
        "Confirm the indication and intended duration of every antiplatelet/NSAID",
        "Ask about bleeding or bruising since the combination started",
    ),
    "sources": (
        f"{DAILYMED}/lookup.cfm?setid=51e98fb6-ba76-497e-95d8-fe895ef0b7ed&version=7",
        f"{DAILYMED}/fda/fdaDrugXsl.cfm?setid=c88f33ed-6dfb-4c5e-bc01-d8e36dd97299&type=display",
    ),
}

# Cluster rule 2: additive bradycardia / conduction disturbance.
BRADYCARDIA_TRIPLE = frozenset({"amiodarone", "digoxin", "metoprolol succinate"})

BRADYCARDIA_RULE = {
    "rule_id": "CLUSTER-02",
    "action_class": "MONITOR",
    "severity": "MAJOR",
    "reason": (
        "Potential additive bradycardia/conduction disturbance; confidence "
        "depends on heart rate, ECG, digoxin level and clinical indication."
    ),
    "action": (
        "Verify indications and assess pulse, ECG and symptoms such as "
        "dizziness, syncope or marked fatigue."
    ),
    "tests": ("ECG", "Digoxin level"),
    "procedure": (
        "Verify the indication for each of the three medicines",
        "Ask about dizziness, syncope or marked fatigue",
    ),
    "sources": (
        f"{DAILYMED}/getFile.cfm?setid=d912a75a-ddac-4e7b-b5c4-321d4252ec05&type=pdf",
    ),
}

TOTAL_RULE_COUNT = len(PAIR_RULES) + 2
