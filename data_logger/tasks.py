import datetime

import frappe
from frappe.utils import add_days, add_months, today
from frappe.utils.file_manager import delete_file


def hourly_long():
    """Execute hourly long tasks"""
    generate_user_login_attempt_log("Hourly Long")


def daily_long():
    """Execute daily long tasks"""
    delete_old_user_login_attempt_logs()
    generate_user_login_attempt_log("Daily Long")


def weekly_long():
    """Execute weekly long tasks"""
    generate_user_login_attempt_log("Weekly Long")


def monthly_long():
    """Execute monthly long tasks"""
    generate_user_login_attempt_log("Monthly Long")


def generate_user_login_attempt_log(frequency):
    """Generate user login attempt log for the given frequency"""
    settings = frappe.get_single("Data Logger Settings")
    if not settings.enabled:
        return

    from_datetime = None
    to_datetime = None

    if (
        settings.data_logger_frequency == "Hourly Long"
        and frequency == "Hourly Long"
    ):
        to_datetime = datetime.datetime.now()
        from_datetime = to_datetime - datetime.timedelta(hours=1)

    if (
        settings.data_logger_frequency == "Daily Long"
        and frequency == "Daily Long"
    ):
        to_datetime = datetime.datetime.now()
        from_datetime = to_datetime - datetime.timedelta(days=1)

    if (
        settings.data_logger_frequency == "Weekly Long"
        and frequency == "Weekly Long"
    ):
        to_datetime = datetime.datetime.now()
        from_datetime = to_datetime - datetime.timedelta(weeks=1)

    if (
        settings.data_logger_frequency == "Monthly Long"
        and frequency == "Monthly Long"
    ):
        to_datetime = datetime.datetime.now()
        from_datetime = add_months(to_datetime, -1)

    if not (to_datetime and from_datetime):
        return

    user_login_attempt = frappe.get_doc(
        {
            "doctype": "User Login Attempt",
            "send_email": settings.send_email,
            "email_to": settings.email_to,
            "from_date": from_datetime,
            "to_date": to_datetime,
        }
    )

    user_login_attempt.insert()


def delete_old_user_login_attempt_logs():
    """Delete old user login attempt logs"""
    settings = frappe.get_single("Data Logger Settings")
    if not settings.enabled:
        return

    if settings.data_log_age == 0:
        return

    to_date = add_days(today(), -settings.data_log_age)
    logs = frappe.get_all(
        "User Login Attempt",
        {
            "creation": ["<=", to_date],
        },
    )

    for log in logs:
        doc = frappe.get_doc("User Login Attempt", log.name)
        # Delete all files
        files = frappe.get_all(
            "File", {"attached_to_name": doc.name}, ["name", "file_url"]
        )
        for file in files:
            frappe.delete_doc("File", file.name)
            # Cleanup
            delete_file(file.file_url)

        doc.delete()
