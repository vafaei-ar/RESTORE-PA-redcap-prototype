"""Registry entry and provenance regression tests (synthetic records only)."""
import pandas as pd
import pytest

from app.registry_store import create_episode, update_episode
from synthetic_data.generate_demo_data import generate_demo_data


@pytest.fixture
def cohort():
    return generate_demo_data(n=60, seed=11)["combined"]


@pytest.fixture
def entry():
    return {
        "age": 66, "sex": "Female", "ruca_code": 4,
        "race_ethnicity": "Other/Multiple",
        "stroke_type": "Ischemic stroke",
        "stroke_etiology": "Cardioembolic",
        "admit_date": "2026-06-01",
        "discharge_date": "2026-06-04",
        "nihss_admit": 9, "nihss_discharge": 4, "mrs_admit": 2,
        "mrs_discharge": 1, "iv_thrombolysis": True,
        "thrombolytic_agent": "TNK", "thrombectomy": False,
        "registry_discharge_disposition": "Home",
        "followup_completed": False, "mrs_90d": None,
    }


def test_create_new_patient_and_episode(cohort, entry):
    out = create_episode(cohort, entry=entry)
    new = out.iloc[-1]
    assert len(out) == len(cohort) + 1
    assert new.PATID.startswith("SYN-")
    assert new.PATID not in cohort.PATID.values
    assert new.ENCOUNTERID not in cohort.ENCOUNTERID.values
    assert new.FIN not in cohort.FIN.values
    assert out.ENCOUNTERID.is_unique
    assert out.FIN.is_unique
    assert new.stroke_type == "Ischemic stroke"
    assert new.thrombolytic_agent == "TNK"
    assert new.review_status == "Needs EHR linkage"
    assert pd.isna(new.pcori_discharge_disposition)
    assert pd.isna(new.mortality_90d)
    assert pd.isna(new.ldl)


def test_add_episode_for_existing_synthetic_patient(cohort, entry):
    patid = cohort.iloc[0].PATID
    out = create_episode(cohort, entry=entry, existing_patid=patid)
    assert out.iloc[-1].PATID == patid
    assert out.PATID.nunique() == cohort.PATID.nunique()
    assert out.loc[out.PATID == patid, "age"].nunique() == 1
    assert out.loc[out.PATID == patid, "sex"].nunique() == 1


def test_new_record_updates_registry_only(cohort, entry):
    out = create_episode(cohort, entry=entry)
    enc = out.iloc[-1].ENCOUNTERID
    updated = update_episode(
        out, encounter_id=enc,
        changes={"followup_completed": True, "mrs_90d": 1,
                 "registry_discharge_disposition": "Inpatient rehab"}
    )
    new = updated.iloc[-1]
    assert bool(new.followup_completed)
    assert int(new.mrs_90d) == 1
    assert new.review_status == "Needs EHR linkage"
    assert pd.isna(new.pcori_discharge_disposition)
    assert pd.isna(new.mortality_90d)


def test_existing_record_source_values_unchanged(cohort):
    sub = cohort[
        (cohort["registry_discharge_disposition"] == "Home")
        & (cohort["pcori_discharge_disposition"] == "Home")
    ]
    assert len(sub) > 0
    original = sub.iloc[0]
    updated = update_episode(
        cohort, encounter_id=original.ENCOUNTERID,
        changes={"registry_discharge_disposition": "Home health"}
    )
    changed = updated.loc[updated.ENCOUNTERID == original.ENCOUNTERID].iloc[0]
    assert changed.pcori_discharge_disposition == "Home"
    assert changed.registry_discharge_disposition == "Home health"
    assert bool(changed.disposition_conflict)
    assert changed.review_status == "Needs source review"
    pd.testing.assert_series_equal(
        cohort.loc[cohort.ENCOUNTERID == original.ENCOUNTERID,
                   ["pcori_discharge_disposition", "ldl", "creatinine"]].iloc[0],
        updated.loc[updated.ENCOUNTERID == original.ENCOUNTERID,
                    ["pcori_discharge_disposition", "ldl", "creatinine"]].iloc[0],
    )


def test_no_silent_mutation_of_input(cohort, entry):
    before = cohort.copy(deep=True)
    out = create_episode(cohort, entry=entry)
    update_episode(out, encounter_id=out.iloc[-1].ENCOUNTERID,
                   changes={"nihss_admit": 8})
    pd.testing.assert_frame_equal(cohort, before)


@pytest.mark.parametrize("changes", [
    {"pcori_discharge_disposition": "Home"},
    {"PATID": "REAL-PATIENT"},
    {"mortality_90d": True},
    {"ldl": 120.0},
])
def test_cannot_edit_imported_ehr_fields(cohort, changes):
    with pytest.raises(ValueError, match="Cannot edit"):
        update_episode(cohort, encounter_id=cohort.iloc[0].ENCOUNTERID, changes=changes)


def test_invalid_date_rejected(cohort, entry):
    entry["discharge_date"] = "2026-05-30"
    with pytest.raises(ValueError, match="Discharge date"):
        create_episode(cohort, entry=entry)


def test_invalid_treatment_for_ich_rejected(cohort, entry):
    entry["stroke_type"] = "ICH"
    with pytest.raises(ValueError, match="ischemic stroke"):
        create_episode(cohort, entry=entry)


def test_invalid_mrs_or_agent_rejected(cohort, entry):
    entry["mrs_discharge"] = 6
    with pytest.raises(ValueError, match="expired discharge"):
        create_episode(cohort, entry=entry)

    entry["mrs_discharge"] = 1
    entry["thrombolytic_agent"] = "None"
    with pytest.raises(ValueError, match="TNK or tPA"):
        create_episode(cohort, entry=entry)


def test_followup_score_required_when_completed(cohort, entry):
    entry["followup_completed"] = True
    with pytest.raises(ValueError, match="90-day mRS"):
        create_episode(cohort, entry=entry)


def test_non_synthetic_patient_not_accepted(cohort, entry):
    with pytest.raises(ValueError, match="synthetic patient"):
        create_episode(cohort, entry=entry, existing_patid="123456789")


def test_repeated_additions_use_unique_ids(cohort, entry):
    one = create_episode(cohort, entry=entry)
    two = create_episode(one, entry=entry)
    assert two.ENCOUNTERID.is_unique
    assert two.FIN.is_unique
    assert two.PATID.nunique() == cohort.PATID.nunique() + 2
