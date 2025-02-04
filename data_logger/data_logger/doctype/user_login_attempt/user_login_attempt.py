"""Data Logger User Login Attempt."""
# Copyright (c) 2025, Havenir Solutions and contributors
# For license information, please see license.txt

import csv

import frappe
import frappe.utils
from frappe import _
from frappe.model.document import Document
from frappe.query_builder.functions import Sum
from frappe.utils import get_site_path
from frappe.utils.file_manager import delete_file, save_file
from pypika.terms import Case


class UserLoginAttempt(Document):
    def validate(self):
        """Hook for validate event"""
        self.validate_from_to_date()
        self.set_logging_attempts()

    def after_insert(self):
        """Hook for after insert event"""

        # Create CSV file
        file_doc = self.create_and_attach_csv()
        self.file_url = file_doc.file_url
        self.save()
        self.notify_update()

        # Send email notification
        if self.send_email:
            self.send_email_notification(file_doc.file_url)

    @frappe.whitelist()
    def recreate_csv(self):
        """Recreate CSV file"""
        # Delete existing file
        if self.file_url:
            file_docs = frappe.db.get_all("File", {"file_url": self.file_url})
            delete_file(self.file_url)
            self.file_url = None

            if file_docs:
                for file in file_docs:
                    frappe.delete_doc("File", file.name)

        # Create new and attach
        file_doc = self.create_and_attach_csv()
        self.file_url = file_doc.file_url
        self.save()

        # Send email notification
        if self.send_email:
            self.send_email_notification(file_doc.file_url)

    def validate_from_to_date(self):
        """From date should be less than to date"""
        if frappe.utils.date_diff(self.to_date, self.from_date) < 0:
            frappe.throw(_("To Date should be greater than From Date"))

    def set_logging_attempts(self):
        """Get users logging attempts"""
        self.attempts = []
        # Build Query
        ActivityLog = frappe.qb.DocType("Activity Log")
        User = frappe.qb.DocType("User")
        success_case = Case().when(ActivityLog.status == "Success", 1).else_(0)
        failed_case = Case().when(ActivityLog.status == "Failed", 1).else_(0)
        sum_successful_logins = Sum(success_case).as_("successful_logins")
        sum_failed_logins = Sum(failed_case).as_("failed_logins")

        query = (
            frappe.qb.from_(ActivityLog)
            .left_join(User)
            .on(User.name == ActivityLog.user)
            .where(
                (ActivityLog.communication_date >= self.from_date)
                & (ActivityLog.communication_date <= self.to_date)
                & (ActivityLog.operation == "Login")
            )
            .groupby(ActivityLog.user)
            .select(
                ActivityLog.user,
                User.first_name,
                User.last_name,
                User.full_name,
                sum_successful_logins,
                sum_failed_logins,
            )
        )

        result = query.run(as_dict=True)
        if result:
            for row in result:
                self.append(
                    "attempts",
                    {
                        "user": row.user,
                        "first_name": row.first_name,
                        "last_name": row.last_name,
                        "full_name": row.full_name,
                        "successful_attempt": row.successful_logins,
                        "failed_attempt": row.failed_logins,
                        "total_attempt": row.successful_logins
                        + row.failed_logins,
                    },
                )

    def create_and_attach_csv(self):
        """Create and attach CSV file"""
        csv_data = [
            [
                "User",
                "First Name",
                "Last Name",
                "Full Name",
                "Successful Attempts",
                "Failed Attempts",
                "Total Attempts",
            ]
        ]
        for attempt in self.attempts:
            csv_data.append(
                [
                    attempt.user,
                    attempt.first_name,
                    attempt.last_name,
                    attempt.full_name,
                    attempt.successful_attempt,
                    attempt.failed_attempt,
                    attempt.total_attempt,
                ]
            )
        csv_filename = f"Login_Attempts_{self.name}.csv"
        csv_path = get_site_path("private", "files", csv_filename)

        # Creating CSV File
        with open(csv_path, "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerows(csv_data)

        # Attach file to document
        with open(csv_path, "rb") as f:
            return save_file(
                csv_filename,
                f.read(),
                self.doctype,
                self.name,
                is_private=1,
            )

    def send_email_notification(self, file_url):
        """Send email with the attached CSV file"""
        recipients = self.email_to.split("\n")
        subject = "User Login Attempts Report"
        message = f"Please find attached the login attempts report from {self.from_date} to {self.to_date}"  # noqa

        attachments = [{"file_url": file_url}]

        frappe.sendmail(
            recipients=recipients,
            subject=subject,
            message=message,
            attachments=attachments,
        )
