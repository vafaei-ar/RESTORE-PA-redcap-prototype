# RESTORE-PA REDCap Prototype

Synthetic-data prototype for a future REDCap-based stroke registry interface that brings together selected PCORI/PCORnet EHR-derived data and Stroke Program registry/GWTG data.

## Purpose

The prototype is intended for collaborator discussion and workflow design before any production REDCap build or real patient-data integration. It demonstrates how a combined system could:

- display EHR-derived and registry-entered data for the same stroke episode;
- preserve source provenance (PCORI/PCORnet, Stroke Universe, GWTG, manual registry entry);
- allow registry fields to be reviewed or edited while keeping imported EHR fields read-only;
- identify missing registry fields;
- provide simple operational and quality-improvement reports; and
- support later translation into a REDCap project/data dictionary.

## Important data rule

**This repository is for synthetic demonstration data only. Do not commit real patient data, PHI, MRNs, FINs, or identifiable exports to this repository.**

## v0.1 scope

The first prototype uses a focused subset of fields that demonstrates the architecture rather than attempting to reproduce every PCORnet or GWTG variable. The broader source-variable inventory remains the reference for later field selection and mapping.

The synthetic cohort includes realistic combinations of:

- ischemic stroke, ICH, SAH, and TIA;
- demographics and geography;
- index admission/discharge dates;
- NIHSS and mRS;
- last-known-well and arrival times;
- IV thrombolysis and mechanical thrombectomy;
- selected imaging/lab context;
- discharge disposition;
- complications;
- mortality, ED revisit, and readmission; and
- post-discharge/90-day follow-up.

## Repository structure

```text
RESTORE-PA-redcap-prototype/
├── app/                  # Streamlit collaborator-facing prototype
├── data_model/           # schema and source/provenance rules
├── synthetic_data/       # reproducible synthetic-data generation
│   └── outputs/          # generated files (gitignored)
├── tests/                # basic synthetic-data validation
├── scripts/              # convenience launch scripts
├── requirements.txt
└── README.md
```

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python synthetic_data/generate_demo_data.py
streamlit run app/app.py
```

The generator creates 200 fully synthetic stroke episodes by default.

## Design principle

The prototype separates the **source value** from the **registry-reviewed value** when the same clinical concept can come from more than one source. This prevents the future interface from silently overwriting PCORI/PCORnet-derived information with manually entered registry data.

## Current status

This is an early collaborator-facing prototype. The next design step is to use feedback from the Stroke Program and REDCap team to choose the production field subset and produce the formal source-to-REDCap mapping/data dictionary.
