from __future__ import annotations

from pathlib import Path
import argparse

import numpy as np
import pandas as pd


OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"


def _clip_int(x: float, low: int, high: int) -> int:
    return int(np.clip(round(x), low, high))


def _severity_profile(stroke_type: str, rng: np.random.Generator) -> tuple[int, int, int]:
    if stroke_type == "TIA":
        nihss = _clip_int(rng.normal(1.5, 1.2), 0, 6)
    elif stroke_type == "Ischemic stroke":
        nihss = _clip_int(rng.gamma(2.2, 3.0), 0, 28)
    elif stroke_type == "ICH":
        nihss = _clip_int(rng.gamma(2.5, 4.0), 1, 35)
    else:  # SAH
        nihss = _clip_int(rng.gamma(2.2, 4.5), 1, 35)

    mrs_admit = int(np.clip(round(nihss / 6 + rng.normal(0, 0.7)), 0, 5))
    nihss_discharge = int(np.clip(round(nihss * rng.uniform(0.35, 0.85) + rng.normal(0, 1.0)), 0, 42))
    return nihss, nihss_discharge, mrs_admit


def generate_demo_data(n: int = 200, seed: int = 20260913) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    rows = []

    start = pd.Timestamp("2025-01-01")
    end = pd.Timestamp("2026-08-31")
    span_days = (end - start).days

    stroke_types = ["Ischemic stroke", "TIA", "ICH", "SAH"]
    stroke_probs = [0.66, 0.14, 0.15, 0.05]
    races = ["White", "Black/African American", "Asian", "Other/Multiple"]
    race_probs = [0.71, 0.16, 0.05, 0.08]

    for i in range(1, n + 1):
        patid = f"SYN-{i:05d}"
        encounterid = f"SYN-ENC-{i:05d}"
        fin = f"SYN-FIN-{100000+i}"
        stroke_type = rng.choice(stroke_types, p=stroke_probs)

        age = _clip_int(rng.normal(69, 14), 22, 95)
        sex = rng.choice(["Female", "Male"], p=[0.51, 0.49])
        race = rng.choice(races, p=race_probs)
        hispanic = rng.choice(["Yes", "No"], p=[0.06, 0.94])
        race_ethnicity = f"{race}; Hispanic/Latino" if hispanic == "Yes" else race
        ruca = int(rng.choice([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], p=[0.38, 0.13, 0.08, 0.08, 0.07, 0.06, 0.06, 0.05, 0.05, 0.04]))
        rural = ruca >= 4

        admit_date = start + pd.Timedelta(days=int(rng.integers(0, span_days + 1)))
        base_los = {"TIA": 1.4, "Ischemic stroke": 4.2, "ICH": 7.1, "SAH": 9.0}[stroke_type]
        los = max(1, _clip_int(rng.gamma(2.0, base_los / 2), 1, 28))
        discharge_date = admit_date + pd.Timedelta(days=los)

        nihss, nihss_discharge, mrs_admit = _severity_profile(stroke_type, rng)
        mortality_risk = 0.015 + 0.006 * nihss + (0.08 if stroke_type == "ICH" else 0) + (0.10 if stroke_type == "SAH" else 0)
        mortality_90d = bool(rng.random() < min(mortality_risk, 0.65))

        arrival = admit_date + pd.Timedelta(hours=float(rng.uniform(0.3, 8.0)))
        onset_to_arrival_h = float(rng.gamma(1.8, 1.7))
        last_known_well = arrival - pd.Timedelta(hours=onset_to_arrival_h)

        eligible_ischemic = stroke_type == "Ischemic stroke"
        iv_prob = 0.34 if eligible_ischemic and onset_to_arrival_h <= 4.5 else 0.04 if eligible_ischemic else 0
        iv_thrombolysis = bool(rng.random() < iv_prob)
        thrombolytic_agent = rng.choice(["TNK", "tPA"], p=[0.75, 0.25]) if iv_thrombolysis else "None"
        door_to_needle = _clip_int(rng.normal(43, 15), 15, 120) if iv_thrombolysis else np.nan

        evt_prob = 0.0
        if eligible_ischemic:
            evt_prob = 0.05 + (0.18 if nihss >= 6 else 0) + (0.14 if nihss >= 12 else 0)
        thrombectomy = bool(rng.random() < min(evt_prob, 0.60))
        door_to_puncture = _clip_int(rng.normal(98, 28), 35, 220) if thrombectomy else np.nan

        hemorrhagic_conversion = bool(
            eligible_ischemic
            and (iv_thrombolysis or thrombectomy)
            and rng.random() < (0.045 + 0.004 * nihss)
        )

        if mortality_90d:
            discharge_disposition = rng.choice(["Expired", "Hospice"], p=[0.72, 0.28])
            mrs_discharge = 6
            mrs_90d = 6
            followup_completed = False
        else:
            mrs_discharge = int(np.clip(round(mrs_admit - rng.uniform(0, 2.2) + rng.normal(0, 0.7)), 0, 5))
            if nihss >= 12:
                discharge_disposition = rng.choice(["Inpatient rehab", "Skilled nursing facility", "Home"], p=[0.48, 0.32, 0.20])
            elif nihss >= 5:
                discharge_disposition = rng.choice(["Home", "Inpatient rehab", "Skilled nursing facility"], p=[0.56, 0.29, 0.15])
            else:
                discharge_disposition = rng.choice(["Home", "Home health", "Inpatient rehab"], p=[0.78, 0.14, 0.08])
            followup_completed = bool(rng.random() < 0.76)
            mrs_90d = int(np.clip(round(mrs_discharge - rng.uniform(0, 1.2) + rng.normal(0, 0.6)), 0, 5)) if followup_completed else np.nan

        readmission_30d = bool((not mortality_90d) and rng.random() < (0.12 + 0.015 * max(mrs_discharge - 2, 0)))
        ed_revisit_30d = bool((not mortality_90d) and rng.random() < (0.11 + 0.02 * max(mrs_discharge - 2, 0)))

        etiologies = {
            "Ischemic stroke": ["Large artery atherosclerosis", "Cardioembolic", "Small vessel", "Cryptogenic", "Other determined"],
            "TIA": ["Probable vascular", "Cryptogenic", "Other determined"],
            "ICH": ["Hypertensive", "Anticoagulant-associated", "Amyloid angiopathy", "Other"],
            "SAH": ["Aneurysmal", "Non-aneurysmal", "Other"],
        }
        stroke_etiology = rng.choice(etiologies[stroke_type])

        rows.append(
            {
                "PATID": patid,
                "ENCOUNTERID": encounterid,
                "FIN": fin,
                "synthetic_patient_name": f"Synthetic Patient {i:03d}",
                "age": age,
                "sex": sex,
                "race_ethnicity": race_ethnicity,
                "ruca_code": ruca,
                "rural": rural,
                "stroke_type": stroke_type,
                "stroke_etiology": stroke_etiology,
                "admit_date": admit_date,
                "discharge_date": discharge_date,
                "last_known_well": last_known_well,
                "arrival_datetime": arrival,
                "nihss_admit": nihss,
                "nihss_discharge": nihss_discharge,
                "mrs_admit": mrs_admit,
                "mrs_discharge": mrs_discharge,
                "iv_thrombolysis": iv_thrombolysis,
                "thrombolytic_agent": thrombolytic_agent,
                "thrombectomy": thrombectomy,
                "door_to_needle_min": door_to_needle,
                "door_to_puncture_min": door_to_puncture,
                "ldl": round(float(np.clip(rng.normal(103, 33), 25, 260)), 1),
                "glucose": round(float(np.clip(rng.normal(132 + 2 * nihss, 45), 55, 420)), 1),
                "creatinine": round(float(np.clip(rng.lognormal(np.log(0.95), 0.35), 0.4, 5.0)), 2),
                "hemorrhagic_conversion": hemorrhagic_conversion,
                "discharge_disposition": discharge_disposition,
                "readmission_30d": readmission_30d,
                "ed_revisit_30d": ed_revisit_30d,
                "mrs_90d": mrs_90d,
                "followup_completed": followup_completed,
                "mortality_90d": mortality_90d,
            }
        )

    combined = pd.DataFrame(rows)

    pcori = combined[
        [
            "PATID", "ENCOUNTERID", "admit_date", "discharge_date", "age", "sex",
            "race_ethnicity", "ruca_code", "ldl", "glucose", "creatinine",
            "readmission_30d", "ed_revisit_30d", "mortality_90d",
        ]
    ].copy()
    pcori["source"] = "PCORI/PCORnet synthetic"

    registry = combined[
        [
            "PATID", "ENCOUNTERID", "FIN", "stroke_type", "stroke_etiology",
            "last_known_well", "arrival_datetime", "nihss_admit", "nihss_discharge",
            "mrs_admit", "mrs_discharge", "iv_thrombolysis", "thrombolytic_agent",
            "thrombectomy", "door_to_needle_min", "door_to_puncture_min",
            "hemorrhagic_conversion", "discharge_disposition",
        ]
    ].copy()
    registry["source"] = "Stroke registry/GWTG synthetic"

    followup = combined[
        ["PATID", "ENCOUNTERID", "followup_completed", "mrs_90d", "mortality_90d"]
    ].copy()
    followup["source"] = "GWTG follow-up synthetic"

    return {"combined": combined, "pcori": pcori, "registry": registry, "followup": followup}


def save_demo_data(data: dict[str, pd.DataFrame], output_dir: Path = OUTPUT_DIR) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    data["combined"].to_parquet(output_dir / "combined_demo.parquet", index=False)
    data["pcori"].to_csv(output_dir / "pcori_synthetic.csv", index=False)
    data["registry"].to_csv(output_dir / "registry_synthetic.csv", index=False)
    data["followup"].to_csv(output_dir / "followup_synthetic.csv", index=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate fully synthetic RESTORE-PA demo data.")
    parser.add_argument("--n", type=int, default=200, help="Number of synthetic stroke episodes")
    parser.add_argument("--seed", type=int, default=20260913, help="Random seed")
    args = parser.parse_args()

    generated = generate_demo_data(n=args.n, seed=args.seed)
    save_demo_data(generated)
    print(f"Generated {len(generated['combined'])} synthetic stroke episodes in {OUTPUT_DIR}")
