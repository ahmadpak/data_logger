// Copyright (c) 2025, Havenir Solutions and contributors
// For license information, please see license.txt

frappe.ui.form.on("User Login Attempt", {
    refresh(frm) {
        create_custom_buttons(frm);
    },
});

const create_custom_buttons = (frm) => {
    if (!frm.is_new()) {
        frm.add_custom_button("Recreate CSV File", () => {
            frm.call("recreate_csv").then(() => frm.refresh_field("file_url"));
        });
    }
};
