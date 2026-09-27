import pandas as pd

from synthetic_data.generate_demo_data import generate_demo_data


def test_generator_size_and_keys():
    data = generate_demo_data(n=50, seed=1)
    combined = data["combined"]
    assert len(combined) == 50
    assert combined["ENCOUNTERID"].is_unique
    assert combined["FIN"].is_unique
    assert combined["PATID"].nunique() < len(combined)
    assert combined["PATID"].nunique() == 45


def test_patient_level_fields_are_stable_across_episodes():
    combined = generate_demo_data(n=200, seed=11)["combined"]
    patient_fields = ["synthetic_patient_name", "age", "sex", "race_ethnicity", "ruca_code"]
    for field in patient_fields:
        assert combined.groupby("PATID")[field].nunique(dropna=False).max() == 1


def test_treatment_logic():
    combined = generate_demo_data(n=500, seed=2)["combined"]
    treated = combined[combined["iv_thrombolysis"]]
    evt = combined[combined["thrombectomy"]]
    assert treated["stroke_type"].eq("Ischemic stroke").all()
    assert evt["stroke_type"].eq("Ischemic stroke").all()
    assert treated["thrombolytic_agent"].isin(["TNK", "tPA"]).all()
    assert combined.loc[~combined["iv_thrombolysis"], "thrombolytic_agent"].eq("None").all()


def test_followup_and_mortality_logic():
    combined = generate_demo_data(n=300, seed=3)["combined"]
    dead = combined[combined["mortality_90d"]]
    assert dead["mrs_90d"].eq(6).all()
    assert (~dead["followup_completed"]).all()


def test_dates_are_ordered():
    combined = generate_demo_data(n=200, seed=4)["combined"]
    assert (
        pd.to_datetime(combined["discharge_date"])
        >= pd.to_datetime(combined["admit_date"])
    ).all()
    assert (
        pd.to_datetime(combined["arrival_datetime"])
        >= pd.to_datetime(combined["admit_date"])
    ).all()
    assert (
        pd.to_datetime(combined["last_known_well"])
        <= pd.to_datetime(combined["arrival_datetime"])
    ).all()


def test_source_conflict_flag_and_review_queue():
    combined = generate_demo_data(n=1000, seed=5)["combined"]
    differs = (
        combined["pcori_discharge_disposition"]
        != combined["registry_discharge_disposition"]
    )
    assert combined["disposition_conflict"].eq(differs).all()
    assert combined.loc[differs, "review_status"].eq("Needs source review").all()
    assert differs.any()


def test_synthetic_identifiers_are_obvious():
    combined = generate_demo_data(n=100, seed=6)["combined"]
    assert combined["PATID"].str.startswith("SYN-").all()
    assert combined["ENCOUNTERID"].str.startswith("SYN-ENC-").all()
    assert combined["FIN"].str.startswith("SYN-FIN-").all()
    assert combined["synthetic_patient_name"].str.startswith("Synthetic Patient ").all()


def test_reproducible_seed():
    a = generate_demo_data(n=100, seed=7)["combined"]
    b = generate_demo_data(n=100, seed=7)["combined"]
    pd.testing.assert_frame_equal(a, b)


def test_invalid_generator_arguments():
    for kwargs in [
        {"n": 0},
        {"n": 10, "patient_fraction": 0},
        {"n": 10, "patient_fraction": 1.1},
    ]:
        try:
            generate_demo_data(**kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Expected ValueError for {kwargs}")
