# Enrollment Structure Analysis

## Main Structural Issues

| Function/Area | Structural Issue | Why It Hurts Maintainability or Scalability | Layer Concern | Priority |
|---|---|---|---|---|
| Global variables | Paths, statuses, current student, and sample data are stored globally. | Global state makes the code harder to test and change because many functions depend on outside values. | Mixed config/service concern | High |
| `connect` | Mostly database-focused, but depends on global `DB_PATH`. | Testing with a different database would require changing global state. | Database concern | Medium |
| `create_tables` | Handles multiple database setup tasks. | As the database grows, this function could become too large. | Database concern | Medium |
| `seed_sample_data` | Mixes database inserts with sample course data. | The app could become harder to update if seed data and real data are mixed. | Database/config concern | Medium |
| `get_course_by_key` | Cleans and formats the key inside the database lookup. | Validation rules are hidden inside database code instead of a service layer. | Database + service concern | High |
| `get_student_enrollments` | Decides that only enrolled records count as active. | This is a business rule inside a database function. | Database making service decision | High |
| `enroll_with_key` | Combines validation, database lookup, insert/update logic, and status decisions. | One function has too many responsibilities, making it hard to test or change. | Mixed service/database concern | High |
| `soft_unenroll_student` | Performs a business action directly through a database update. | Future unenrollment rules would be harder to add cleanly. | Mixed service/database concern | High |
| `get_student_summary` | Builds summary counts from database records and status rules. | It depends on database-shaped data and service rules at the same time. | Service concern | Medium |
| `export_database_snapshot` | Mixes database reads, current student state, JSON formatting, and file writing. | This makes export logic hard to reuse or test. | Mixed database/service/file concern | High |
| SQLite queries | SQL is spread throughout the project. | Database behavior becomes harder to find and update consistently. | Database concern | High |
| Main runner | Mixes setup, testing, enrollment flow, summaries, printing, and export. | Demo/test flow is not clearly separated from app logic. | Mixed orchestration concern | High |

## Summary

The project works, but the current structure is procedural and mixes responsibilities across layers. The biggest issue is that some database functions are also making service-level decisions, especially around enrollment status, key formatting, and what counts as an active enrollment.

The highest-priority areas to improve later are `enroll_with_key`, `soft_unenroll_student`, `export_database_snapshot`, and the main runner because they combine multiple responsibilities. Global state is also a major risk because paths, statuses, current student data, and sample course keys are shared across the project instead of being clearly separated into configuration, database, and service layers.