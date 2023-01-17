import frappe
def get_master_setup(master_name):

    return frappe.get_doc("qp_GP_MasterSetup", master_name)