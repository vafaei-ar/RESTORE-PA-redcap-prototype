# RESTORE-PA REDCap Prototype

Synthetic-data prototype for a future REDCap-based stroke registry interface that brings together selected PCORI/PCORnet EHR-derived data and Stroke Program registry/GWTG data.

## Purpose

The prototype is intended for collaborator discussion and workflow design before any production REDCap build or real patient-data integration. It demonstrates how a combined system could:

- display EHR-derived and registry-entered data for the same stroke episode;
- preserve source provenance (PCORI/PCORnet, Stroke Universe, GWTG, manual registry entry);
- create synthetic stroke registry entries (new patient or repeat episode), and update admission, treatment, discharge and follow-up fields;
- allow registry fields to be reviewed or edited while keeping imported EHR fields read-only;
- show source disagreements without overwriting the original imported value;
- support patients with more than one stroke episode;
- identify follow-up and review work queues;
- provide simple operational and quality-improvement reports; and
- support later translation into a REDCap project/data dictionary.

## Important data rule

**This repository is for synthetic demonstration data only. Do not commit real patient data, PHI, MRNs, FINs, or identifiable exports to this repository.**

The generated files under `synthetic_data/outputs/` are reproducible and intentionally ignored by Git.

## v0.1 scope

The first prototype uses a focused subset of fields that demonstrates the architecture rather than attempting to reproduce every PCORnet or GWTG variable. The broader source-variable inventory remains the reference for later field selection and mapping.

The synthetic cohort includes realistic combinations of:

- ischemic stroke, ICH, SAH, and TIA;
- patient-level demographics and rurality;
- multiple episodes for a subset of synthetic patients;
- index admission/discharge dates;
- NIHSS and mRS;
- last-known-well and arrival times;
- IV thrombolysis and mechanical thrombectomy;
- selected laboratory context;
- source-specific discharge disposition values, including a small synthetic disagreement set;
- mortality, ED revisit, and readmission; and
- post-discharge/90-day follow-up.

## Repository structure

```text
RESTORE-PA-redcap-prototype/
├── .github/workflows/      # automated validation
├── app/                    # Streamlit collaborator-facing prototype
├── data_model/             # schema and source/provenance rules
├── synthetic_data/         # reproducible synthetic-data generation
│   └── outputs/            # generated locally; gitignored
├── tests/                  # synthetic-data validation
├── scripts/                # convenience launch scripts
├── requirements.txt
└── README.md
```

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Optional: pre-generate local files
python synthetic_data/generate_demo_data.py

streamlit run app/app.py
```

If no generated data file is present, the app automatically creates the same seeded 200-episode synthetic cohort in memory. This makes the prototype suitable for a clean clone or simple Streamlit deployment. All identifiers are clearly synthetic and use the `SYN-` prefix.

## What to show collaborators

A short demo can follow this sequence:

1. **Dashboard**: show cohort composition and the registry work queue.
2. **Case Browser**: open a case and compare read-only PCORI/PCORnet values with editable registry/GWTG fields.
3. **Source disagreement example**: open a case marked `Needs source review` and show how both source values are preserved.
4. **Registry Entry**: create a new synthetic stroke episode, optionally linked to an existing synthetic patient. Enter NIHSS/mRS, thrombolysis/EVT, discharge, and follow-up.
5. **Case Browser**: confirm the new episode appears as "Needs EHR linkage" without fabricated imported EHR values.
6. **Registry Entry > Update registry / follow-up**: complete a 90-day mRS and verify that the edited values appear in the case browser.
7. **Reports**: show EHR-linkage queue, follow-up due, source disagreements, treatment cohorts, rural cases, and readmissions.
8. **Workflow / Data Dictionary**: use these pages to discuss how the prototype would translate into REDCap.

## Design principles

- Never overwrite a source PCORI/PCORnet value with a registry-entered value.
- Preserve provenance when the same concept appears in multiple sources.
- Keep patient identity separate from stroke-episode data.
- Allow one patient to have multiple stroke episodes.
- Keep imported PCORI/PCORnet fields read-only in the operational workflow.
- Treat registry/GWTG values as reviewable/editable according to the agreed production scope.
- Keep the repository synthetic-only.

## Registry entry demonstration (v0.4)

The new **Registry Entry** page supports two operations:

- **Create stroke episode**: create a brand-new synthetic patient and stroke episode, or add another episode to an existing synthetic patient. Enter admission/discharge dates, stroke type and etiology, NIHSS/mRS, IV thrombolysis, thrombectomy, discharge disposition, and 90-day follow-up.
- **Update registry / follow-up**: edit existing synthetic registry fields while keeping imported PCORI/PCORnet values unchanged.

The Case Browser's **Registry review** tab also now saves edits to the session dataset. New registry-only episodes are marked **Needs EHR linkage**. The imported EHR information remains unavailable rather than being fabricated.

**Persistence:** Changes are stored in Streamlit session state. They remain visible across pages and application reruns in the same browser session, but are not saved to disk or shared with another session. Use **Reset demo entries** in the sidebar to restore the seeded cohort.

**Not production-ready:** This workflow has no approved user authentication, longitudinal audit history, database persistence, REDCap import/export, or real patient-data integration. Do not enter PHI into any demo controls.

## Deployment-ready behavior

The app does not require committed data files. It can start from the repository alone and generate its synthetic cohort in memory. The default Streamlit configuration uses a light theme for collaborator meetings.

For an institutional or public demo deployment, point the Streamlit entry point to:

```text
app/app.py
```

No secrets, API credentials, or real clinical data are required.

## Validation

Run:

```bash
pytest -q
```

The tests check identifier safety, treatment logic, date ordering, repeat-patient consistency, source-conflict flags, reproducibility, follow-up/mortality rules, registry entry validation, preservation of imported EHR fields, and app rendering.

## Current status

This is an early collaborator-facing prototype, not a production REDCap implementation. The next design step is to use feedback from the Stroke Program and REDCap team to choose the production field subset and produce the formal source-to-REDCap mapping/data dictionary.
