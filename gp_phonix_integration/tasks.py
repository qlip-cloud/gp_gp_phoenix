import frappe
from gp_phonix_integration.gp_phonix_integration.use_case.item_setup import sync_item

def cron():
	
    master_setup_list = frappe.get_all("qp_GP_MasterSetup", {"is_active": True}, ["name", "store_main"])

    for master_setup in master_setup_list:

        frappe.enqueue('gp_phonix_integration.gp_phonix_integration.use_case.item_setup.sync_item', master_name=master_setup.get("name"),store_main=master_setup.get("store_main"))