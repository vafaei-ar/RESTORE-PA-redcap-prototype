"""Synthetic-only, session-scoped registry entry model.

Never use this module with real patient information. It intentionally has no
database, file-write, network, or external-ID input capability.
"""
from __future__ import annotations

from datetime import date, datetime
import re

import numpy as np
import pandas as pd

STROKE_TYPES = ("Ischemic stroke", "TIA", "ICH", "SAH")
DISPOSITIONS = (
    "Not yet documented", "Home", "Home health", "Inpatient rehab",
    "Skilled nursing facility", "Hospice", "Expired"
)
EDITABLE_FIELDS = frozenset({
    "stroke_type", "stroke_etiology", "nihss_admit", "nihss_discharge",
    "mrs_admit", "mrs_discharge", "iv_thrombolysis", "thrombolytic_agent",
    "thrombectomy", "registry_discharge_disposition",
    "followup_completed", "mrs_90d"
})


def _next_identifier(series: pd.Series, prefix: str, start: int) -> int:
    largest = start - 1
    for value in series.dropna().astype(str):
        match = re.fullmatch(re.escape(prefix) + r"(\d+)", value)
        if match:
            largest = max(largest, int(match.group(1)))
    return largest + 1


def _validate(fields: dict) -> None:
    stroke = fields["stroke_type"]
    if stroke not in STROKE_TYPES:
        raise ValueError("Select a valid stroke type.")
    nihss = int(fields["nihss_admit"])
    if not 0 <= nihss <= 42:
        raise ValueError("Admission NIHSS must be between 0 and 42.")
    for name in ("nihss_discharge",):
        if fields.get(name) is not None and not 0 <= int(fields[name]) <= 42:
            raise ValueError("Discharge NIHSS must be between 0 and 42.")
    for name in ("mrs_admit", "mrs_discharge"):
        value = fields.get(name)
        if value is not None and not 0 <= int(value) <= 6:
            raise ValueError("mRS values must be between 0 and 6.")
    if fields["registry_discharge_disposition"] not in DISPOSITIONS:
        raise ValueError("Select a valid discharge disposition.")

    ivt = bool(fields["iv_thrombolysis"])
    evt = bool(fields["thrombectomy"])
    if stroke != "Ischemic stroke" and (ivt or evt):
        raise ValueError(
            "This simplified demo only records IV thrombolysis and EVT for ischemic stroke."
        )
    agent = fields["thrombolytic_agent"]
    if ivt and agent not in ("TNK", "tPA"):
        raise ValueError("Select TNK or tPA when IV thrombolysis is recorded.")
    if not ivt and agent != "None":
        raise ValueError("The thrombolytic agent must be None when IVT is not recorded.")

    disposition = fields["registry_discharge_disposition"]
    mrs_discharge = fields.get("mrs_discharge")
    if mrs_discharge == 6 and disposition != "Expired":
        raise ValueError("Discharge mRS 6 requires an expired discharge disposition.")
    if disposition == "Expired" and mrs_discharge != 6:
        raise ValueError("Expired discharge disposition requires discharge mRS 6.")

    followup_done = bool(fields["followup_completed"])
    mrs_90d = fields.get("mrs_90d")
    if followup_done and mrs_90d is None:
        raise ValueError("Enter a 90-day mRS if follow-up is marked complete.")
    if mrs_90d is not None and not 0 <= int(mrs_90d) <= 6:
        raise ValueError("90-day mRS must be between 0 and 6.")
    if not followup_done and mrs_90d is not None and int(mrs_90d) != 6:
        raise ValueError(
            "Without completed follow-up, 90-day mRS must be blank "
            "(except score 6 for a separately recorded death)."
        )
    if disposition == "Expired" and followup_done:
        raise ValueError("An in-hospital death cannot have completed 90-day follow-up.")


def _status(ehr_disposition, registry_disposition, followup_completed: bool,
            registry_death: bool = False) -> tuple[str, bool]:
    if pd.isna(ehr_disposition):
        return "Needs EHR linkage", False
    conflict = (
        registry_disposition != "Not yet documented"
        and ehr_disposition != registry_disposition
    )
    if conflict:
        return "Needs source review", True
    if not followup_completed and not registry_death:
        return "Follow-up due", False
    return "Complete", False


def create_episode(
    data: pd.DataFrame, *, entry: dict, existing_patid: str | None = None
) -> pd.DataFrame:
    """Return a new combined DataFrame containing a synthetic registry-only episode.

    existing_patid may reference only a synthetic PATID already present in data.
    No real patient identifiers or names can be entered.
    """
    _validate(entry)
    if existing_patid is not None:
        matching = data[data["PATID"] == existing_patid]
        if matching.empty or not str(existing_patid).startswith("SYN-"):
            raise ValueError("Select an existing synthetic patient.")
        profile = matching.iloc[0]
        patient_fields = {
            k: profile[k] for k in
            ("PATID", "synthetic_patient_name", "age", "sex",
             "race_ethnicity", "ruca_code", "rural")
        }
    else:
        n = _next_identifier(data["PATID"], "SYN-", 1)
        age = int(entry["age"])
        ruca = int(entry["ruca_code"])
        if not 18 <= age <= 100 or not 1 <= ruca <= 10:
            raise ValueError("Age or RUCA is outside the demo's allowed range.")
        patient_fields = {
            "PATID": f"SYN-{n:05d}",
            "synthetic_patient_name": f"Synthetic Patient {n:03d}",
            "age": age,
            "sex": entry["sex"],
            "race_ethnicity": entry["race_ethnicity"],
            "ruca_code": ruca,
            "rural": ruca >= 4,
        }
        if entry["sex"] not in ("Female", "Male", "Unknown"):
            raise ValueError("Invalid synthetic sex selection.")

    admit = pd.Timestamp(entry["admit_date"])
    discharge = pd.Timestamp(entry["discharge_date"])
    if discharge < admit:
        raise ValueError("Discharge date cannot precede admission date.")

    encounter_no = _next_identifier(data["ENCOUNTERID"], "SYN-ENC-", 1)
    fin_no = _next_identifier(data["FIN"], "SYN-FIN-", 100001)
    episode_no = int(data["episode_number"].max()) + 1

    row = {column: np.nan for column in data.columns}
    row.update(patient_fields)
    row.update({
        "ENCOUNTERID": f"SYN-ENC-{encounter_no:05d}",
        "FIN": f"SYN-FIN-{fin_no}",
        "episode_number": episode_no,
        "admit_date": admit,
        "discharge_date": discharge,
        "arrival_datetime": pd.NaT,
        "last_known_well": pd.NaT,
        "nihss_admit": int(entry["nihss_admit"]),
        "nihss_discharge": entry.get("nihss_discharge"),
        "mrs_admit": entry.get("mrs_admit"),
        "mrs_discharge": entry.get("mrs_discharge"),
        "stroke_type": entry["stroke_type"],
        "stroke_etiology": entry["stroke_etiology"],
        "iv_thrombolysis": bool(entry["iv_thrombolysis"]),
        "thrombolytic_agent": entry["thrombolytic_agent"],
        "thrombectomy": bool(entry["thrombectomy"]),
        "hemorrhagic_conversion": False,
        "door_to_needle_min": np.nan,
        "door_to_puncture_min": np.nan,
        "pcori_discharge_disposition": np.nan,
        "registry_discharge_disposition": entry["registry_discharge_disposition"],
        "followup_completed": bool(entry["followup_completed"]),
        "mrs_90d": (
            float(entry["mrs_90d"])
            if entry.get("mrs_90d") is not None
            else np.nan
        ),
        "disposition_conflict": False,
        "review_status": "Needs EHR linkage",
    })
    # Intentionally leave EHR-only labs, utilization, and mortality as missing.
    # Missing is not equivalent to "No".
    result = pd.concat([data, pd.DataFrame([row])], ignore_index=True)
    if result["ENCOUNTERID"].duplicated().any() or result["FIN"].duplicated().any():
        raise ValueError("Encounter/FIN collision in synthetic dataset.")
    return result


def update_episode(
    data: pd.DataFrame, *, encounter_id: str, changes: dict
) -> pd.DataFrame:
    """Apply only authorized registry edits. Preserve all EHR/source fields."""
    if not changes:
        return data.copy(deep=True)
    unknown = set(changes) - EDITABLE_FIELDS
    if unknown:
        raise ValueError("Cannot edit imported or derived fields: " + ", ".join(sorted(unknown)))
    hits = data.index[data["ENCOUNTERID"] == encounter_id]
    if len(hits) != 1:
        raise ValueError("Select one valid synthetic episode.")
    idx = hits[0]
    current = data.loc[idx]
    candidate = {name: current[name] for name in EDITABLE_FIELDS}
    candidate.update(changes)
    # Convert missing optional values to ordinary None for validation.
    for name in ("nihss_discharge", "mrs_admit", "mrs_discharge", "mrs_90d"):
        if pd.isna(candidate.get(name)):
            candidate[name] = None
    _validate(candidate)

    out = data.copy(deep=True)
    for field in changes:
        out.at[idx, field] = (
            np.nan if changes[field] is None else changes[field]
        )
    status, conflict = _status(
        out.at[idx, "pcori_discharge_disposition"],
        out.at[idx, "registry_discharge_disposition"],
        bool(out.at[idx, "followup_completed"]),
        registry_death=(out.at[idx, "registry_discharge_disposition"] == "Expired"),
    )
    out.at[idx, "review_status"] = status
    out.at[idx, "disposition_conflict"] = conflict
    return out
