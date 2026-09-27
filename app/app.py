from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from synthetic_data.generate_demo_data import generate_demo_data

DATA_PATH = ROOT / "synthetic_data" / "outputs" / "combined_demo.parquet"
MAPPING_PATH = ROOT / "data_model" / "field_mapping.csv"

st.set_page_config(page_title="RESTORE-PA Prototype", page_icon="🧠", layout="wide")


@st.cache_data
def load_data() -> pd.DataFrame:
    if DATA_PATH.exists():
        return pd.read_parquet(DATA_PATH)

    # Deployment-friendly fallback: generate the exact same seeded synthetic
    # cohort in memory when no local output file is present.
    return generate_demo_data(n=200, seed=20260913)["combined"]


@st.cache_data
def load_mapping() -> pd.DataFrame:
    return pd.read_csv(MAPPING_PATH)


def yes_no(value: bool) -> str:
    return "Yes" if bool(value) else "No"


def dashboard(df: pd.DataFrame) -> None:
    st.title("RESTORE-PA Stroke Registry Prototype")
    st.caption("Synthetic demonstration data only. No real patient data or PHI.")
    st.info(
        "Use this prototype to discuss workflow, field scope, provenance, and reports. "
        "It is not a production clinical system."
    )

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Stroke episodes", f"{len(df):,}")
    c2.metric("Synthetic patients", f"{df.PATID.nunique():,}")
    c3.metric("Ischemic stroke", f"{(df.stroke_type == 'Ischemic stroke').mean():.1%}")
    c4.metric("IV thrombolysis", f"{df.iv_thrombolysis.mean():.1%}")
    c5.metric("Thrombectomy", f"{df.thrombectomy.mean():.1%}")
    c6.metric("90-day follow-up", f"{df.followup_completed.mean():.1%}")

    review = df["review_status"].value_counts().rename_axis("Status").to_frame("Cases")
    left, right = st.columns([1.3, 1])
    with left:
        st.subheader("Case mix")
        case_mix = (
            df["stroke_type"].value_counts().rename_axis("Stroke type").to_frame("Cases")
        )
        st.bar_chart(case_mix)
    with right:
        st.subheader("Registry work queue")
        st.dataframe(review, use_container_width=True)

    left, right = st.columns(2)
    with left:
        st.subheader("Discharge disposition")
        st.dataframe(
            df["registry_discharge_disposition"]
            .value_counts()
            .rename_axis("Disposition")
            .to_frame("Cases"),
            use_container_width=True,
        )
    with right:
        st.subheader("Operational outcomes")
        metrics = pd.DataFrame(
            {
                "Outcome": [
                    "30-day readmission",
                    "30-day ED revisit",
                    "In-hospital mortality",
                    "90-day mortality",
                    "Source disagreement",
                ],
                "Rate": [
                    df.readmission_30d.mean(),
                    df.ed_revisit_30d.mean(),
                    df.death_in_hospital.mean(),
                    df.mortality_90d.mean(),
                    df.disposition_conflict.mean(),
                ],
            }
        )
        metrics["Rate"] = metrics["Rate"].map(lambda x: f"{x:.1%}")
        st.dataframe(metrics, hide_index=True, use_container_width=True)


def case_browser(df: pd.DataFrame) -> None:
    st.title("Case Browser")
    st.caption(
        "PCORI/PCORnet values are shown as imported/read-only. Registry values can be "
        "reviewed or edited in this demonstration session."
    )

    filter_text = st.text_input("Search synthetic name, PATID, ENCOUNTERID, or FIN")
    filtered = df.copy()
    if filter_text:
        q = filter_text.lower().strip()
        mask = (
            filtered["synthetic_patient_name"].str.lower().str.contains(q)
            | filtered["PATID"].str.lower().str.contains(q)
            | filtered["ENCOUNTERID"].str.lower().str.contains(q)
            | filtered["FIN"].str.lower().str.contains(q)
        )
        filtered = filtered[mask]

    st.dataframe(
        filtered[
            [
                "synthetic_patient_name",
                "PATID",
                "FIN",
                "stroke_type",
                "admit_date",
                "nihss_admit",
                "registry_discharge_disposition",
                "review_status",
            ]
        ],
        hide_index=True,
        use_container_width=True,
    )

    if filtered.empty:
        return

    selected = st.selectbox(
        "Open case",
        filtered.index,
        format_func=lambda idx: (
            f"{filtered.loc[idx, 'synthetic_patient_name']} — "
            f"{filtered.loc[idx, 'stroke_type']} — "
            f"{filtered.loc[idx, 'admit_date'].date()}"
        ),
    )
    row = filtered.loc[selected]

    patient_episodes = df[df.PATID == row.PATID].sort_values("admit_date")
    if len(patient_episodes) > 1:
        st.info(
            f"This synthetic patient has {len(patient_episodes)} stroke episodes. "
            "The interface keeps patient identity separate from episode-level data."
        )

    st.subheader("Episode summary")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("NIHSS admission", int(row.nihss_admit))
    c2.metric("mRS discharge", int(row.mrs_discharge))
    c3.metric("IV thrombolysis", yes_no(row.iv_thrombolysis))
    c4.metric("Thrombectomy", yes_no(row.thrombectomy))
    c5.metric("Review status", row.review_status)

    imported, registry = st.columns(2)
    with imported:
        st.markdown("### PCORI/PCORnet imported fields")
        st.info("Read-only in the proposed workflow")
        imported_df = pd.DataFrame(
            {
                "Field": [
                    "PATID",
                    "ENCOUNTERID",
                    "Admission",
                    "Discharge",
                    "Age",
                    "Sex",
                    "Race/ethnicity",
                    "RUCA",
                    "LDL",
                    "Glucose",
                    "Creatinine",
                    "Discharge disposition",
                    "In-hospital death",
                    "30-day readmission",
                    "30-day ED revisit",
                    "90-day mortality",
                ],
                "Value": [
                    row.PATID,
                    row.ENCOUNTERID,
                    row.admit_date,
                    row.discharge_date,
                    row.age,
                    row.sex,
                    row.race_ethnicity,
                    row.ruca_code,
                    row.ldl,
                    row.glucose,
                    row.creatinine,
                    row.pcori_discharge_disposition,
                    yes_no(row.death_in_hospital),
                    yes_no(row.readmission_30d),
                    yes_no(row.ed_revisit_30d),
                    yes_no(row.mortality_90d),
                ],
            }
        )
        st.dataframe(imported_df, hide_index=True, use_container_width=True)

    with registry:
        st.markdown("### Stroke registry / GWTG fields")
        st.success("Editable demonstration fields")
        key_prefix = f"case_{selected}_"
        stroke_type = st.selectbox(
            "Stroke type",
            ["Ischemic stroke", "TIA", "ICH", "SAH"],
            index=["Ischemic stroke", "TIA", "ICH", "SAH"].index(row.stroke_type),
            key=key_prefix + "stroke_type",
        )
        nihss = st.number_input(
            "NIHSS on admission",
            min_value=0,
            max_value=42,
            value=int(row.nihss_admit),
            key=key_prefix + "nihss",
        )
        mrs = st.number_input(
            "mRS at discharge",
            min_value=0,
            max_value=6,
            value=int(row.mrs_discharge),
            key=key_prefix + "mrs",
        )
        ivt = st.checkbox(
            "IV thrombolysis",
            value=bool(row.iv_thrombolysis),
            key=key_prefix + "ivt",
        )
        evt = st.checkbox(
            "Mechanical thrombectomy",
            value=bool(row.thrombectomy),
            key=key_prefix + "evt",
        )
        disposition_options = [
            "Home",
            "Home health",
            "Inpatient rehab",
            "Skilled nursing facility",
            "Hospice",
            "Expired",
        ]
        disposition = st.selectbox(
            "Registry discharge disposition",
            disposition_options,
            index=disposition_options.index(row.registry_discharge_disposition),
            key=key_prefix + "disposition",
        )
        note = st.text_area("Registry reviewer note", key=key_prefix + "note")

        if row.disposition_conflict:
            st.warning(
                "Source disagreement: PCORI/PCORnet and registry discharge disposition "
                "do not match. A reviewer should reconcile the registry value without "
                "overwriting the imported source value."
            )

        if st.button("Save demo edit", type="primary"):
            st.session_state[key_prefix + "saved"] = {
                "stroke_type": stroke_type,
                "nihss_admit": nihss,
                "mrs_discharge": mrs,
                "iv_thrombolysis": ivt,
                "thrombectomy": evt,
                "registry_discharge_disposition": disposition,
                "reviewer_note": note,
            }
            st.success(
                "Saved in this browser session only. No synthetic source file was overwritten."
            )

    st.subheader("Follow-up")
    f1, f2, f3 = st.columns(3)
    f1.metric("Follow-up completed", yes_no(row.followup_completed))
    f2.metric(
        "90-day mRS",
        "Not available" if pd.isna(row.mrs_90d) else int(row.mrs_90d),
    )
    f3.metric("90-day mortality", yes_no(row.mortality_90d))

    if len(patient_episodes) > 1:
        st.subheader("Other episodes for this synthetic patient")
        st.dataframe(
            patient_episodes[
                [
                    "ENCOUNTERID",
                    "FIN",
                    "admit_date",
                    "stroke_type",
                    "nihss_admit",
                    "registry_discharge_disposition",
                ]
            ],
            hide_index=True,
            use_container_width=True,
        )


def reports(df: pd.DataFrame) -> None:
    st.title("Reports")
    st.caption("Example operational reports for collaborator discussion")

    report = st.selectbox(
        "Report",
        [
            "Registry work queue",
            "Source disagreements",
            "Cases needing follow-up",
            "Missing 90-day mRS",
            "Thrombolysis cases",
            "Thrombectomy cases",
            "Rural stroke cases",
            "30-day readmissions",
        ],
    )

    if report == "Registry work queue":
        out = df[df.review_status != "Complete"]
    elif report == "Source disagreements":
        out = df[df.disposition_conflict]
    elif report == "Cases needing follow-up":
        out = df[~df.followup_completed & ~df.mortality_90d]
    elif report == "Missing 90-day mRS":
        out = df[df.mrs_90d.isna() & ~df.mortality_90d]
    elif report == "Thrombolysis cases":
        out = df[df.iv_thrombolysis]
    elif report == "Thrombectomy cases":
        out = df[df.thrombectomy]
    elif report == "Rural stroke cases":
        out = df[df.rural]
    else:
        out = df[df.readmission_30d]

    st.metric("Cases", len(out))
    st.dataframe(
        out[
            [
                "synthetic_patient_name",
                "PATID",
                "FIN",
                "stroke_type",
                "admit_date",
                "nihss_admit",
                "iv_thrombolysis",
                "thrombectomy",
                "pcori_discharge_disposition",
                "registry_discharge_disposition",
                "review_status",
                "followup_completed",
                "mrs_90d",
            ]
        ],
        hide_index=True,
        use_container_width=True,
    )


def workflow() -> None:
    st.title("Proposed Workflow")
    st.markdown(
        """
**1. Identify the stroke episode.** The patient is represented by PATID in the
PCORI/PCORnet layer and by authorized clinical identifiers in the operational registry.
The stroke episode is anchored by ENCOUNTERID plus FIN/admission-discharge dates.

**2. Import selected EHR context.** Selected PCORI/PCORnet-derived values are
synchronized into the REDCap-facing workflow as read-only source values.

**3. Review registry/GWTG fields.** Stroke Program staff review, complete, and update
registry fields for the selected episode.

**4. Reconcile without overwriting provenance.** When a concept exists in both sources,
the interface displays both values. Registry review can resolve the operational value
while the original imported EHR value remains preserved.

**5. Follow cases and report.** Work queues identify missing follow-up, source
disagreements, treatment cohorts, rural cases, and utilization outcomes.
"""
    )
    st.info(
        "This prototype demonstrates workflow and field behavior only. It is not a "
        "production REDCap implementation and contains no real patient data."
    )


def data_dictionary(mapping: pd.DataFrame) -> None:
    st.title("Prototype Data Dictionary")
    st.caption("Focused v0.1 mapping; not the complete PCORnet/GWTG source inventory")
    st.dataframe(mapping, hide_index=True, use_container_width=True)


df = load_data()
mapping = load_mapping()

page = st.sidebar.radio(
    "Navigate",
    ["Dashboard", "Case Browser", "Reports", "Workflow", "Data Dictionary"],
)
st.sidebar.warning("Synthetic demonstration data only")

if page == "Dashboard":
    dashboard(df)
elif page == "Case Browser":
    case_browser(df)
elif page == "Reports":
    reports(df)
elif page == "Workflow":
    workflow()
else:
    data_dictionary(mapping)
