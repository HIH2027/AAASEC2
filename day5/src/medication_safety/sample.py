"""The de-identified demonstration profile.

Kept out of server.py so the web app can prefill its slots without
importing fastmcp, which a hosted deployment does not install.
"""

# De-identified sample profile. No name, no record number, no date of birth.
SAMPLE_PROFILE = {
    "age": 78,
    "warfarin_indication": "DVT",
    "dvt_timing": "7 years ago",
    "inr": 1.6,
    "egfr": 42,
    "crcl": 38,
    "serum_creatinine": 1.6,
    "dialysis": False,
    "liver_status": "Not provided",
    "aspirin_clopidogrel_indication": "Not provided",
    "potassium": "Not provided",
    "magnesium": "Not provided",
    "qtc_ms": "Not provided",
    "heart_rate": "Not provided",
    "digoxin_level": "Not provided",
    "cbc_hemoglobin": "Not provided",
    "medications": [
        {"name": "Warfarin", "dose": "5 mg", "frequency": "once daily"},
        {"name": "Amiodarone", "dose": "200 mg", "frequency": "once daily"},
        {"name": "Aspirin", "dose": "81 mg", "frequency": "once daily"},
        {
            "name": "Ketoconazole",
            "dose": "200 mg",
            "frequency": "once daily",
            "route": "oral",
        },
        {"name": "Digoxin", "dose": "0.125 mg", "frequency": "once daily"},
        {"name": "Simvastatin", "dose": "40 mg", "frequency": "at bedtime"},
        {
            "name": "Metoprolol succinate",
            "dose": "50 mg",
            "frequency": "once daily",
        },
        {"name": "Fluoxetine", "dose": "20 mg", "frequency": "once daily"},
        {"name": "Clopidogrel", "dose": "75 mg", "frequency": "once daily"},
        {"name": "Spironolactone", "dose": "25 mg", "frequency": "once daily"},
        {
            "name": "Ibuprofen",
            "dose": "400 mg",
            "frequency": "three times daily as needed",
        },
    ],
}
