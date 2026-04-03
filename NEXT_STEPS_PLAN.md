# IT Asset Management App — Suggested Next Steps Plan

## Purpose
This document outlines the recommended sequence for moving from database setup to a functional Streamlit application with reliable query workflows.

## Current Baseline
- Python app can establish a MySQL connection.
- Schema file exists: `schema.sql`.
- Data is available for import through MySQL Workbench.
- Streamlit app skeleton exists in `src/main.py`.

---

## Phase 1 — Database Initialization (Highest Priority)

### 1. Confirm target database
- Decide and document the exact database/schema name used for this project.
- Ensure Workbench and the app both point to the same target.

### 2. Apply schema
- Execute `schema.sql` in MySQL Workbench against the target database.
- Confirm all expected tables, keys, and constraints were created.

### 3. Import seed/application data
- Import data into tables in dependency-safe order:
  - Parent/reference tables first
  - Child/transaction tables second
- If foreign key errors occur, adjust import order and data consistency.

### 4. Validate data load
- Check row counts for each table.
- Spot-check critical joins to confirm relational integrity.
- Log any mismatches for correction before app query work begins.

### Deliverables
- Schema created successfully
- Data imported successfully
- Basic validation checklist completed

---

## Phase 2 — Application Configuration Alignment

### 1. Environment configuration review
- Verify app environment variables are present and correct:
  - `DB_HOST`
  - `DB_USER`
  - `DB_PASS`
  - `DB_PORT`
  - Database name setting
- Confirm SSL certificate path is valid where required.

### 2. App/database target match
- Confirm `src/main.py` points to the same database used in Workbench.
- Remove hardcoded mismatches before feature work.

### Deliverables
- One source of truth for DB config
- Successful test connection from Streamlit app

---

## Phase 3 — Minimal Query UI (First Usable Milestone)

### 1. Add one read-only query workflow
- Add one button-triggered query action.
- Execute a simple `SELECT ... LIMIT ...` query.
- Render output in a Streamlit table/dataframe.

### 2. Add error/empty states
- Show clear UI feedback for:
  - Connection failure
  - Query error
  - No matching rows

### 3. Keep cursor lifecycle short
- Maintain connection at app level.
- Create/close cursor inside each query function.

### Deliverables
- One working end-to-end query in UI
- Stable behavior on reruns

---

## Phase 4 — Expand Query Experience

### 1. Add user input filters
- Text search filters
- Dropdown filters for status/type
- Date range filters (if applicable)

### 2. Add structured layouts
- Sidebar for controls
- Main panel for results
- Optional tabs for grouped views

### 3. Improve result usability
- Row counts and summary metrics
- Sorting expectations documented
- Optional CSV export for stakeholders

### Deliverables
- Multi-filter query page
- Usable operator workflow for read operations

---

## Phase 5 — Data Modification Features (CRUD)

### 1. Add controlled insert/update/delete flows
- Use forms for all write operations.
- Add validation before submitting changes.
- Confirm writes with success/failure messages.

### 2. Protect data integrity
- Enforce required fields in UI.
- Handle foreign key references with dropdowns where possible.

### Deliverables
- At least one safe write workflow
- Error handling that prevents silent data corruption

---

## Phase 6 — Quality, Testing, and Team Handoff

### 1. Test checklist
- Connection test
- Query result correctness test
- Edge case tests (empty result, invalid filter, dropped connection)

### 2. Team documentation
- Setup guide (env vars, dependencies, run instructions)
- Data load guide (schema + import order)
- Feature usage guide for demo day

### 3. Final polish
- Improve labels/help text for non-technical users
- Add loading indicators for longer queries

### Deliverables
- Repeatable local setup
- Demo-ready app behavior

---

## Suggested Immediate Next 3 Actions
1. Run `schema.sql` in Workbench and verify table creation.
2. Import data in parent→child order and validate row counts.
3. Implement one Streamlit button that runs one verified `SELECT` query and displays results.

## Risks to Watch
- App points to a different database than Workbench.
- Foreign key failures due to import order.
- Hardcoded config values drifting from `.env` values.

## Definition of “Ready to Build More UI”
You are ready for broader UI/query work when:
- Schema and seed data are confirmed loaded.
- Streamlit can connect consistently.
- At least one query works end-to-end in the app and matches Workbench output.
