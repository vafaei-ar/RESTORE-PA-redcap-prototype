"""Streamlit registry abstraction screens for synthetic demonstration only."""
from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from app.registry_store import (
    DISPOSITIONS, STROKE_TYPES, create_episode, update_episode
)


def _mrss(value) -> int | None:
    return None if value == "Not recorded" else int(value)


def _mrss_options(value) -> int:
    if pd.isna(value):
        return 0
    try:
        return [ "Not recorded", "0", "1", "2", "3", "4", "5", "6" ].index(str(int(value)))
    except (ValueError, TypeError):
        return 0


def registry_entry_page(data: pd.DataFrame) -> None:
    st.title("Registry Data Entry")
    st.caption("Demonstrate admission abstraction, treatment, discharge, and 90-day follow-up.")
    st.warning(
        "Synthetic demo only. Do not enter real names, medical record numbers, "
        "patient dates, or other identifiable patient information. "
        "Changes remain in this browser session."
    )
    if st.session_state.get("last_registry_entry"):
        st.success(st.session_state["last_registry_entry"])

    new_tab, edit_tab = st.tabs(["Create stroke episode", "Update registry / follow-up"])
    with new_tab:
        _create_view(data)
    with edit_tab:
        _update_view(data)


def _create_view(data: pd.DataFrame) -> None:
    patient_mode = st.radio(
        "Patient record",
        ["New synthetic patient", "Existing synthetic patient"],
        horizontal=True,
        key="entry_patient_mode",
    )
    existing_id = None
    if patient_mode == "Existing synthetic patient":
        patients = (
            data[["PATID", "synthetic_patient_name", "age", "sex"]]
            .drop_duplicates("PATID")
            .sort_values("PATID")
        )
        ids = patients.PATID.tolist()
        existing_id = st.selectbox(
            "Select synthetic patient",
            ids,
            format_func=lambda p: (
                f"{p} | {patients.loc[patients.PATID == p, 'synthetic_patient_name'].iloc[0]}"
            ),
        )
        st.caption(
            "This creates a new stroke episode under the selected synthetic patient; "
            "it does not create a second patient."
        )

    with st.form("new_stroke_episode", clear_on_submit=False):
        st.markdown("#### 1. Patient context")
        if patient_mode == "New synthetic patient":
            c1, c2, c3 = st.columns(3)
            age = c1.number_input("Age (synthetic)", min_value=18, max_value=100, value=67)
            sex = c2.selectbox("Sex", ["Female", "Male", "Unknown"])
            ruca = c3.number_input("RUCA code", min_value=1, max_value=10, value=2)
            race = st.selectbox(
                "Race/ethnicity",
                ["White", "Black/African American", "Asian",
                 "Other/Multiple", "Hispanic/Latino", "Unknown"],
            )
        else:
            age, sex, ruca, race = None, None, None, None
            st.info("Patient demographics come from the selected synthetic patient.")

        st.markdown("#### 2. Stroke encounter")
        a, b, c = st.columns(3)
        stroke = a.selectbox("Stroke type", list(STROKE_TYPES))
        admit = b.date_input("Admission date (synthetic)", value=date(2026, 6, 1))
        discharge = c.date_input("Discharge date (synthetic)", value=date(2026, 6, 4))
        etiology = st.selectbox(
            "Stroke etiology",
            ["Not yet determined", "Large artery atherosclerosis",
             "Cardioembolic", "Small vessel", "Cryptogenic", "Other determined",
             "Hypertensive", "Amyloid angiopathy", "Aneurysmal", "Other"],
        )

        st.markdown("#### 3. Severity and acute treatments")
        a, b, c = st.columns(3)
        nihss = a.number_input("NIHSS on admission", min_value=0, max_value=42, value=7)
        nihss_discharge = b.number_input(
            "NIHSS at discharge", min_value=0, max_value=42, value=4
        )
        mrs_admit = c.number_input("mRS on admission", min_value=0, max_value=5, value=2)
        a, b, c = st.columns(3)
        ivt = a.checkbox("IV thrombolysis (tPA/TNK)")
        evt = b.checkbox("Mechanical thrombectomy (EVT)")
        agent = c.selectbox("Thrombolytic agent", ["None", "TNK", "tPA"])

        st.markdown("#### 4. Discharge and follow-up")
        a, b, c = st.columns(3)
        disposition = a.selectbox("Discharge disposition", list(DISPOSITIONS), index=1)
        mrs_discharge = b.number_input("mRS at discharge", min_value=0, max_value=6, value=1)
        completed = c.checkbox("90-day follow-up completed")
        mrs_90 = st.selectbox(
            "90-day mRS",
            ["Not recorded", "0", "1", "2", "3", "4", "5", "6"],
        )

        submitted = st.form_submit_button("Create synthetic stroke episode", type="primary")

    if submitted:
        entry = {
            "age": age, "sex": sex, "ruca_code": ruca, "race_ethnicity": race,
            "stroke_type": stroke, "stroke_etiology": etiology,
            "admit_date": admit, "discharge_date": discharge,
            "nihss_admit": nihss, "nihss_discharge": nihss_discharge,
            "mrs_admit": mrs_admit, "mrs_discharge": mrs_discharge,
            "iv_thrombolysis": ivt, "thrombolytic_agent": agent,
            "thrombectomy": evt, "registry_discharge_disposition": disposition,
            "followup_completed": completed, "mrs_90d": _mrss(mrs_90),
        }
        try:
            out = create_episode(data, entry=entry, existing_patid=existing_id)
        except ValueError as exc:
            st.error(str(exc))
        else:
            latest = out.iloc[-1]
            st.session_state["demo_registry_df"] = out
            st.session_state["last_registry_entry"] = (
                f"Created {latest.ENCOUNTERID} for {latest.PATID}. "
                "The episode is now visible in Case Browser and Reports."
            )
            st.rerun()


def _update_view(data: pd.DataFrame) -> None:
    st.caption(
        "Select an existing synthetic stroke episode. Registry values can be changed; "
        "PCORI/PCORnet imported fields remain read-only."
    )
    options = data["ENCOUNTERID"].tolist()
    encounterid = st.selectbox(
        "Stroke episode",
        options,
        format_func=lambda e: (
            f"{e} | {data.loc[data.ENCOUNTERID == e, 'PATID'].iloc[0]}"
            f" | {data.loc[data.ENCOUNTERID == e, 'stroke_type'].iloc[0]}"
        ),
        key="registry_edit_episode",
    )
    row = data.loc[data.ENCOUNTERID == encounterid].iloc[0]
    st.caption(
        f"Imported EHR discharge disposition: "
        f"{'No EHR record linked' if pd.isna(row.pcori_discharge_disposition) else row.pcori_discharge_disposition}"
    )
    options_mrs = ["Not recorded", "0", "1", "2", "3", "4", "5", "6"]
    with st.form("registry_update_form"):
        st.markdown("#### Admission and treatment")
        c1, c2 = st.columns(2)
        stroke = c1.selectbox(
            "Stroke type", list(STROKE_TYPES),
            index=list(STROKE_TYPES).index(row.stroke_type)
        )
        nihss = c2.number_input(
            "NIHSS at admission", min_value=0, max_value=42, value=int(row.nihss_admit)
        )
        c1, c2 = st.columns(2)
        ivt = c1.checkbox("IV thrombolysis", value=bool(row.iv_thrombolysis))
        evt = c2.checkbox("Thrombectomy", value=bool(row.thrombectomy))
        agent = st.selectbox(
            "Thrombolytic agent", ["None", "TNK", "tPA"],
            index=["None", "TNK", "tPA"].index(row.thrombolytic_agent)
        )

        st.markdown("#### Discharge and follow-up")
        c1, c2 = st.columns(2)
        disposition = c1.selectbox(
            "Registry discharge disposition", list(DISPOSITIONS),
            index=list(DISPOSITIONS).index(row.registry_discharge_disposition)
        )
        discharge_mrs = c2.number_input(
            "mRS at discharge", min_value=0, max_value=6, value=int(row.mrs_discharge)
        )
        completed = st.checkbox(
            "Follow-up completed", value=bool(row.followup_completed)
        )
        score = st.selectbox(
            "90-day mRS", options_mrs, index=_mrss_options(row.mrs_90d)
        )
        submitted = st.form_submit_button("Save registry updates", type="primary")

    if submitted:
        changes = {
            "stroke_type": stroke, "nihss_admit": nihss,
            "iv_thrombolysis": ivt, "thrombolytic_agent": agent,
            "thrombectomy": evt,
            "registry_discharge_disposition": disposition,
            "mrs_discharge": discharge_mrs,
            "followup_completed": completed,
            "mrs_90d": _mrss(score),
        }
        try:
            out = update_episode(
                data, encounter_id=encounterid, changes=changes
            )
        except ValueError as exc:
            st.error(str(exc))
        else:
            st.session_state["demo_registry_df"] = out
            st.session_state["last_registry_entry"] = (
                f"Saved registry changes for {encounterid}. "
                "Source values remain preserved."
            )
            st.rerun()
