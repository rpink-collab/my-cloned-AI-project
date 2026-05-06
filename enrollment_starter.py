"""
Module 8 Student Enrollment backend starter.

This file is intentionally procedural. It has functions and top-level
database code, but no classes yet. Students will first group related behavior
into an EnrollmentManager class, then separate service and database layers.

App idea:
    - a student opens a dashboard
    - the dashboard shows enrolled classes
    - the student enters an enrollment key to join another class
    - the database stores courses and enrollment records
    - a JSON snapshot is exported so students can inspect the seeded data

Focus:
    - student enrollment behavior
    - local SQLite database
    - enrollment keys
    - soft unenroll using status = "unenrolled"

Out of scope:
    - Streamlit UI
    - authentication/session state
    - caching
    - export formatting
    - production health checks

Run with:
    enrollment_starter.py
"""

# Module 8 Student Enrollment backend refactor.
#
# Backend-only refactor of the procedural enrollment starter.

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Optional


DB_PATH = Path(__file__).with_name("student_enrollment_practice.db")
SNAPSHOT_PATH = Path(__file__).with_name("student_enrollment_snapshot.json")

STATUS_ENROLLED = "enrolled"
STATUS_UNENROLLED = "unenrolled"

CURRENT_STUDENT = {
    "user_id": "u100",
    "name": "Maya Patel",
    "email": "maya.patel@example.edu",
}

AVAILABLE_COURSE_KEYS = [
    {
        "course_id": "MISY350",
        "course_name": "Python for Business Analytics",
        "instructor": "Dr. Rivera",
        "enrollment_key": "MISY350-SPRING",
    },
    {
        "course_id": "DATA210",
        "course_name": "Data Storytelling",
        "instructor": "Prof. Morgan",
        "enrollment_key": "DATA210-SPRING",
    },
    {
        "course_id": "WEB220",
        "course_name": "Web Apps With Streamlit",
        "instructor": "Dr. Chen",
        "enrollment_key": "WEB220-SPRING",
    },
]

SAMPLE_ENROLLMENTS = [
    ("u100", "maya.patel@example.edu", "MISY350", STATUS_ENROLLED),
    ("u100", "maya.patel@example.edu", "DATA210", STATUS_UNENROLLED),
    ("u101", "alex@example.edu", "MISY350", STATUS_ENROLLED),
    ("u102", "blair@example.edu", "WEB220", STATUS_ENROLLED),
]


def rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    """Convert SQLite rows into dictionaries."""
    return [dict(row) for row in rows]


class EnrollmentDatabase:
    """Database layer for SQLite setup, queries, inserts, and updates."""

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path

    def connect(self) -> sqlite3.Connection:
        """Open a database connection."""
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def create_tables(self) -> None:
        """Create the courses and enrollments tables."""
        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS courses (
                    course_id TEXT PRIMARY KEY,
                    course_name TEXT NOT NULL,
                    instructor TEXT NOT NULL,
                    enrollment_key TEXT NOT NULL UNIQUE
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS enrollments (
                    enrollment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    email TEXT NOT NULL,
                    course_id TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'enrolled',
                    enrolled_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, course_id),
                    FOREIGN KEY(course_id) REFERENCES courses(course_id)
                )
                """
            )

    def seed_sample_data(
        self,
        courses: list[dict[str, str]] = AVAILABLE_COURSE_KEYS,
        enrollments: list[tuple[str, str, str, str]] = SAMPLE_ENROLLMENTS,
    ) -> None:
        """Seed courses, enrollment keys, and practice enrollment records."""
        with self.connect() as connection:
            connection.executemany(
                """
                INSERT OR IGNORE INTO courses (
                    course_id, course_name, instructor, enrollment_key
                )
                VALUES (?, ?, ?, ?)
                """,
                [
                    (
                        course["course_id"],
                        course["course_name"],
                        course["instructor"],
                        course["enrollment_key"],
                    )
                    for course in courses
                ],
            )
            connection.executemany(
                """
                INSERT OR IGNORE INTO enrollments (user_id, email, course_id, status)
                VALUES (?, ?, ?, ?)
                """,
                enrollments,
            )

    def get_available_course_keys(self) -> list[dict[str, Any]]:
        """Return available course-key rows."""
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT course_id, course_name, instructor, enrollment_key
                FROM courses
                ORDER BY course_id
                """
            ).fetchall()

        return rows_to_dicts(rows)

    def get_course_by_key(self, normalized_enrollment_key: str) -> Optional[dict[str, Any]]:
        """Find a course by an already-normalized enrollment key."""
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT course_id, course_name, instructor, enrollment_key
                FROM courses
                WHERE enrollment_key = ?
                """,
                (normalized_enrollment_key,),
            ).fetchone()

        return dict(row) if row else None

    def get_student_enrollments_by_status(
        self,
        user_id: str,
        status: str,
    ) -> list[dict[str, Any]]:
        """Return student enrollment rows matching one status."""
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    e.enrollment_id,
                    e.user_id,
                    e.email,
                    e.course_id,
                    c.course_name,
                    c.instructor,
                    e.status,
                    e.enrolled_at
                FROM enrollments e
                JOIN courses c ON c.course_id = e.course_id
                WHERE e.user_id = ? AND e.status = ?
                ORDER BY c.course_id
                """,
                (user_id, status),
            ).fetchall()

        return rows_to_dicts(rows)

    def get_student_enrollment_history(self, user_id: str) -> list[dict[str, Any]]:
        """Return all enrollment rows for one student."""
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    e.enrollment_id,
                    e.user_id,
                    e.email,
                    e.course_id,
                    c.course_name,
                    c.instructor,
                    e.status,
                    e.enrolled_at
                FROM enrollments e
                JOIN courses c ON c.course_id = e.course_id
                WHERE e.user_id = ?
                ORDER BY c.course_id
                """,
                (user_id,),
            ).fetchall()

        return rows_to_dicts(rows)

    def get_student_course_record(
        self,
        user_id: str,
        course_id: str,
    ) -> Optional[dict[str, Any]]:
        """Return one student's enrollment row for one course."""
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT enrollment_id, user_id, email, course_id, status, enrolled_at
                FROM enrollments
                WHERE user_id = ? AND course_id = ?
                """,
                (user_id, course_id),
            ).fetchone()

        return dict(row) if row else None

    def upsert_enrollment(
        self,
        user_id: str,
        email: str,
        course_id: str,
        status: str,
    ) -> None:
        """Insert or reactivate an enrollment row."""
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO enrollments (user_id, email, course_id, status)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, course_id)
                DO UPDATE SET
                    email = excluded.email,
                    status = excluded.status,
                    enrolled_at = CURRENT_TIMESTAMP
                """,
                (user_id, email, course_id, status),
            )

    def update_enrollment_status(
        self,
        user_id: str,
        course_id: str,
        status: str,
    ) -> bool:
        """Update one enrollment row's status."""
        with self.connect() as connection:
            cursor = connection.execute(
                """
                UPDATE enrollments
                SET status = ?
                WHERE user_id = ? AND course_id = ?
                """,
                (status, user_id, course_id),
            )

        return cursor.rowcount > 0

    def get_all_enrollment_records(self) -> list[dict[str, Any]]:
        """Return every enrollment row for reports or snapshots."""
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    e.enrollment_id,
                    e.user_id,
                    e.email,
                    e.course_id,
                    c.course_name,
                    c.instructor,
                    e.status,
                    e.enrolled_at
                FROM enrollments e
                JOIN courses c ON c.course_id = e.course_id
                ORDER BY e.user_id, e.course_id
                """
            ).fetchall()

        return rows_to_dicts(rows)


class EnrollmentService:
    """Service layer for enrollment rules, validation, and summaries."""

    def __init__(self, database: EnrollmentDatabase) -> None:
        self.database = database

    def normalize_enrollment_key(self, enrollment_key: str) -> str:
        """Normalize a student-entered enrollment key."""
        return enrollment_key.strip().upper()

    def is_valid_student_input(self, user_id: str, email: str) -> bool:
        """Validate the minimum student fields required for enrollment."""
        return bool(user_id and email and "@" in email)

    def get_available_course_keys(self) -> list[dict[str, Any]]:
        """Return available enrollment keys for practice display."""
        return self.database.get_available_course_keys()

    def get_course_by_key(self, enrollment_key: str) -> Optional[dict[str, Any]]:
        """Validate and find a course by enrollment key."""
        if not enrollment_key:
            return None

        normalized_key = self.normalize_enrollment_key(enrollment_key)
        return self.database.get_course_by_key(normalized_key)

    def get_student_enrollments(self, user_id: str) -> list[dict[str, Any]]:
        """Return classes where the student is currently enrolled."""
        if not user_id:
            return []

        return self.database.get_student_enrollments_by_status(user_id, STATUS_ENROLLED)

    def get_student_enrollment_history(self, user_id: str) -> list[dict[str, Any]]:
        """Return all enrollment records for one student."""
        if not user_id:
            return []

        return self.database.get_student_enrollment_history(user_id)

    def enroll_with_key(
        self,
        user_id: str,
        email: str,
        enrollment_key: str,
    ) -> Optional[dict[str, Any]]:
        """Enroll or reactivate a student using a course enrollment key."""
        if not self.is_valid_student_input(user_id, email) or not enrollment_key:
            return None

        course = self.get_course_by_key(enrollment_key)
        if not course:
            return None

        self.database.upsert_enrollment(
            user_id=user_id,
            email=email,
            course_id=course["course_id"],
            status=STATUS_ENROLLED,
        )
        return self.database.get_student_course_record(user_id, course["course_id"])

    def soft_unenroll_student(self, user_id: str, course_id: str) -> bool:
        """Soft-unenroll one student by changing status instead of deleting."""
        if not user_id or not course_id:
            return False

        return self.database.update_enrollment_status(
            user_id=user_id,
            course_id=course_id,
            status=STATUS_UNENROLLED,
        )

    def get_student_summary(self, user_id: str) -> dict[str, int]:
        """Return summary counts for one student."""
        summary = {
            "total_records": 0,
            STATUS_ENROLLED: 0,
            STATUS_UNENROLLED: 0,
        }

        for record in self.get_student_enrollment_history(user_id):
            summary["total_records"] += 1
            status = record["status"]
            if status in summary:
                summary[status] += 1

        return summary


class SnapshotExporter:
    """Export helper for writing database snapshots to JSON."""

    def __init__(
        self,
        database: EnrollmentDatabase,
        current_student: dict[str, str] = CURRENT_STUDENT,
    ) -> None:
        self.database = database
        self.current_student = current_student

    def export_database_snapshot(self, path: Path = SNAPSHOT_PATH) -> None:
        """Write seeded database content to JSON so students can inspect it."""
        snapshot = {
            "current_student": self.current_student,
            "available_course_keys": self.database.get_available_course_keys(),
            "enrollment_table": self.database.get_all_enrollment_records(),
        }
        path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")


def main() -> None:
    """Small terminal runner for checking backend behavior before the UI exists."""
    database = EnrollmentDatabase()
    service = EnrollmentService(database)
    exporter = SnapshotExporter(database)

    database.create_tables()
    database.seed_sample_data()

    user_id = CURRENT_STUDENT["user_id"]
    email = CURRENT_STUDENT["email"]

    print("Current student:")
    print(CURRENT_STUDENT)

    print("\nAvailable enrollment keys:")
    print(service.get_available_course_keys())

    print("\nInitial enrolled classes:")
    print(service.get_student_enrollments(user_id))

    print("\nStudent enters key DATA210-SPRING:")
    print(service.enroll_with_key(user_id, email, "DATA210-SPRING"))

    print("\nUpdated enrolled classes:")
    print(service.get_student_enrollments(user_id))

    print("\nStudent summary:")
    print(service.get_student_summary(user_id))

    exporter.export_database_snapshot()
    print(f"\nDatabase snapshot written to: {SNAPSHOT_PATH}")


if __name__ == "__main__":
    main()