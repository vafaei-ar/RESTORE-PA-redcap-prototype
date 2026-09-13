import pandas as pd

from synthetic_data.generate_demo_data import generate_demo_data


def test_generator_size_and_keys():
    data = generate_demo_data(n=50, seed=1)
    combined = data["combined"]
    assert len(combined) == 50
    assert combined["PATID"].is_unique
    assert combined["ENCOUNTERID"].is_unique
    assert combined["FIN"].is_unique


def test_treatment_logic():
    combined = generate_demo_data(n=500, seed=2)["combined"]
    treated = combined[combined["iv_thrombolysis"]]
    evt = combined[combined["thrombectomy"]]
    assert treated["stroke_type"].eq("Ischemic stroke").all()
    assert evt["stroke_type"].eq("Ischemic stroke").all()


def test_followup_and_mortality_logic():
    combined = generate_demo_data(n=300, seed=3)["combined"]
    dead = combined[combined["mortality_90d"]]
    assert dead["mrs_90d"].eq(6).all()
    assert (~dead["followup_completed"]).all()


def test_dates_are_ordered():
    combined = generate_demo_data(n=200, seed=4)["combined"]
    assert (pd.to_datetime(combined["discharge_date"]) >= pd.to_datetime(combined["admit_date"])).all()
    assert (pd.to_datetime(combined["arrival_datetime"]) >= pd.to_datetime(combined["admit_date"])).all()
    assert (pd.to_datetime(combined["last_known_well"]) <= pd.to_datetime(combined["arrival_datetime"])).all()
