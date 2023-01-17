import frappe
import json
from gp_phonix_integration.gp_phonix_integration.service.connection import execute_send
from gp_phonix_integration.gp_phonix_integration.constant.api_setup import CONFIG

@frappe.whitelist()

def get_master_list(company):

	response =  execute_send(company_name = company, endpoint_code = CONFIG)

	stores = prepare_stores(response.get("Warehouses"))
	
	prices_levels = format_converter(response.get("PriceLevels"), "IdPriceLevel")

	orders_ids = format_converter(response.get("Orders"), "IdOrder", "OrderType")

	customers_class = format_converter(response.get("CustomerClass"), "IdClass", "ClassDescription")
	
	return {
		"stores": stores,
		"prices_levels": prices_levels,
		"orders_ids": orders_ids,
		"customers_class": customers_class
	}


def prepare_stores(stores):

	data = frappe.db.sql("""
		UPDATE `tabqp_GP_Store` 
		SET
			is_deleted = 1 
	""")

	store_list = []

	for store in stores:

		doctype = 'qp_GP_Store'

		store_id = store.get("IdWarehouse")
		
		store_name = store.get("WarehouseName")

		store_description = get_format(store, "IdWarehouse", "WarehouseName")

		param = (doctype, store_id)

		if frappe.db.exists(*param):

			frappe.db.set_value(*param, "is_deleted", 0)

		else:
			
			new_store = frappe.new_doc('qp_GP_Store')

			new_store.store_id = store_id
			new_store.store_name = store_name
			new_store.store_description = store_description

			new_store.save()

		store_list.append(store_description)
	
	return store_list


def format_converter(list_origin, id_name, description_name = None):

	list_result = map(lambda x: get_format(x, id_name , description_name), list_origin)

	return list(list_result)

def description_valdiation(obj, description_name):

	return "|{}".format(obj.get(description_name)) if description_name else ""

def get_format(obj, id_name, description_name = None):

	description = description_valdiation(obj, description_name)

	return "{}{}".format(obj.get(id_name), description)