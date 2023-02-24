import frappe
import json
import random
from gp_phonix_integration.gp_phonix_integration.service.connection import execute_send
from gp_phonix_integration.gp_phonix_integration.service.utils import get_master_setup
from gp_phonix_integration.gp_phonix_integration.constant.api_setup import CHECKOUTART,LEVELS

def handler(item_list):

    name = "name"
    
    return __search_inventary(item_list, name)

def get_item_order(item_list):

    name = "item_code"

    return __search_inventary(item_list, name) 

def __search_inventary(item_list = [], name = None):
    
    item_name = list(map(lambda item: {"Id": item[name]},item_list))

    store_main = __get_basic_params()

    companies = frappe.db.get_all("Company", pluck='name');

    json_data = json.dumps({
        "Items": item_name,
        "Warehouses": [{
            "Id": store_main
        }]
    })

    response =  execute_send(company_name = companies[0], endpoint_code = CHECKOUTART, json_data = json_data)

    for item in item_list:

        inventaies = list(filter(lambda inventary: item[name] == inventary["IdItem"], response["Items"]))

        item.setdefault("quantity", float(inventaies[0]["Quantity"]))
        item.setdefault("quantity_dis", float(inventaies[0]["QuantityDis"]))

        #item.setdefault("quantity", random.choice([0, 100, 50, 0, 0]))
    

    return item_list

def __get_basic_params():

    master_names = frappe.db.get_all("qp_GP_MasterSetup", pluck='name');

    master_name = master_names[0]

    master_setup = get_master_setup(master_name)

    return master_setup.get_store_id_main()