# Collaborator demo script

This is a short suggested walkthrough for RESTORE-PA discussions. The application uses synthetic data only.

## 1. Start with the dashboard

Point out:

- synthetic patient count vs. stroke episode count;
- stroke case mix;
- IV thrombolysis and thrombectomy rates;
- 90-day follow-up rate; and
- the registry work queue.

The purpose is to show that the proposed interface can support both clinical registry work and reporting.

## 2. Open a case

Use **Case Browser** and open any synthetic case.

Explain the two-column design:

- **PCORI/PCORnet imported fields** are read-only source values.
- **Stroke registry / GWTG fields** are reviewable/editable registry values.

This is the key provenance rule for the prototype.

## 3. Show a source disagreement

Go to **Reports > Source disagreements**, copy a PATID or FIN, and search for that case in **Case Browser**.

The page will show both discharge-disposition values and a warning. The intended workflow is to let the registry reviewer resolve the operational registry value without overwriting the original imported value.

## 4. Demonstrate registry data entry

Open **Registry Entry > Create stroke episode**. Create a new **synthetic** patient or add an episode to an existing synthetic patient. Enter stroke type, severity, treatment, discharge and optional 90-day follow-up. Use the **Create synthetic stroke episode** button.

Return to **Case Browser** and find the new synthetic episode. It appears in the session dataset but is marked **Needs EHR linkage**: the demo deliberately does not invent imported PCORI values for a manually entered registry record.

In **Registry Entry > Update registry / follow-up**, update the 90-day mRS and save. Reopen the case to verify the change.

## 5. Show multiple episodes

Search for a synthetic patient who has more than one episode. The case page displays the patient's other episodes.

This demonstrates why patient-level identity and episode-level stroke data should be modeled separately.

## 6. Show registry work queues

Under **Reports**, demonstrate:

- Registry work queue
- Source disagreements
- Cases needing follow-up
- Missing 90-day mRS
- Thrombolysis cases
- Thrombectomy cases
- Rural stroke cases
- 30-day readmissions

These reports are examples for discussion, not finalized RESTORE-PA requirements.

## 7. End with workflow and data dictionary

Use **Workflow** to summarize the proposed process and **Data Dictionary** to discuss which fields should be included in the production REDCap project.

## Questions for collaborators

The prototype is intended to make these decisions easier:

1. Which PCORI/PCORnet values should be visible in REDCap?
2. Which imported values need a registry-reviewed counterpart?
3. Which GWTG/Stroke Universe fields are essential for routine workflow?
4. Which follow-up fields should be actively tracked?
5. Which reports or work queues are needed by the Stroke Program?
6. How should source disagreements be reviewed and documented?

## Session reset

Before a second collaborator demonstration, use **Reset demo entries** in the sidebar. It restores the 200-episode seeded synthetic dataset. Changes are kept only in the current Streamlit browser session and are not saved to disk.
