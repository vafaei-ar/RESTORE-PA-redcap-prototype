from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = Path(__file__).resolve().parent
# Streamlit executes app/app.py as a script. Import sibling modules directly,
# instead of treating "app" as a package, to avoid the app.py name collision.
for directory in (ROOT, APP_DIR):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from synthetic_data.generate_demo_data import generate_demo_data
from registry_store import update_episode
from registry_entry import registry_entry_page

DATA_PATH = ROOT / "synthetic_data" / "outputs" / "combined_demo.parquet"
MAPPING_PATH = ROOT / "data_model" / "field_mapping.csv"

st.set_page_config(
    page_title="RESTORE-PA Prototype",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)


def apply_ui_style() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 2.1rem;
            padding-bottom: 2.5rem;
        }
        div[data-testid="stMetric"] {
            border: 1px solid rgba(49, 51, 63, 0.12);
            border-radius: 0.65rem;
            padding: 0.75rem 0.85rem;
            min-height: 6.0rem;
            background: rgba(250, 250, 250, 0.55);
        }
        div[data-testid="stMetricLabel"] p {
            font-size: 0.92rem;
            line-height: 1.15rem;
        }
        div[data-testid="stMetricValue"] {
            font-size: 1.65rem;
        }
        .small-muted {
            color: #667085;
            font-size: 0.90rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data
def load_data() -> pd.DataFrame:
    if DATA_PATH.exists():
        return pd.read_parquet(DATA_PATH)

    return generate_demo_data(n=200, seed=20260913)["combined"]


@st.cache_data
def load_mapping() -> pd.DataFrame:
    return pd.read_csv(MAPPING_PATH)


def yes_no(value) -> str:
    if pd.isna(value):
        return "Not available"
    return "Yes" if bool(value) else "No"


def known_rate(df: pd.DataFrame, column: str) -> float:
    values = pd.to_numeric(df[column], errors="coerce")
    return float(values.mean()) if values.notna().any() else float("nan")


def date_only(value) -> str:
    if pd.isna(value):
        return ""
    return pd.Timestamp(value).strftime("%Y-%m-%d")


def dashboard(df: pd.DataFrame) -> None:
    st.title("RESTORE-PA Stroke Registry Prototype")
    st.caption("Synthetic demonstration data only. No real patient data or PHI.")
    st.info(
        "Use this prototype to discuss workflow, field scope, provenance, and reports. "
        "It is not a production clinical system."
    )

    # Two rows of four metrics are intentionally used instead of a six-across row.
    # This keeps labels and values readable on normal laptop screens and in print/PDF.
    r1 = st.columns(4)
    r1[0].metric("Stroke episodes", f"{len(df):,}")
    r1[1].metric("Synthetic patients", f"{df.PATID.nunique():,}")
    r1[2].metric(
        "Ischemic stroke",
        f"{(df.stroke_type == 'Ischemic stroke').mean():.1%}",
    )
    r1[3].metric("90-day follow-up", f"{df.followup_completed.mean():.1%}")

    r2 = st.columns(4)
    r2[0].metric("IV thrombolysis", f"{df.iv_thrombolysis.mean():.1%}")
    r2[1].metric("Thrombectomy", f"{df.thrombectomy.mean():.1%}")
    r2[2].metric("Readmission (30 d)", f"{known_rate(df, "readmission_30d"):.1%}")
    r2[3].metric("Source conflicts", f"{df.disposition_conflict.mean():.1%}")

    st.divider()

    left, right = st.columns([1.15, 0.85])
    with left:
        st.subheader("Case mix")
        case_mix = (
            df["stroke_type"]
            .replace({"Ischemic stroke": "Ischemic"})
            .value_counts()
            .rename_axis("Stroke type")
            .to_frame("Cases")
        )
        st.bar_chart(case_mix)

    with right:
        st.subheader("Registry work queue")
        queue_order = [
            "Needs EHR linkage", "Needs source review", "Follow-up due", "Complete"
        ]
        review = (
            df["review_status"]
            .value_counts()
            .reindex(queue_order, fill_value=0)
            .rename_axis("Status")
            .reset_index(name="Cases")
        )
        st.table(review.set_index("Status"))
        st.caption(
            "The queue separates source reconciliation from post-discharge follow-up."
        )

    st.divider()

    left, right = st.columns(2)
    with left:
        st.subheader("Discharge disposition")
        disposition = (
            df["registry_discharge_disposition"]
            .value_counts()
            .rename_axis("Disposition")
            .reset_index(name="Cases")
        )
        st.table(disposition.set_index("Disposition"))

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
                "Rate (%)": [
                    100 * df.readmission_30d.mean(),
                    100 * known_rate(df, "ed_revisit_30d"),
                    100 * known_rate(df, "death_in_hospital"),
                    100 * known_rate(df, "mortality_90d"),
                    100 * df.disposition_conflict.mean(),
                ],
            }
        )
        metrics["Rate"] = metrics["Rate (%)"].map(lambda x: f"{x:.1f}%" if pd.notna(x) else "N/A")
        st.table(metrics[["Outcome", "Rate"]].set_index("Outcome"))


def _case_listing(filtered: pd.DataFrame) -> pd.DataFrame:
    out = filtered[
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
    ].copy()
    out["admit_date"] = pd.to_datetime(out["admit_date"]).dt.strftime("%Y-%m-%d")
    return out.rename(
        columns={
            "synthetic_patient_name": "Patient",
            "PATID": "PATID",
            "FIN": "FIN",
            "stroke_type": "Stroke type",
            "admit_date": "Admission",
            "nihss_admit": "NIHSS",
            "registry_discharge_disposition": "Registry disposition",
            "review_status": "Review status",
        }
    )


def _source_overview(row: pd.Series) -> pd.DataFrame:
    linked = pd.notna(row.pcori_discharge_disposition)
    return pd.DataFrame(
        [
            {
                "Concept": "Patient identifier",
                "PCORI/PCORnet": row.PATID if linked else "Not linked",
                "Registry/GWTG": row.PATID,
                "Status": "Linked" if linked else "Registry only",
            },
            {
                "Concept": "Stroke episode identifier",
                "PCORI/PCORnet": row.ENCOUNTERID if linked else "Not linked",
                "Registry/GWTG": row.FIN,
                "Status": "Linked" if linked else "Registry only",
            },
            {
                "Concept": "Discharge disposition",
                "PCORI/PCORnet": (
                    row.pcori_discharge_disposition if linked else "Not linked"
                ),
                "Registry/GWTG": row.registry_discharge_disposition,
                "Status": (
                    "Not linked" if not linked
                    else "Needs review" if row.disposition_conflict else "Concordant"
                ),
            },
        ]
    )


def _ehr_details(row: pd.Series) -> pd.DataFrame:
    details = pd.DataFrame(
        {
            "Field": [
                "PATID",
                "ENCOUNTERID",
                "Admission date",
                "Discharge date",
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
                date_only(row.admit_date),
                date_only(row.discharge_date),
                int(row.age),
                row.sex,
                row.race_ethnicity,
                int(row.ruca_code),
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
    # Field/Value is a presentation table, not a typed clinical dataset.
    # Keeping all display values as strings avoids mixed int/float/text
    # serialization failures in Streamlit's Arrow transport.
    details["Value"] = details["Value"].astype("string")
    return details



def case_browser(df: pd.DataFrame) -> None:
    st.title("Case Browser")
    st.caption(
        "Review one stroke episode at a time. Imported PCORI/PCORnet values remain "
        "read-only; registry/GWTG values can be reviewed or edited."
    )

    filter_text = st.text_input(
        "Search patient, PATID, ENCOUNTERID, or FIN",
        placeholder="Example: SYN-00012 or SYN-FIN-100019",
    )
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
        _case_listing(filtered),
        hide_index=True,
        width="stretch",
        height=300,
        column_config={
            "Patient": st.column_config.TextColumn("Patient", width="medium"),
            "PATID": st.column_config.TextColumn("PATID", width="small"),
            "FIN": st.column_config.TextColumn("FIN", width="small"),
            "Stroke type": st.column_config.TextColumn("Stroke type", width="medium"),
            "Admission": st.column_config.TextColumn("Admission", width="small"),
            "NIHSS": st.column_config.NumberColumn("NIHSS", width="small"),
            "Registry disposition": st.column_config.TextColumn(
                "Registry disposition", width="medium"
            ),
            "Review status": st.column_config.TextColumn(
                "Review status", width="medium"
            ),
        },
    )

    if filtered.empty:
        st.warning("No cases match the current search.")
        return

    selected = st.selectbox(
        "Open case",
        filtered.index,
        format_func=lambda idx: (
            f"{filtered.loc[idx, 'synthetic_patient_name']} | "
            f"{filtered.loc[idx, 'stroke_type']} | "
            f"{pd.Timestamp(filtered.loc[idx, 'admit_date']).date()}"
        ),
    )
    row = filtered.loc[selected]
    patient_episodes = df[df.PATID == row.PATID].sort_values("admit_date")

    st.subheader("Episode summary")
    summary = st.columns(4)
    summary[0].metric("NIHSS admission", int(row.nihss_admit))
    summary[1].metric("mRS discharge", int(row.mrs_discharge))
    summary[2].metric("IV thrombolysis", yes_no(row.iv_thrombolysis))
    summary[3].metric("Thrombectomy", yes_no(row.thrombectomy))

    status_text = row.review_status
    if status_text == "Complete":
        st.success("Review status: Complete")
    elif status_text == "Needs source review":
        st.warning("Review status: Needs source review")
    else:
        st.info(f"Review status: {status_text}")

    if len(patient_episodes) > 1:
        st.info(
            f"This synthetic patient has {len(patient_episodes)} stroke episodes. "
            "Patient-level identity is kept separate from episode-level data."
        )

    st.subheader("Source review")
    overview_tab, ehr_tab, registry_tab = st.tabs(
        ["Compare sources", "Imported EHR data", "Registry review"]
    )

    with overview_tab:
        st.caption(
            "Values from different sources remain visible rather than being silently overwritten."
        )
        st.dataframe(
            _source_overview(row),
            hide_index=True,
            width="stretch",
            height=175,
            column_config={
                "Concept": st.column_config.TextColumn("Concept", width="medium"),
                "PCORI/PCORnet": st.column_config.TextColumn(
                    "PCORI/PCORnet (read-only)", width="large"
                ),
                "Registry/GWTG": st.column_config.TextColumn(
                    "Registry/GWTG", width="large"
                ),
                "Status": st.column_config.TextColumn("Status", width="medium"),
            },
        )
        if pd.isna(row.pcori_discharge_disposition):
            st.info(
                "This registry-entered episode has no linked PCORI/PCORnet record yet. "
                "Imported EHR fields are unavailable and have not been invented."
            )
        elif row.disposition_conflict:
            st.warning(
                "The discharge-disposition values disagree. The registry reviewer can "
                "resolve the registry value while the imported EHR value remains preserved."
            )

    with ehr_tab:
        if pd.isna(row.pcori_discharge_disposition):
            st.warning(
                "No EHR episode has been linked to this registry-only entry. "
                "Imported PCORI/PCORnet fields and outcomes are unavailable."
            )
        else:
            st.info("Imported values are read-only in the proposed workflow.")
            st.dataframe(
                _ehr_details(row),
                hide_index=True,
                width="stretch",
                height=515,
                column_config={
                    "Field": st.column_config.TextColumn("Field", width="medium"),
                    "Value": st.column_config.TextColumn("Value", width="large"),
                },
            )

    with registry_tab:
        st.success("Editable demonstration fields")
        key_prefix = f"case_{selected}_"
        with st.form(key=key_prefix + "registry_form"):
            form_left, form_right = st.columns(2)
            with form_left:
                stroke_type = st.selectbox(
                    "Stroke type",
                    ["Ischemic stroke", "TIA", "ICH", "SAH"],
                    index=["Ischemic stroke", "TIA", "ICH", "SAH"].index(
                        row.stroke_type
                    ),
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
            with form_right:
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
                agent = st.selectbox(
                    "Thrombolytic agent",
                    ["None", "TNK", "tPA"],
                    index=["None", "TNK", "tPA"].index(row.thrombolytic_agent),
                    key=key_prefix + "agent",
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
                    index=disposition_options.index(
                        row.registry_discharge_disposition
                    ),
                    key=key_prefix + "disposition",
                )

            submitted = st.form_submit_button("Save demo edit", type="primary")

        if submitted:
            changes = {
                "stroke_type": stroke_type,
                "nihss_admit": int(nihss),
                "mrs_discharge": int(mrs),
                "iv_thrombolysis": ivt,
                "thrombolytic_agent": agent,
                "thrombectomy": evt,
                "registry_discharge_disposition": disposition,
            }
            try:
                updated = update_episode(
                    df, encounter_id=str(row.ENCOUNTERID), changes=changes
                )
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.session_state["demo_registry_df"] = updated
                st.session_state["last_registry_entry"] = (
                    f"Saved registry fields for {row.ENCOUNTERID}."
                )
                st.success(
                    "Changes saved in this browser session and reflected in reports. "
                    "Imported EHR values were not changed."
                )
                st.rerun()

    st.subheader("Follow-up")
    follow = st.columns(3)
    follow[0].metric("Follow-up completed", yes_no(row.followup_completed))
    follow[1].metric(
        "90-day mRS",
        "Not available" if pd.isna(row.mrs_90d) else int(row.mrs_90d),
    )
    follow[2].metric("90-day mortality", yes_no(row.mortality_90d))

    if len(patient_episodes) > 1:
        with st.expander("Other episodes for this synthetic patient"):
            other = patient_episodes[
                [
                    "ENCOUNTERID",
                    "FIN",
                    "admit_date",
                    "stroke_type",
                    "nihss_admit",
                    "registry_discharge_disposition",
                ]
            ].copy()
            other["admit_date"] = pd.to_datetime(other["admit_date"]).dt.strftime(
                "%Y-%m-%d"
            )
            other = other.rename(
                columns={
                    "ENCOUNTERID": "ENCOUNTERID",
                    "FIN": "FIN",
                    "admit_date": "Admission",
                    "stroke_type": "Stroke type",
                    "nihss_admit": "NIHSS",
                    "registry_discharge_disposition": "Registry disposition",
                }
            )
            st.dataframe(other, hide_index=True, width="stretch")


REPORT_INFO = {
    "Registry work queue": "Cases that still need EHR linkage, source reconciliation or follow-up.",
    "Needs EHR linkage": "Registry-entered episodes with no linked PCORI/PCORnet record.",
    "Source disagreements": "Cases where PCORI/PCORnet and registry discharge disposition differ.",
    "Cases needing follow-up": "Living patients whose follow-up is not yet completed.",
    "Missing 90-day mRS": "Living patients without an available 90-day mRS.",
    "Thrombolysis cases": "Episodes with IV thrombolysis.",
    "Thrombectomy cases": "Episodes with mechanical thrombectomy.",
    "Rural stroke cases": "Episodes classified as rural using the synthetic RUCA field.",
    "30-day readmissions": "Episodes followed by a synthetic 30-day readmission.",
}


def reports(df: pd.DataFrame) -> None:
    st.title("Reports")
    st.caption("Example operational reports for collaborator discussion")

    report = st.selectbox("Report", list(REPORT_INFO))
    st.info(REPORT_INFO[report])

    if report == "Registry work queue":
        out = df[df.review_status != "Complete"]
    elif report == "Needs EHR linkage":
        out = df[df.review_status == "Needs EHR linkage"]
    elif report == "Source disagreements":
        out = df[df.disposition_conflict]
    elif report == "Cases needing follow-up":
        out = df[
            ~df.followup_completed.fillna(False).astype(bool)
            & ~df.mortality_90d.fillna(False).astype(bool)
        ]
    elif report == "Missing 90-day mRS":
        out = df[
            df.mrs_90d.isna()
            & ~df.mortality_90d.fillna(False).astype(bool)
        ]
    elif report == "Thrombolysis cases":
        out = df[df.iv_thrombolysis]
    elif report == "Thrombectomy cases":
        out = df[df.thrombectomy]
    elif report == "Rural stroke cases":
        out = df[df.rural]
    else:
        out = df[df.readmission_30d.fillna(False).astype(bool)]

    st.metric("Cases in report", len(out))

    display = out[
        [
            "synthetic_patient_name",
            "PATID",
            "FIN",
            "stroke_type",
            "admit_date",
            "nihss_admit",
            "registry_discharge_disposition",
            "review_status",
            "followup_completed",
            "mrs_90d",
        ]
    ].copy()
    display["admit_date"] = pd.to_datetime(display["admit_date"]).dt.strftime("%Y-%m-%d")
    display["followup_completed"] = display["followup_completed"].map(yes_no)
    display = display.rename(
        columns={
            "synthetic_patient_name": "Patient",
            "stroke_type": "Stroke type",
            "admit_date": "Admission",
            "nihss_admit": "NIHSS",
            "registry_discharge_disposition": "Registry disposition",
            "review_status": "Review status",
            "followup_completed": "Follow-up",
            "mrs_90d": "90-day mRS",
        }
    )

    st.dataframe(
        display,
        hide_index=True,
        width="stretch",
        height=430,
        column_config={
            "Patient": st.column_config.TextColumn("Patient", width="medium"),
            "PATID": st.column_config.TextColumn("PATID", width="small"),
            "FIN": st.column_config.TextColumn("FIN", width="small"),
            "Stroke type": st.column_config.TextColumn("Stroke type", width="medium"),
            "Admission": st.column_config.TextColumn("Admission", width="small"),
            "NIHSS": st.column_config.NumberColumn("NIHSS", width="small"),
            "Registry disposition": st.column_config.TextColumn(
                "Registry disposition", width="medium"
            ),
            "Review status": st.column_config.TextColumn(
                "Review status", width="medium"
            ),
            "Follow-up": st.column_config.TextColumn("Follow-up", width="small"),
            "90-day mRS": st.column_config.NumberColumn("90-day mRS", width="small"),
        },
    )

    csv_bytes = display.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download this report (CSV)",
        data=csv_bytes,
        file_name=report.lower().replace(" ", "_").replace("-", "_") + ".csv",
        mime="text/csv",
    )


def workflow() -> None:
    st.title("Proposed Workflow")
    st.caption(
        "A practical sequence for linking EHR context with registry abstraction."
    )
    st.markdown(
        """
**1. Identify the stroke episode.** Link the patient and episode across
PCORI/PCORnet and the operational registry using approved identifiers and
encounter/date context.

**2. Import selected EHR context.** Synchronize only the selected
stroke-relevant PCORI/PCORnet values needed for review and reporting.
Keep these source fields read-only.

**3. Enter or update registry fields.** Stroke Program staff use
**Registry Entry** to create episodes and record stroke type, severity,
treatment, discharge and follow-up.

**4. Reconcile sources.** When the same concept appears in both sources,
display both values. Preserve imported EHR values when the registry value
changes.

**5. Review work queues and reports.** Identify incomplete follow-up,
source disagreements, cases awaiting EHR linkage and operational outcomes.
"""
    )
    st.info(
        "This is a synthetic workflow demonstration, not production REDCap. "
        "No real patient data are included."
    )


def data_dictionary(mapping: pd.DataFrame) -> None:
    st.title("Prototype Data Dictionary")
    st.caption(
        "Focused prototype mapping. This is not the complete PCORnet/GWTG source inventory."
    )

    filter_left, filter_right = st.columns(2)
    domains = ["All"] + sorted(mapping["domain"].dropna().unique().tolist())
    sources = ["All"] + sorted(mapping["source_layer"].dropna().unique().tolist())
    with filter_left:
        domain = st.selectbox("Domain", domains)
    with filter_right:
        source = st.selectbox("Source layer", sources)

    shown = mapping.copy()
    if domain != "All":
        shown = shown[shown["domain"] == domain]
    if source != "All":
        shown = shown[shown["source_layer"] == source]

    display = shown.rename(
        columns={
            "concept": "Concept",
            "demo_field": "Prototype field",
            "source_layer": "Source layer",
            "source_field": "Source field",
            "editable_in_demo": "Editable",
            "domain": "Domain",
        }
    ).copy()
    display["Editable"] = display["Editable"].str.capitalize()

    st.metric("Fields shown", len(display))
    st.dataframe(
        display[
            [
                "Concept",
                "Prototype field",
                "Source layer",
                "Source field",
                "Editable",
                "Domain",
            ]
        ],
        hide_index=True,
        width="stretch",
        height=520,
        column_config={
            "Concept": st.column_config.TextColumn("Concept", width="medium"),
            "Prototype field": st.column_config.TextColumn(
                "Prototype field", width="medium"
            ),
            "Source layer": st.column_config.TextColumn(
                "Source layer", width="medium"
            ),
            "Source field": st.column_config.TextColumn(
                "Source field", width="large"
            ),
            "Editable": st.column_config.TextColumn("Editable", width="small"),
            "Domain": st.column_config.TextColumn("Domain", width="medium"),
        },
    )


apply_ui_style()
if "demo_registry_df" not in st.session_state:
    st.session_state["demo_registry_df"] = load_data().copy(deep=True)

df = st.session_state["demo_registry_df"]
mapping = load_mapping()

page = st.sidebar.radio(
    "Navigate",
    ["Dashboard", "Case Browser", "Registry Entry", "Reports", "Workflow", "Data Dictionary"],
)
st.sidebar.divider()
st.sidebar.caption("Synthetic demonstration data only")
st.sidebar.caption("No real patient data or PHI")
with st.sidebar.expander("Reset demo entries"):
    reset_ok = st.checkbox("Confirm reset of session changes", key="reset_demo_confirm")
    if st.button("Reset synthetic session", disabled=not reset_ok):
        st.session_state["demo_registry_df"] = load_data().copy(deep=True)
        st.session_state.pop("last_registry_entry", None)
        st.rerun()

if page == "Dashboard":
    dashboard(df)
elif page == "Case Browser":
    case_browser(df)
elif page == "Registry Entry":
    registry_entry_page(df)
elif page == "Reports":
    reports(df)
elif page == "Workflow":
    workflow()
else:
    data_dictionary(mapping)
