import frappe
from qp_phonix_front.qp_phonix_front.uses_cases.shipping_method.shipping_method_list import __get_customer

def get_master_setup(master_name):

    return frappe.get_doc("qp_GP_MasterSetup", master_name)

def get_price_list(customer = None):
    
    if not customer:
        
        customer = __get_customer()

    if customer.default_price_list:
        
        return customer.default_price_list

    return frappe.db.get_single_value("Selling Settings", "selling_price_list")