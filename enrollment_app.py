from __future__ import annotations

import streamlit as st

from enrollment_starter import (
    CURRENT_STUDENT,
    EnrollmentDatabase,
    EnrollmentService,
    SnapshotExporter,
)


# ---------- Setup ----------

st.set_page_config(
    page_title="Student Enrollment App",
    page_icon="🎓",
    layout="wide",
)


@st.cache_resource
def get_service() -> EnrollmentService:
    """Create database, seed data, and return the service layer."""
    database = EnrollmentDatabase()
    database.create_tables()
    database.seed_sample_data()

    exporter = SnapshotExporter(database)
    exporter.export_database_snapshot()

    return EnrollmentService(database)


def initialize_session_state() -> None:
    """Set default session state values for routing and feedback."""
    if "role" not in st.session_state:
        st.session_state["role"] = "student"

    if "page" not in st.session_state:
        st.session_state["page"] = "dashboard"

    if "selected_course_id" not in st.session_state:
        st.session_state["selected_course_id"] = None

    if "message" not in st.session_state:
        st.session_state["message"] = ""

    if "message_type" not in st.session_state:
        st.session_state["message_type"] = ""


def set_message(message: str, message_type: str) -> None:
    """Store a feedback message in session state."""
    st.session_state["message"] = message
    st.session_state["message_type"] = message_type


def show_message() -> None:
    """Display success, warning, or error messages."""
    message = st.session_state.get("message", "")
    message_type = st.session_state.get("message_type", "")

    if not message:
        return

    if message_type == "success":
        st.success(message)
    elif message_type == "warning":
        st.warning(message)
    elif message_type == "error":
        st.error(message)


def clear_message() -> None:
    """Clear the current feedback message."""
    st.session_state["message"] = ""
    st.session_state["message_type"] = ""


def go_to_dashboard() -> None:
    """Route user back to dashboard."""
    st.session_state["page"] = "dashboard"
    st.session_state["selected_course_id"] = None


def go_to_class(course_id: str) -> None:
    """Route user to selected class page."""
    st.session_state["selected_course_id"] = course_id
    st.session_state["page"] = "class_detail"


# ---------- Pages ----------

def show_dashboard(service: EnrollmentService) -> None:
    """Student dashboard page."""
    student = CURRENT_STUDENT
    user_id = student["user_id"]
    email = student["email"]

    st.title("Student Enrollment Dashboard")
    st.caption(f"Logged in as {student['name']} | {email}")

    show_message()

    summary = service.get_student_summary(user_id)
    enrolled_courses = service.get_student_enrollments(user_id)

    st.divider()

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Records", summary["total_records"])
    col2.metric("Currently Enrolled", summary["enrolled"])
    col3.metric("Unenrolled", summary["unenrolled"])

    st.divider()

    st.subheader("Join a Class")

    with st.form("enrollment_form"):
        enrollment_key = st.text_input(
            "Enter enrollment key",
            placeholder="Example: DATA210-SPRING",
        )
        submitted = st.form_submit_button("Join Class")

    if submitted:
        clear_message()

        if not enrollment_key.strip():
            set_message("Please enter an enrollment key.", "warning")
            st.rerun()

        enrollment_record = service.enroll_with_key(
            user_id=user_id,
            email=email,
            enrollment_key=enrollment_key,
        )

        if enrollment_record:
            st.session_state["selected_course_id"] = enrollment_record["course_id"]
            st.session_state["page"] = "class_detail"
            set_message(
                f"You are now enrolled in {enrollment_record['course_id']}.",
                "success",
            )
            st.rerun()
        else:
            set_message("Invalid enrollment key. Please try again.", "error")
            st.rerun()

    with st.expander("Available practice enrollment keys"):
        available_keys = service.get_available_course_keys()

        for course in available_keys:
            st.write(
                f"**{course['course_id']}** — {course['course_name']} "
                f"({course['enrollment_key']})"
            )

    st.divider()

    st.subheader("My Enrolled Classes")

    if not enrolled_courses:
        st.warning("You are not currently enrolled in any classes.")
        return

    for course in enrolled_courses:
        with st.container(border=True):
            left_col, right_col = st.columns([3, 1])

            with left_col:
                st.write(f"### {course['course_id']}: {course['course_name']}")
                st.write(f"**Instructor:** {course['instructor']}")
                st.write(f"**Status:** {course['status']}")
                st.write(f"**Enrolled At:** {course['enrolled_at']}")

            with right_col:
                if st.button(
                    "Go to Class",
                    key=f"go_{course['course_id']}",
                    use_container_width=True,
                ):
                    clear_message()
                    go_to_class(course["course_id"])
                    st.rerun()

                if st.button(
                    "Unenroll",
                    key=f"unenroll_{course['course_id']}",
                    use_container_width=True,
                ):
                    success = service.soft_unenroll_student(
                        user_id=user_id,
                        course_id=course["course_id"],
                    )

                    if success:
                        set_message(
                            f"You have been unenrolled from {course['course_id']}.",
                            "success",
                        )
                    else:
                        set_message(
                            "Something went wrong. The class could not be unenrolled.",
                            "error",
                        )

                    st.session_state["page"] = "dashboard"
                    st.rerun()


def show_class_detail(service: EnrollmentService) -> None:
    """Selected class detail page."""
    student = CURRENT_STUDENT
    user_id = student["user_id"]
    selected_course_id = st.session_state.get("selected_course_id")

    if not selected_course_id:
        set_message("No class was selected. Returning to dashboard.", "warning")
        go_to_dashboard()
        st.rerun()

    enrolled_courses = service.get_student_enrollments(user_id)

    selected_course = None
    for course in enrolled_courses:
        if course["course_id"] == selected_course_id:
            selected_course = course
            break

    if selected_course is None:
        set_message(
            "That class is no longer active in your enrolled courses.",
            "warning",
        )
        go_to_dashboard()
        st.rerun()

    st.title("Class Page")
    st.caption(f"Viewing class for {student['name']}")

    show_message()

    st.divider()

    with st.container(border=True):
        st.subheader(selected_course["course_name"])
        st.write(f"**Course ID:** {selected_course['course_id']}")
        st.write(f"**Instructor:** {selected_course['instructor']}")
        st.write(f"**Status:** {selected_course['status']}")
        st.write(f"**Enrolled At:** {selected_course['enrolled_at']}")

    st.divider()

    if st.button("Back to Dashboard"):
        clear_message()
        go_to_dashboard()
        st.rerun()


# ---------- Main App ----------

def main() -> None:
    initialize_session_state()
    service = get_service()

    if st.session_state["role"] != "student":
        st.error("You do not have permission to view this student app.")
        return

    with st.sidebar:
        st.title("Navigation")
        st.write(f"Role: **{st.session_state['role']}**")
        st.write(f"Student: **{CURRENT_STUDENT['name']}**")

        if st.button("Dashboard"):
            clear_message()
            go_to_dashboard()
            st.rerun()

    if st.session_state["page"] == "dashboard":
        show_dashboard(service)
    elif st.session_state["page"] == "class_detail":
        show_class_detail(service)
    else:
        set_message("Unknown page. Returning to dashboard.", "warning")
        go_to_dashboard()
        st.rerun()


if __name__ == "__main__":
    main()