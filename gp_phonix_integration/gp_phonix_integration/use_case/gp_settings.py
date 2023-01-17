import frappe

def get_active_app():

    return frappe.db.get_singles_value('qp_GP_Application', 'active_app')
