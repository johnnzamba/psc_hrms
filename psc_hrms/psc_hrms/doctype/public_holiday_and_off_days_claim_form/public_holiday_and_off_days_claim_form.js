// Copyright (c) 2025, Techsavanna Technology and contributors
// For license information, please see license.txt

frappe.ui.form.on("Public Holiday and Off Days Claim Form", {
    setup(frm) {
        frm.set_query("for_staff", function() {
            let filters = {};
            if (frm.doc.department) {
                filters.department = frm.doc.department;
            }
            return { filters };
        });
        frm.set_query("worked_on", "table_bxck", () => {
            if (frm.doc.from_date && frm.doc.to_date) {
                return {
                    filters: [
                        ["worked_on", ">=", frm.doc.from_date],
                        ["worked_on", "<=", frm.doc.to_date],
                    ]
                };
            }
        });
    },
    department(frm) {
        frm.refresh_field("for_staff");
    }, 
    for_staff(frm) {
        if (frm.doc.for_staff) {
            frappe.db.get_value('Employee', frm.doc.for_staff, 'employee_name')
                .then(({ message }) => {
                    if (message && message.employee_name) {
                        frm.set_value('staff_name', message.employee_name);
                    }
                });
        } else {
            // Clear staff_name if for_staff is cleared
            frm.set_value('staff_name', null);
        }
    },
    refresh(frm) {
        // clear any previous intro
        frm.set_intro();
        if (frm.doc.workflow_state === "Draft" && !frm.is_new()) {
            
            frm.set_intro(
                __("Please Ensure to Submit Document to the Supervisor for Review"),
                "red"
            );
        }

        if (frm.doc.workflow_state === "Approved by Supervisor") {
            
            frm.set_intro(
                __("Please Ensure to Submit Document to the HOD for Review"),
                "green"
            );
        }
        if (frm.doc.workflow_state === "Approved by HOD") {
            
            frm.set_intro(
                __("Please Ensure to Submit Document to the HR for Review"),
                "orange"
            );
        }
        if (frm.doc.workflow_state === "Approved by HRM" && frm.doc.leave_allocation) {
            const link = `<a href="/app/leave-allocation/${frm.doc.leave_allocation}" target="_blank">${frm.doc.leave_allocation}</a>`;
            frm.set_intro(
                `Leave Allocation Done after APPROVAL: ${link}`,
                "blue"
            );
        }        

    }
    
    // onload(frm) {
    //     if (frm.is_new()) {
    //         frappe.db
    //             .get_value("Employee",
    //                 { user_id: frappe.session.user },
    //                 "name"
    //             )
    //             .then(({ message }) => {
    //                 if (message && message.name) {
    //                     frm.set_value("created_by", message.name);
    //                 }
    //             });
        
    //     }
    // }
    
});

//Helper 
function refresh_eligible_days(frm) {
    const count = (frm.doc.table_bxck || []).filter(r => r.worked_on).length;
    frm.set_value('eligible_days', `${count} Day(s)`);
}

frappe.ui.form.on('Claim Form Reference', {
    refresh(frm, cdt, cdn) {
        const row = locals[cdt][cdn];

        // —— 1) Prefill staff_name on new rows ——
        if (!row.staff_name && frm.doc.for_staff) {
            frappe.model.set_value(cdt, cdn, 'staff_name', frm.doc.for_staff);
        }

        // —— 2) Constrain the datepicker for worked_on ——
        let grid = frm.fields_dict['table_bxck'].grid;
        grid.wrapper.off('focus', 'input[data-fieldname="worked_on"]');
        grid.wrapper.on('focus', 'input[data-fieldname="worked_on"]', function() {
            let $inp = $(this);
            if (frm.doc.from_date && frm.doc.to_date) {
                $inp.datepicker('setStartDate', frm.doc.from_date);
                $inp.datepicker('setEndDate',   frm.doc.to_date);
            }
        });
    },
    table_bxck_add(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
    
        if (frm.doc.for_staff) {
          // fetch the Employee.employee_name, then set staff_name to that
          frappe.db
            .get_value('Employee',
                       frm.doc.for_staff,
                       'employee_name'
            )
            .then(({ message }) => {
              if (message && message.employee_name) {
                frappe.model.set_value(cdt, cdn, 'staff_name', message.employee_name);
              }
            });
        }
    },
    after_insert(frm, cdt, cdn) {
        refresh_eligible_days(frm);
    },

    // also handle removal of a row
    table_bxck_remove(frm, cdt, cdn) {
        refresh_eligible_days(frm);
    },

    // —— 3) Validate after the user actually picks or types a date ——
    worked_on(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        const { from_date, to_date } = frm.doc;
        if (from_date && to_date
            && (row.worked_on < from_date || row.worked_on > to_date)
        ) {
            frappe.msgprint({
                title: __('Date selected OUTSIDE Range'),
                indicator: 'red',
                message: __('NOTE: The days CLAIMED must be between {0} and {1}', [
                    from_date,
                    to_date
                ])
            });
            // clear it so they have to pick again
            frappe.model.set_value(cdt, cdn, 'worked_on', null);
        }
        refresh_eligible_days(frm);
    }
});
